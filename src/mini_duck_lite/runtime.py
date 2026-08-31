"""50 Hz local runtime foundation with watchdog and soft-limit fail-safe."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime
import json
import math
from pathlib import Path
import time
from typing import Callable

from mini_duck_lite.hardware import ImuBackend, MockImuBackend, MockServoBus, ServoBus


Clock = Callable[[], float]


@dataclass(frozen=True)
class RuntimeConfig:
    control_hz: int
    command_timeout_ms: float
    imu_timeout_ms: float
    max_tick_late_ms: float
    soft_limits_rad: dict[int, tuple[float, float]]
    safe_pose_rad: dict[int, float]


def load_runtime_config(path: Path, *, allow_sim_limits: bool = False) -> RuntimeConfig:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("schema_version") != "safe-runtime/v1":
        raise ValueError("unsupported runtime config schema")
    if data.get("control_hz") != 50:
        raise ValueError("the V0.4 local control loop must run at 50 Hz")
    if data.get("limits_source") == "SIM_ONLY" and not allow_sim_limits:
        raise ValueError("SIM_ONLY limits cannot start a real hardware runtime")
    limits = {
        int(bus_id): (float(values[0]), float(values[1]))
        for bus_id, values in data["soft_limits_rad"].items()
    }
    safe_pose = {
        int(bus_id): float(value) for bus_id, value in data["safe_pose_rad"].items()
    }
    if limits.keys() != safe_pose.keys():
        raise ValueError("safe pose and soft limits must cover the same bus IDs")
    for bus_id, (lower, upper) in limits.items():
        if not lower < safe_pose[bus_id] < upper:
            raise ValueError(f"safe pose for bus {bus_id} is outside soft limits")
    return RuntimeConfig(
        control_hz=50,
        command_timeout_ms=float(data["command_timeout_ms"]),
        imu_timeout_ms=float(data["imu_timeout_ms"]),
        max_tick_late_ms=float(data["max_tick_late_ms"]),
        soft_limits_rad=limits,
        safe_pose_rad=safe_pose,
    )


class SafeRuntime:
    def __init__(
        self,
        *,
        config: RuntimeConfig,
        servo_bus: ServoBus,
        imu: ImuBackend,
        clock: Clock = time.monotonic,
    ) -> None:
        self.config = config
        self.servo_bus = servo_bus
        self.imu = imu
        self.clock = clock
        self._command = dict(config.safe_pose_rad)
        self._command_at: float | None = None
        self._last_tick: float | None = None
        self.safe_state_reason: str | None = None

    def set_command(self, positions_rad: dict[int, float]) -> None:
        if positions_rad.keys() != self.config.soft_limits_rad.keys():
            raise ValueError("command must cover the full calibrated joint set")
        for bus_id, value in positions_rad.items():
            lower, upper = self.config.soft_limits_rad[bus_id]
            if not math.isfinite(value):
                raise ValueError(f"joint {bus_id} command is not finite")
            if not lower <= value <= upper:
                raise ValueError(f"joint {bus_id} command exceeds its soft limit")
        self._command = dict(positions_rad)
        self._command_at = self.clock()

    def _enter_safe_state(self, reason: str) -> dict[str, object]:
        self.safe_state_reason = reason
        self.servo_bus.torque_off()
        return {"status": "SAFE_STATE", "reason": reason}

    def tick(self) -> dict[str, object]:
        now = self.clock()
        if self._command_at is None:
            return self._enter_safe_state("NO_COMMAND")
        command_age_ms = (now - self._command_at) * 1000.0
        if command_age_ms > self.config.command_timeout_ms:
            return self._enter_safe_state("COMMAND_TIMEOUT")
        if self._last_tick is not None:
            expected_period = 1.0 / self.config.control_hz
            late_ms = max(0.0, now - self._last_tick - expected_period) * 1000.0
            if late_ms > self.config.max_tick_late_ms:
                return self._enter_safe_state("CONTROL_DEADLINE_MISS")

        try:
            sample = self.imu.read()
        except (OSError, RuntimeError, ValueError):
            return self._enter_safe_state("IMU_IO_ERROR")
        imu_age_ms = max(0.0, (self.clock() - sample.timestamp_s) * 1000.0)
        if imu_age_ms > self.config.imu_timeout_ms:
            return self._enter_safe_state("IMU_STALE")
        sensor_values = (*sample.quaternion_wxyz, *sample.angular_velocity_rad_s)
        if not all(math.isfinite(value) for value in sensor_values):
            return self._enter_safe_state("IMU_NAN")

        states: dict[int, dict[str, float | bool]] = {}
        for bus_id, target in self._command.items():
            try:
                self.servo_bus.write_position(bus_id, target)
                state = self.servo_bus.read(bus_id)
            except (ConnectionError, OSError, RuntimeError):
                return self._enter_safe_state(f"SERVO_{bus_id}_DISCONNECTED")
            if not state.connected:
                return self._enter_safe_state(f"SERVO_{bus_id}_DISCONNECTED")
            states[bus_id] = {
                "position_rad": state.position_rad,
                "velocity_rad_s": state.velocity_rad_s,
                "current_a": state.current_a,
                "voltage_v": state.voltage_v,
                "temperature_c": state.temperature_c,
                "latency_ms": state.latency_ms,
                "connected": state.connected,
            }
        self._last_tick = now
        return {
            "status": "RUNNING",
            "command_age_ms": command_age_ms,
            "imu_age_ms": imu_age_ms,
            "states": states,
        }

    def close(self) -> None:
        self.servo_bus.torque_off()
        self.servo_bus.close()
        self.imu.close()


def run_mock_runtime(config: RuntimeConfig, cycles: int, log_path: Path) -> None:
    if cycles <= 0:
        raise ValueError("cycles must be greater than zero")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        raise FileExistsError(f"runtime log already exists: {log_path}")
    bus = MockServoBus(list(config.soft_limits_rad))
    runtime = SafeRuntime(config=config, servo_bus=bus, imu=MockImuBackend())
    period = 1.0 / config.control_hz
    try:
        with log_path.open("w", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "record_type": "runtime_session",
                        "schema_version": "runtime-log/v1",
                        "started_at": datetime.now().astimezone().isoformat(),
                        "backend": "mock",
                        "evidence_level": "SIM_PASS",
                        "gate_eligible": False,
                        "config": asdict(config),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            running_cycles = 0
            safe_events = 0
            for cycle in range(cycles):
                runtime.set_command(config.safe_pose_rad)
                result = runtime.tick()
                running_cycles += int(result["status"] == "RUNNING")
                safe_events += int(result["status"] == "SAFE_STATE")
                handle.write(
                    json.dumps(
                        {
                            "record_type": "runtime_tick",
                            "cycle": cycle,
                            "monotonic_s": time.monotonic(),
                            **result,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                time.sleep(period)
            handle.write(
                json.dumps(
                    {
                        "record_type": "runtime_summary",
                        "finished_at": datetime.now().astimezone().isoformat(),
                        "requested_cycles": cycles,
                        "running_cycles": running_cycles,
                        "safe_events": safe_events,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    finally:
        runtime.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("log", type=Path)
    parser.add_argument("--backend", choices=("mock",), default="mock")
    parser.add_argument("--cycles", type=int, default=100)
    args = parser.parse_args()
    config = load_runtime_config(args.config, allow_sim_limits=True)
    run_mock_runtime(config, args.cycles, args.log)
    print(json.dumps({"status": "SIM_PASS", "log": str(args.log.resolve())}, indent=2))


if __name__ == "__main__":
    main()
