"""Run reproducible actuator qualification and write CSV/JSON evidence."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
import math
from pathlib import Path
import statistics
import subprocess
import time
from typing import Any, Callable

from mini_duck_lite.hardware import MockServoBus, ServoBus


SAMPLE_FIELDS = (
    "sample",
    "test",
    "sku",
    "bus_id",
    "target_deg",
    "position_deg",
    "error_deg",
    "velocity_deg_s",
    "current_a",
    "voltage_v",
    "temperature_c",
    "latency_ms",
    "connected",
    "source_timestamp_s",
)


class SimulatedClock:
    """A shared monotonic time base for accelerated mock qualification only."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += max(0.0, seconds)


class QualificationStopped(RuntimeError):
    """Stop a run while preserving its samples and failure summary."""


def _validate_plan(plan: dict[str, Any]) -> None:
    if plan.get("schema_version") != "actuator-qualification/v1":
        raise ValueError("unsupported actuator qualification schema")
    if plan.get("gate") != "H1":
        raise ValueError("actuator qualification plan must target H1")
    if plan.get("control_hz") != 50:
        raise ValueError("V0.4 qualification must run at 50 Hz")
    temperature = plan.get("stop_temperature_c")
    if (
        isinstance(temperature, bool)
        or not isinstance(temperature, (int, float))
        or not math.isfinite(temperature)
        or not 0 < temperature <= 55
    ):
        raise ValueError("stop_temperature_c must be finite and within (0, 55]")


