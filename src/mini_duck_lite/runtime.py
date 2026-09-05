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

from mini_duck_lite.hardware import (
    ImuBackend, ImuSample, MockImuBackend, MockServoBus, ServoBus, ServoState,
)


Clock = Callable[[], float]


@dataclass(frozen=True)
class RuntimeConfig:
    control_hz: int
    command_timeout_ms: float
    imu_timeout_ms: float
    max_tick_late_ms: float
    soft_limits_rad: dict[int, tuple[float, float]]
    safe_pose_rad: dict[int, float]
    servo_timeout_ms: float = 100.0

    def __post_init__(self) -> None:
        if self.control_hz != 50:
            raise ValueError("the V0.4 local control loop must run at 50 Hz")
        for name in ("command_timeout_ms", "imu_timeout_ms", "servo_timeout_ms"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and greater than zero")
        if not math.isfinite(self.max_tick_late_ms) or self.max_tick_late_ms < 0:
            raise ValueError("max_tick_late_ms must be finite and non-negative")
        if not self.soft_limits_rad or self.soft_limits_rad.keys() != self.safe_pose_rad.keys():
            raise ValueError("safe pose and soft limits must cover the same non-empty bus IDs")
        for bus_id, (lower, upper) in self.soft_limits_rad.items():
            safe = self.safe_pose_rad[bus_id]
            if not all(math.isfinite(value) for value in (lower, safe, upper)):
                raise ValueError(f"soft limits and safe pose for bus {bus_id} must be finite")
            if not lower < safe < upper:
                raise ValueError(f"safe pose for bus {bus_id} is outside soft limits")


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
    return RuntimeConfig(
        control_hz=50,
        command_timeout_ms=float(data["command_timeout_ms"]),
        imu_timeout_ms=float(data["imu_timeout_ms"]),
        max_tick_late_ms=float(data["max_tick_late_ms"]),
        soft_limits_rad=limits,
        safe_pose_rad=safe_pose,
        servo_timeout_ms=float(data.get("servo_timeout_ms", data["imu_timeout_ms"])),
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
        if self.safe_state_reason is not None:
            raise RuntimeError("safe state is latched; close and reinitialize the runtime")
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
        if self.safe_state_reason is None:
            self.safe_state_reason = reason
        result: dict[str, object] = {
            "status": "SAFE_STATE", "reason": self.safe_state_reason,
        }
        try:
            self.servo_bus.torque_off()
        except (OSError, RuntimeError, ValueError):
            # A transport failure must remain visible as a failed shutdown,
            # not mask the original fault or imply that torque was removed.
            result["torque_off_failed"] = True
        return result

    def _timing_fault(self, started: float, now: float) -> str | None:
        if self._command_at is None:
            return "NO_COMMAND"
        if (now - self._command_at) * 1000.0 >= self.config.command_timeout_ms:
            return "COMMAND_TIMEOUT"
        if now - started >= 1.0 / self.config.control_hz:
            return "CONTROL_DEADLINE_MISS"
        return None

    def _imu_fault(self, sample: ImuSample, now: float) -> str | None:
        try:
            if (len(sample.quaternion_wxyz), len(sample.angular_velocity_rad_s),
                    len(sample.linear_acceleration_m_s2)) != (4, 3, 3):
                return "IMU_IO_ERROR"
            values = (*sample.quaternion_wxyz, *sample.angular_velocity_rad_s,
                      *sample.linear_acceleration_m_s2, sample.timestamp_s)
            if not all(math.isfinite(value) for value in values):
                return "IMU_NAN"
            age_ms = (now - sample.timestamp_s) * 1000.0
            if age_ms < 0 or age_ms >= self.config.imu_timeout_ms:
                return "IMU_STALE"
        except (AttributeError, TypeError, ValueError):
            return "IMU_IO_ERROR"
        return None

    def _servo_fault(self, bus_id: int, state: ServoState, now: float) -> str | None:
        try:
            if state.bus_id != bus_id or not state.connected:
                return f"SERVO_{bus_id}_DISCONNECTED"
            values = (state.position_rad, state.velocity_rad_s, state.current_a,
                      state.voltage_v, state.temperature_c, state.latency_ms,
                      state.timestamp_s)
            if not all(math.isfinite(value) for value in values):
                return f"SERVO_{bus_id}_NAN"
            age_ms = (now - state.timestamp_s) * 1000.0
            if age_ms < 0 or age_ms >= self.config.servo_timeout_ms:
                return f"SERVO_{bus_id}_STALE"
            lower, upper = self.config.soft_limits_rad[bus_id]
            if not lower <= state.position_rad <= upper:
                return "JOINT_LIMIT"
        except (AttributeError, TypeError, ValueError):
            return f"SERVO_{bus_id}_IO_ERROR"
        return None

    def tick(self) -> dict[str, object]:
        if self.safe_state_reason is not None:
            return self._enter_safe_state(self.safe_state_reason)
        started = self.clock()
        fault = self._timing_fault(started, started)
        if fault:
            return self._enter_safe_state(fault)
        if self._last_tick is not None:
            expected_period = 1.0 / self.config.control_hz
            late_ms = max(0.0, started - self._last_tick - expected_period) * 1000.0
            if late_ms > self.config.max_tick_late_ms:
                return self._enter_safe_state("CONTROL_DEADLINE_MISS")

        try:
            sample = self.imu.read()
        except (OSError, RuntimeError, ValueError, TypeError, IndexError):
            return self._enter_safe_state("IMU_IO_ERROR")
        now = self.clock()
        fault = self._timing_fault(started, now) or self._imu_fault(sample, now)
        if fault:
            return self._enter_safe_state(fault)

        # No target is written until the entire calibrated joint set has been
        # read and validated. A fault on the last ID cannot move earlier IDs.
        feedback: dict[int, ServoState] = {}
        for bus_id in self._command:
            try:
                state = self.servo_bus.read(bus_id)
            except (ConnectionError, OSError, RuntimeError):
                return self._enter_safe_state(f"SERVO_{bus_id}_DISCONNECTED")
            except (ValueError, TypeError, KeyError):
                return self._enter_safe_state(f"SERVO_{bus_id}_IO_ERROR")
            now = self.clock()
            fault = self._timing_fault(started, now) or self._servo_fault(bus_id, state, now)
            if fault:
                return self._enter_safe_state(fault)
            feedback[bus_id] = state

        freshness_deadlines = [(sample.timestamp_s + self.config.imu_timeout_ms / 1000.0,
                                "IMU_STALE")]
        freshness_deadlines.extend(
            (state.timestamp_s + self.config.servo_timeout_ms / 1000.0,
             f"SERVO_{bus_id}_STALE") for bus_id, state in feedback.items()
        )
        for bus_id, target in self._command.items():
            now = self.clock()
            fault = self._timing_fault(started, now)
            if not fault:
                fault = next((reason for deadline, reason in freshness_deadlines
                              if now >= deadline), None)
            if fault:
                return self._enter_safe_state(fault)
            try:
                self.servo_bus.write_position(bus_id, target)
            except (ConnectionError, OSError, RuntimeError):
                return self._enter_safe_state(f"SERVO_{bus_id}_DISCONNECTED")
            except (ValueError, TypeError, KeyError):
                return self._enter_safe_state(f"SERVO_{bus_id}_IO_ERROR")

        # Detect even a final write that exceeded its backend's required bound.
        now = self.clock()
        fault = self._timing_fault(started, now)
        if not fault:
            fault = next((reason for deadline, reason in freshness_deadlines
                          if now >= deadline), None)
        if fault:
            return self._enter_safe_state(fault)
        self._last_tick = started
        return {
            "status": "RUNNING",
            "command_age_ms": (now - self._command_at) * 1000.0,
            "imu_age_ms": (now - sample.timestamp_s) * 1000.0,
            "states": {bus_id: {
                "position_rad": state.position_rad,
                "velocity_rad_s": state.velocity_rad_s,
                "current_a": state.current_a,
                "voltage_v": state.voltage_v,
                "temperature_c": state.temperature_c,
                "latency_ms": state.latency_ms,
                "connected": state.connected,
                "timestamp_s": state.timestamp_s,
            } for bus_id, state in feedback.items()},
        }

    def close(self) -> None:
        try:
            self.servo_bus.torque_off()
        finally:
            try:
                self.servo_bus.close()
            finally:
                self.imu.close()


def run_mock_runtime(config: RuntimeConfig, cycles: int, log_path: Path) -> dict[str, object]:
    if cycles <= 0:
        raise ValueError("cycles must be greater than zero")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        raise FileExistsError(f"runtime log already exists: {log_path}")
    clock = time.monotonic
    bus = MockServoBus(list(config.soft_limits_rad), clock=clock)
    runtime = SafeRuntime(config=config, servo_bus=bus, imu=MockImuBackend(clock=clock), clock=clock)
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
                        "status": "RUNNING",
                        "evidence_level": None,
                        "gate_eligible": False,
                        "config": asdict(config),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            running_cycles = 0
            safe_events = 0
            schedule_start = clock()
            for cycle in range(cycles):
                # Fixed start times include I/O and logging in the 20 ms period.
                remaining = schedule_start + cycle * period - clock()
                if remaining > 0:
                    time.sleep(remaining)
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
                if result["status"] == "SAFE_STATE":
                    break
            status = "SIM_PASS" if running_cycles == cycles and safe_events == 0 else "SIM_FAIL"
            summary = {
                "record_type": "runtime_summary",
                "finished_at": datetime.now().astimezone().isoformat(),
                "status": status,
                "evidence_level": "SIM_PASS" if status == "SIM_PASS" else None,
                "requested_cycles": cycles,
                "running_cycles": running_cycles,
                "safe_events": safe_events,
            }
            handle.write(
                json.dumps(
                    summary,
                    ensure_ascii=False,
                )
                + "\n"
            )
    finally:
        runtime.close()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("log", type=Path)
    parser.add_argument("--backend", choices=("mock",), default="mock")
    parser.add_argument("--cycles", type=int, default=100)
    args = parser.parse_args()
    config = load_runtime_config(args.config, allow_sim_limits=True)
    summary = run_mock_runtime(config, args.cycles, args.log)
    print(json.dumps({"status": summary["status"], "log": str(args.log.resolve())}, indent=2))
    if summary["status"] != "SIM_PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
