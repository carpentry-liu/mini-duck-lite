from dataclasses import replace
import csv
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mini_duck_lite.hardware import MockServoBus
from mini_duck_lite.qualification import SimulatedClock, load_plan, main, run_qualification


ROOT = Path(__file__).resolve().parents[1]


class RecordingBus(MockServoBus):
    def __init__(self, clock, temperature=28.0):
        super().__init__([1], clock=clock)
        self.temperature = temperature
        self.read_count = 0
        self.write_count = 0
        self.writes_after_hot_sample = 0
        self.off_count = 0

    def read(self, bus_id):
        self.read_count += 1
        return replace(super().read(bus_id), temperature_c=self.temperature)

    def write_position(self, bus_id, position_rad):
        self.write_count += 1
        if self.read_count and self.temperature >= 55:
            self.writes_after_hot_sample += 1
        super().write_position(bus_id, position_rad)

    def torque_off(self):
        self.off_count += 1
        super().torque_off()


def run(tmp_path, clock, bus, *, quick=True, plan=None):
    return run_qualification(
        plan=plan or load_plan(ROOT / "config/qualification/h1-c044-c046.json"),
        output_dir=tmp_path,
        sku="STS3215-C044",
        bus_id=1,
        bus=bus,
        backend_name="mock",
        quick=quick,
        clock=clock,
        sleep=clock.sleep,
        timing_mode="simulated",
    )


@pytest.mark.parametrize("temperature", [55.0, 80.0])
def test_overheat_stops_before_any_further_motion_and_archives_failure(tmp_path, temperature):
    clock = SimulatedClock()
    bus = RecordingBus(clock, temperature)
    summary = run(tmp_path, clock, bus)

    assert bus.writes_after_hot_sample == 0
    assert bus.off_count >= 1
    assert summary["status"] == "FAILED"
    assert summary["evidence_level"] == "SIM_FAIL"
    assert summary["failure_reason"] == "TEMPERATURE_LIMIT"
    assert summary["sample_count"] == 1
    assert summary["completed_trajectory_samples"] < summary["planned_trajectory_samples"]
    assert summary["gate_eligible"] is False
    assert json.loads((tmp_path / "summary.json").read_text())["failure_reason"] == "TEMPERATURE_LIMIT"
    assert json.loads((tmp_path / "metadata.json").read_text())["evidence_level"] == "SIM"


def test_full_thermal_run_has_thirty_minutes_of_consistent_virtual_time(tmp_path):
    clock = SimulatedClock()
    bus = RecordingBus(clock)
    summary = run(tmp_path, clock, bus, quick=False)
    with (tmp_path / "samples.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    thermal_times = [float(row["source_timestamp_s"]) for row in rows if row["test"] == "thermal"]
    all_times = [float(row["source_timestamp_s"]) for row in rows]

    assert len(thermal_times) == 90_000
    assert thermal_times[-1] - thermal_times[0] == pytest.approx(1800.0 - 0.02)
    assert all(b - a == pytest.approx(0.02) for a, b in zip(all_times, all_times[1:]))
    assert summary["elapsed_control_seconds"] == pytest.approx(len(rows) / 50)
    assert summary["elapsed_wall_seconds"] < summary["elapsed_control_seconds"]
    assert summary["status"] == "COMPLETED"
    assert summary["evidence_level"] == "SIM_PASS"
    assert summary["timing_mode"] == "simulated"


def test_sampling_uses_absolute_deadlines_without_accumulating_io_time(tmp_path):
    clock = SimulatedClock()

    class SlowBus(RecordingBus):
        def read(self, bus_id):
            clock.now += 0.003
            return super().read(bus_id)

    summary = run(tmp_path, clock, SlowBus(clock))
    with (tmp_path / "samples.csv").open() as handle:
        times = [float(row["source_timestamp_s"]) for row in csv.DictReader(handle)]
    assert summary["status"] == "COMPLETED"
    assert times[-1] - times[0] == pytest.approx((len(times) - 1) / 50)


def test_bus_error_before_first_sample_still_generates_failure_summary(tmp_path):
    clock = SimulatedClock()

    class BrokenBus(RecordingBus):
        def read(self, bus_id):
            raise OSError("disconnected")

    bus = BrokenBus(clock)
    summary = run(tmp_path, clock, bus)
    assert summary["status"] == "FAILED"
    assert summary["sample_count"] == 0
    assert summary["metrics"]["peak_temperature_c"] is None
    assert bus.off_count >= 1
    assert (tmp_path / "summary.json").is_file()


def test_shutdown_errors_preserve_original_failure_and_archive_summary(tmp_path):
    clock = SimulatedClock()

    class BrokenBus(RecordingBus):
        def read(self, bus_id):
            raise OSError("read disconnected")

        def torque_off(self):
            raise OSError("torque shutdown disconnected")

        def close(self):
            raise OSError("close disconnected")

    summary = run(tmp_path, clock, BrokenBus(clock))
    assert summary["status"] == "FAILED"
    assert "read disconnected" in summary["failure_reason"]
    assert len(summary["cleanup_errors"]) == 2
    assert json.loads((tmp_path / "summary.json").read_text()) == summary


def test_overdue_final_read_cannot_pass_a_single_sample_plan(tmp_path):
    clock = SimulatedClock()

    class SlowBus(RecordingBus):
        def read(self, bus_id):
            clock.now += 0.2
            return super().read(bus_id)

    plan = load_plan(ROOT / "config/qualification/h1-c044-c046.json")
    plan["step_tests"]["angles_deg"] = []
    plan["velocity_test"]["repetitions"] = 0
    plan["thermal_test"]["duration_seconds"] = 0.02
    plan["disconnect_test"] = False
    bus = SlowBus(clock)
    summary = run(tmp_path, clock, bus, quick=False, plan=plan)
    assert summary["planned_trajectory_samples"] == 1
    assert summary["evidence_level"] == "SIM_FAIL"
    assert summary["failure_reason"] == "CONTROL_DEADLINE_MISS"
    assert bus.write_count == 1
    assert bus.off_count >= 1


@pytest.mark.parametrize("temperature", [None, float("nan"), float("inf"), 56, -1, True])
def test_invalid_temperature_stop_configuration_is_rejected(tmp_path, temperature):
    plan = load_plan(ROOT / "config/qualification/h1-c044-c046.json")
    plan["stop_temperature_c"] = temperature
    clock = SimulatedClock()
    with pytest.raises(ValueError, match="stop_temperature_c"):
        run(tmp_path, clock, RecordingBus(clock), plan=plan)


def test_qualification_cli_returns_nonzero_for_overheat(tmp_path, capsys):
    class HotBus(MockServoBus):
        def read(self, bus_id):
            return replace(super().read(bus_id), temperature_c=80.0)

    argv = ["mini-duck-qualify", str(ROOT / "config/qualification/h1-c044-c046.json"),
            str(tmp_path), "--sku", "STS3215-C044", "--quick"]
    with patch("sys.argv", argv), patch("mini_duck_lite.qualification.MockServoBus", HotBus):
        with pytest.raises(SystemExit) as error:
            main()
    assert error.value.code == 1
    assert json.loads(capsys.readouterr().out)["evidence_level"] == "SIM_FAIL"