def load_plan(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        plan = json.load(handle)
    _validate_plan(plan)
    return plan


def _target_sequence(plan: dict[str, Any], *, quick: bool) -> list[tuple[str, float, int]]:
    control_hz = int(plan["control_hz"])
    step = plan["step_tests"]
    repetitions = 1 if quick else int(step["repetitions"])
    settle_samples = 5 if quick else max(1, round(float(step["settle_seconds"]) * control_hz))
    sequence: list[tuple[str, float, int]] = []
    for angle in step["angles_deg"]:
        for _ in range(repetitions):
            sequence.append(("step", float(angle), settle_samples))
            sequence.append(("step_return", 0.0, settle_samples))

    velocity = plan["velocity_test"]
    velocity_repetitions = 1 if quick else int(velocity["repetitions"])
    velocity_samples = 5 if quick else control_hz
    travel = float(velocity["travel_deg"])
    for _ in range(velocity_repetitions):
        sequence.append(("velocity_out", travel, velocity_samples))
        sequence.append(("velocity_return", -travel, velocity_samples))

    thermal = plan["thermal_test"]
    thermal_seconds = 1.0 if quick else float(thermal["duration_seconds"])
    thermal_samples = max(1, round(thermal_seconds * control_hz))
    amplitude = float(thermal["amplitude_deg"])
    half_period_samples = max(
        1, round(float(thermal["period_seconds"]) * control_hz / 2.0)
    )
    for index in range(thermal_samples):
        target = amplitude if (index // half_period_samples) % 2 == 0 else -amplitude
        sequence.append(("thermal", target, 1))
    return sequence


def _git_state() -> tuple[str | None, bool | None]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--short"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()
        )
        return commit, dirty
    except (OSError, subprocess.SubprocessError):
        return None, None


def run_qualification(
    *,
    plan: dict[str, Any],
    output_dir: Path,
    sku: str,
    bus_id: int,
    bus: ServoBus,
    backend_name: str,
    quick: bool,
    hardware_revision: str = "reference-prototype-a-pre-h1",
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    timing_mode: str = "realtime",
) -> dict[str, Any]:
    _validate_plan(plan)
    if timing_mode not in {"realtime", "simulated"}:
        raise ValueError("timing_mode must be realtime or simulated")
    if timing_mode == "simulated" and (
        backend_name != "mock" or not isinstance(bus, MockServoBus)
    ):
        raise ValueError("simulated timing is restricted to mock hardware")
    output_dir.mkdir(parents=True, exist_ok=True)
    samples_path = output_dir / "samples.csv"
    summary_path = output_dir / "summary.json"
    metadata_path = output_dir / "metadata.json"
    if any(path.exists() for path in (samples_path, summary_path, metadata_path)):
        raise FileExistsError(f"qualification output already exists: {output_dir}")

    git_commit, git_dirty = _git_state()
    metadata = {
        "schema_version": "actuator-qualification-run/v1",
        "started_at": datetime.now().astimezone().isoformat(),
        "gate": "H1",
        "sku": sku,
        "bus_id": bus_id,
        "hardware_revision": hardware_revision,
        "backend": backend_name,
        "quick_mode": quick,
        "control_hz": plan["control_hz"],
        "evidence_level": "SIM" if backend_name == "mock" else "HIL_PENDING",
        "status": "RUNNING",
        "gate_eligible": False,
        "timing_mode": timing_mode,
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "plan": plan,
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    errors_deg: list[float] = []
    latencies_ms: list[float] = []
    currents_a: list[float] = []
    temperatures_c: list[float] = []
    voltages_v: list[float] = []
    disconnected_samples = 0
    sample_index = 0
    failure_reason: str | None = None
    cleanup_errors: list[str] = []
    sequence = _target_sequence(plan, quick=quick)
    planned_samples = sum(count for _, _, count in sequence)
    period = 1.0 / plan["control_hz"]
    wall_started = time.monotonic()
    control_started = clock()
    next_sample_at = control_started + period

    def read_sample():
        nonlocal next_sample_at
        sleep(max(0.0, next_sample_at - clock()))
        if clock() - next_sample_at > period:
            raise QualificationStopped("CONTROL_DEADLINE_MISS")
        state = bus.read(bus_id)
        if clock() - next_sample_at > period:
            raise QualificationStopped("CONTROL_DEADLINE_MISS")
        next_sample_at += period
        return state

    def check_temperature(temperature_c: float) -> None:
        if not math.isfinite(temperature_c):
            raise QualificationStopped("TEMPERATURE_INVALID")
        if temperature_c >= plan["stop_temperature_c"]:
            raise QualificationStopped("TEMPERATURE_LIMIT")

    try:
        with samples_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=SAMPLE_FIELDS)
            writer.writeheader()
            for test_name, target_deg, sample_count in sequence:
                if clock() - next_sample_at > period:
                    raise QualificationStopped("CONTROL_DEADLINE_MISS")
                target_rad = math.radians(target_deg)
                bus.write_position(bus_id, target_rad)
                for _ in range(sample_count):
                    state = read_sample()
                    position_deg = math.degrees(state.position_rad)
                    error_deg = target_deg - position_deg
                    row = {
                        "sample": sample_index,
                        "test": test_name,
                        "sku": sku,
                        "bus_id": bus_id,
                        "target_deg": round(target_deg, 6),
                        "position_deg": round(position_deg, 6),
                        "error_deg": round(error_deg, 6),
                        "velocity_deg_s": round(
                            math.degrees(state.velocity_rad_s), 6
                        ),
                        "current_a": round(state.current_a, 6),
                        "voltage_v": round(state.voltage_v, 6),
                        "temperature_c": round(state.temperature_c, 6),
                        "latency_ms": round(state.latency_ms, 6),
                        "connected": state.connected,
                        "source_timestamp_s": round(state.timestamp_s, 6),
                    }
                    writer.writerow(row)
                    errors_deg.append(error_deg)
                    latencies_ms.append(state.latency_ms)
                    currents_a.append(state.current_a)
                    temperatures_c.append(state.temperature_c)
                    voltages_v.append(state.voltage_v)
                    disconnected_samples += int(not state.connected)
                    sample_index += 1
                    check_temperature(state.temperature_c)
                    if not state.connected:
                        raise QualificationStopped("SERVO_DISCONNECTED")
            if plan.get("disconnect_test") and isinstance(bus, MockServoBus):
                bus.set_connected(bus_id, False)
                disconnected = read_sample()
                writer.writerow(
                    {
                        "sample": sample_index,
                        "test": "disconnect",
                        "sku": sku,
                        "bus_id": bus_id,
                        "target_deg": 0.0,
                        "position_deg": round(
                            math.degrees(disconnected.position_rad), 6
                        ),
                        "error_deg": 0.0,
                        "velocity_deg_s": 0.0,
                        "current_a": round(disconnected.current_a, 6),
                        "voltage_v": round(disconnected.voltage_v, 6),
                        "temperature_c": round(disconnected.temperature_c, 6),
                        "latency_ms": round(disconnected.latency_ms, 6),
                        "connected": disconnected.connected,
                        "source_timestamp_s": round(disconnected.timestamp_s, 6),
                    }
                )
                disconnected_samples += 1
                voltages_v.append(disconnected.voltage_v)
                sample_index += 1
                check_temperature(disconnected.temperature_c)
                bus.set_connected(bus_id, True)
                recovered = read_sample()
                writer.writerow(
                    {
                        "sample": sample_index,
                        "test": "reconnect",
                        "sku": sku,
                        "bus_id": bus_id,
                        "target_deg": 0.0,
                        "position_deg": round(math.degrees(recovered.position_rad), 6),
                        "error_deg": 0.0,
                        "velocity_deg_s": round(
                            math.degrees(recovered.velocity_rad_s), 6
                        ),
                        "current_a": round(recovered.current_a, 6),
                        "voltage_v": round(recovered.voltage_v, 6),
                        "temperature_c": round(recovered.temperature_c, 6),
                        "latency_ms": round(recovered.latency_ms, 6),
                        "connected": recovered.connected,
                        "source_timestamp_s": round(recovered.timestamp_s, 6),
                    }
                )
                latencies_ms.append(recovered.latency_ms)
                currents_a.append(recovered.current_a)
                temperatures_c.append(recovered.temperature_c)
                voltages_v.append(recovered.voltage_v)
                sample_index += 1
                check_temperature(recovered.temperature_c)
                if not recovered.connected:
                    raise QualificationStopped("SERVO_RECONNECT_FAILED")
    except QualificationStopped as error:
        failure_reason = str(error)
    except (OSError, RuntimeError, ValueError) as error:
        failure_reason = f"SERVO_IO_ERROR: {type(error).__name__}: {error}"
    finally:
        # A broken transport may also reject shutdown. Preserve the original
        # failure and still archive evidence; never imply torque was removed.
        for name, operation in (("torque_off", bus.torque_off), ("close", bus.close)):
            try:
                operation()
            except Exception as error:
                cleanup_errors.append(f"{name}: {type(error).__name__}: {error}")
        if cleanup_errors and failure_reason is None:
            failure_reason = "SHUTDOWN_FAILED"

    completed = failure_reason is None
    summary = {
        **metadata,
        "status": "COMPLETED" if completed else "FAILED",
        "evidence_level": (
            ("SIM_PASS" if completed else "SIM_FAIL")
            if backend_name == "mock"
            else "HIL_PENDING"
        ),
        "gate_eligible": completed and backend_name != "mock" and not quick,
        "failure_reason": failure_reason,
        "cleanup_errors": cleanup_errors,
        "finished_at": datetime.now().astimezone().isoformat(),
        "sample_count": sample_index,
        "planned_trajectory_samples": planned_samples,
        "completed_trajectory_samples": len(errors_deg),
        "elapsed_control_seconds": clock() - control_started,
        "elapsed_wall_seconds": time.monotonic() - wall_started,
        "metrics": {
            "tracking_rmse_deg": (
                (sum(error * error for error in errors_deg) / len(errors_deg)) ** 0.5
                if errors_deg else None
            ),
            "mean_latency_ms": statistics.fmean(latencies_ms) if latencies_ms else None,
            "peak_current_a": max(currents_a, default=None),
            "minimum_voltage_v": min(voltages_v, default=None),
            "peak_temperature_c": max(temperatures_c, default=None),
            "disconnected_samples": disconnected_samples,
            "packet_loss_fraction": disconnected_samples / sample_index if sample_index else None,
        },
        "artifacts": {
            "samples_csv": str(samples_path.resolve()),
            "metadata_json": str(metadata_path.resolve()),
        },
        "warning": (
            "Mock data validates the logger only; it cannot pass H1."
            if backend_name == "mock"
            else None
        ),
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--sku", required=True, choices=("STS3215-C044", "STS3215-C046"))
    parser.add_argument("--bus-id", type=int, default=1)
    parser.add_argument("--backend", choices=("mock",), default="mock")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument(
        "--hardware-revision", default="reference-prototype-a-pre-h1"
    )
    args = parser.parse_args()

    plan = load_plan(args.plan)
    clock = SimulatedClock()
    bus = MockServoBus([args.bus_id], clock=clock)
    summary = run_qualification(
        plan=plan,
        output_dir=args.output_dir,
        sku=args.sku,
        bus_id=args.bus_id,
        bus=bus,
        backend_name=args.backend,
        quick=args.quick,
        hardware_revision=args.hardware_revision,
        clock=clock,
        sleep=clock.sleep,
        timing_mode="simulated",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["status"] != "COMPLETED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
