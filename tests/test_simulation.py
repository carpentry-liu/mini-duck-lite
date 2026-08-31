from pathlib import Path

from mini_duck_lite.simulation import run_simulation


def test_headless_smoke_simulation(tmp_path: Path) -> None:
    summary = run_simulation(duration=0.1, output=tmp_path, tether=True)

    assert summary["passed"] is True
    assert summary["finite_state"] is True
    assert summary["joint_count"] == 10
    assert summary["actuator_count"] == 10
    assert summary["telemetry_samples"] == 5
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "telemetry.jsonl").is_file()
