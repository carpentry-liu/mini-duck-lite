"""Dependency-free acceptance rules for fixed-command walking rollouts."""

from __future__ import annotations

import math
from collections.abc import Sequence


def assess_walk_acceptance(
    *,
    no_fall_fraction: float,
    forward_velocity_rmse: float,
    mean_forward_velocity: float,
    command_x: float,
    mean_lateral_errors: Sequence[float],
    mean_yaw_errors: Sequence[float],
    nan_events: int,
) -> dict[str, object]:
    """Assess time-averaged errors without cancelling different environments.

    Each sequence contains one signed temporal mean per environment, relative
    to that environment's command. Periodic sway can cancel within a rollout;
    persistent opposite errors in different rollouts cannot cancel each other.
    """
    if not mean_lateral_errors or len(mean_lateral_errors) != len(mean_yaw_errors):
        raise ValueError("tracking errors must cover the same nonempty environments")
    lateral_error = sum(abs(value) for value in mean_lateral_errors) / len(mean_lateral_errors)
    yaw_error = sum(abs(value) for value in mean_yaw_errors) / len(mean_yaw_errors)
    finite = all(math.isfinite(value) for value in (
        no_fall_fraction, forward_velocity_rmse, mean_forward_velocity,
        command_x, *mean_lateral_errors, *mean_yaw_errors,
    ))
    passed = (
        finite
        and no_fall_fraction >= 0.95
        and forward_velocity_rmse <= 0.12
        and abs(mean_forward_velocity - command_x) <= 0.10
        and yaw_error <= 0.15
        and lateral_error <= 0.05
        and nan_events == 0
    )
    return {
        "passed": passed,
        "mean_absolute_environment_net_yaw_error_radps": yaw_error,
        "mean_absolute_environment_net_lateral_error_mps": lateral_error,
        "criteria": {
            "no_fall_environment_fraction_min": 0.95,
            "forward_velocity_rmse_mps_max": 0.12,
            "mean_forward_velocity_tolerance_mps": 0.10,
            "mean_absolute_environment_net_yaw_error_radps_max": 0.15,
            "mean_absolute_environment_net_lateral_error_mps_max": 0.05,
            "nan_events_max": 0,
        },
    }
