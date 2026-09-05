from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/walk_acceptance.py"
SPEC = importlib.util.spec_from_file_location("walk_acceptance", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def assess(lateral: list[float], yaw: list[float], **overrides: float) -> dict[str, object]:
    inputs = dict(no_fall_fraction=1.0, forward_velocity_rmse=0.0,
                  mean_forward_velocity=0.25, command_x=0.25,
                  mean_lateral_errors=lateral, mean_yaw_errors=yaw, nan_events=0)
    inputs.update(overrides)
    return MODULE.assess_walk_acceptance(**inputs)


@pytest.mark.parametrize("lateral,yaw", [([0.4, -0.4], [0.0, 0.0]),
                                        ([0.0, 0.0], [0.8, -0.8])])
def test_persistent_opposite_environment_errors_do_not_cancel(lateral, yaw) -> None:
    assert assess(lateral, yaw)["passed"] is False


def test_periodic_sway_within_each_environment_is_allowed() -> None:
    trace = [0.4, -0.4] * 225
    temporal_mean = sum(trace) / len(trace)
    assert assess([temporal_mean, temporal_mean], [0.0, 0.0])["passed"] is True


def test_nonzero_yaw_tracks_command_rather_than_zero() -> None:
    command = 0.5
    assert assess([0.0, 0.0], [0.5 - command, 0.5 - command])["passed"] is True
    assert assess([0.0, 0.0], [0.0 - command, 0.0 - command])["passed"] is False


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_tracking_errors_fail_closed(bad: float) -> None:
    assert assess([bad, 0.0], [0.0, 0.0])["passed"] is False


def test_falls_and_forward_tracking_still_gate_acceptance() -> None:
    assert assess([0.0], [0.0], no_fall_fraction=0.94)["passed"] is False
    assert assess([0.0], [0.0], forward_velocity_rmse=0.13)["passed"] is False
