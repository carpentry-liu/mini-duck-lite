from __future__ import annotations

from pathlib import Path

import pytest

from mini_duck_lite.manifest import audit_manifest, load_manifest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def ready_manifest() -> dict:
    manifest = load_manifest(ROOT / "config/hardware/reference-prototype-a.json")
    manifest["actuators"]["selection_state"] = "HIL_PASS"
    for candidate in manifest["actuators"]["candidates"]:
        candidate["measurement_state"] = "HIL_PASS"
    for bus_id, joint in enumerate(manifest["joints"], 1):
        joint.update(
            bus_id=bus_id,
            actuator_sku="STS3215-C044",
            soft_limit_rad=[-1.0, 1.0],
        )
    manifest["imu"]["calibration_state"] = "HIL_PASS"
    manifest["power"].update(
        full_body_peak_current_a=5.0, measurement_state="HIL_PASS"
    )
    return manifest


def test_measured_manifest_is_ready(ready_manifest: dict) -> None:
    report = audit_manifest(ready_manifest)
    assert report["runtime_ready"] is True
    assert report["runtime_blockers"] == []


@pytest.mark.parametrize(
    "current", [None, "TBD_MEASURE", 0, -1, float("nan"), float("inf"), True]
)
def test_unknown_or_invalid_current_blocks_runtime(ready_manifest: dict, current) -> None:
    ready_manifest["power"]["full_body_peak_current_a"] = current
    report = audit_manifest(ready_manifest)
    assert report["runtime_ready"] is False
    assert any("peak current" in item for item in report["runtime_blockers"])


@pytest.mark.parametrize("state", [None, "TBD_MEASURE", "SIM_PASS"])
def test_numeric_current_also_requires_hil_measurement(
    ready_manifest: dict, state
) -> None:
    ready_manifest["power"]["measurement_state"] = state
    report = audit_manifest(ready_manifest)
    assert report["runtime_ready"] is False
    assert "full-body peak current measurement has not passed HIL" in report["runtime_blockers"]


@pytest.mark.parametrize(
    "limits",
    [
        [float("nan"), 1],
        [-1, float("nan")],
        [float("-inf"), 1],
        [-1, float("inf")],
        [False, 1],
        [1, 1],
        [1, -1],
    ],
)
def test_nonfinite_or_invalid_soft_limits_block_runtime(
    ready_manifest: dict, limits
) -> None:
    ready_manifest["joints"][0]["soft_limit_rad"] = limits
    report = audit_manifest(ready_manifest)
    assert report["runtime_ready"] is False
    assert any("soft_limit_rad" in item for item in report["runtime_blockers"])


@pytest.mark.parametrize("bus_id", [-1, 254, 255, True, 1.0, None])
def test_invalid_servo_id_blocks_runtime(ready_manifest: dict, bus_id) -> None:
    ready_manifest["joints"][0]["bus_id"] = bus_id
    assert audit_manifest(ready_manifest)["runtime_ready"] is False


@pytest.mark.parametrize("bus_id", [0, 253])
def test_servo_id_range_includes_both_endpoints(ready_manifest: dict, bus_id: int) -> None:
    ready_manifest["joints"][0]["bus_id"] = bus_id
    assert audit_manifest(ready_manifest)["runtime_ready"] is True
