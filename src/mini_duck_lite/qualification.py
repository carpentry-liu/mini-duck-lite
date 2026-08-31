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
from typing import Any

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


def load_plan(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        plan = json.load(handle)
    if plan.get("schema_version") != "actuator-qualification/v1":
        raise ValueError("unsupported actuator qualification schema")
    if plan.get("gate") != "H1":
        raise ValueError("actuator qualification plan must target H1")
    if plan.get("control_hz") != 50:
        raise ValueError("V0.4 qualification must run at 50 Hz")
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
) -> dict[str, Any]:
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
        "evidence_level": "SIM_PASS" if backend_name == "mock" else "HIL_PENDING",
        "gate_eligible": backend_name != "mock" and not quick,
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

    try:
        with samples_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=SAMPLE_FIELDS)
            writer.writeheader()
            for test_name, target_deg, sample_count in _target_sequence(
                plan, quick=quick
            ):
                target_rad = math.radians(target_deg)
                bus.write_position(bus_id, target_rad)
                for _ in range(sample_count):
                    state = bus.read(bus_id)
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
            if plan.get("disconnect_test") and isinstance(bus, MockServoBus):
                bus.set_connected(bus_id, False)
                disconnected = bus.read(bus_id)
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
                bus.set_connected(bus_id, True)
                recovered = bus.read(bus_id)
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
    finally:
        bus.torque_off()
        bus.close()

    summary = {
        **metadata,
        "finished_at": datetime.now().astimezone().isoformat(),
        "sample_count": sample_index,
        "metrics": {
            "tracking_rmse_deg": (
                sum(error * error for error in errors_deg) / len(errors_deg)
            )
            ** 0.5,
            "mean_latency_ms": statistics.fmean(latencies_ms),
            "peak_current_a": max(currents_a),
            "minimum_voltage_v": min(voltages_v),
            "peak_temperature_c": max(temperatures_c),
            "disconnected_samples": disconnected_samples,
            "packet_loss_fraction": disconnected_samples / sample_index,
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
    bus = MockServoBus([args.bus_id])
    summary = run_qualification(
        plan=plan,
        output_dir=args.output_dir,
        sku=args.sku,
        bus_id=args.bus_id,
        bus=bus,
        backend_name=args.backend,
        quick=args.quick,
        hardware_revision=args.hardware_revision,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
