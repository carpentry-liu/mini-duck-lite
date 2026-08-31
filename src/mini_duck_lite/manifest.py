"""Hardware manifest validation for the V0.4 Hardware-First gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "hardware-manifest/v1"
PLATFORM_VERSION = "0.4"
JOINT_ORDER = (
    "left_hip_yaw",
    "left_hip_roll",
    "left_hip_pitch",
    "left_knee",
    "left_ankle",
    "right_hip_yaw",
    "right_hip_roll",
    "right_hip_pitch",
    "right_knee",
    "right_ankle",
)
REQUIRED_CANDIDATE_SKUS = {"STS3215-C044", "STS3215-C046"}


class ManifestError(ValueError):
    """Raised when a hardware manifest violates a fail-closed contract."""


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ManifestError("hardware manifest must be a JSON object")
    return data


def audit_manifest(data: dict[str, Any]) -> dict[str, Any]:
    """Validate identity fields and report whether real runtime may start."""

    errors: list[str] = []
    blockers: list[str] = []

    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if data.get("platform_version") != PLATFORM_VERSION:
        errors.append(f"platform_version must be {PLATFORM_VERSION}")
    if not data.get("hardware_revision"):
        errors.append("hardware_revision is required")
    if data.get("qualification_gate") != "H1":
        errors.append("qualification_gate must be H1")

    embodiment = data.get("embodiment", {})
    if embodiment.get("active_joint_count") != len(JOINT_ORDER):
        errors.append("embodiment.active_joint_count must be 10")
    if tuple(embodiment.get("joint_order", ())) != JOINT_ORDER:
        errors.append("embodiment.joint_order does not match the V0.4 contract")

    candidates = data.get("actuators", {}).get("candidates", [])
    candidate_skus = {candidate.get("sku") for candidate in candidates}
    candidate_states = {
        candidate.get("sku"): candidate.get("measurement_state")
        for candidate in candidates
    }
    missing_skus = REQUIRED_CANDIDATE_SKUS - candidate_skus
    if missing_skus:
        errors.append(f"missing actuator candidates: {sorted(missing_skus)}")
    for candidate in candidates:
        sku = candidate.get("sku", "<unknown>")
        if not candidate.get("gear_ratio"):
            errors.append(f"{sku} must include a full gear ratio")
        if candidate.get("measurement_state") not in {"TBD_MEASURE", "HIL_PASS"}:
            errors.append(f"{sku}.measurement_state must be TBD_MEASURE or HIL_PASS")

    imu = data.get("imu", {})
    if imu.get("primary") != "BNO085":
        errors.append("V0.4 new-build primary IMU must be BNO085")
    if "BNO055" not in imu.get("compatibility", []):
        errors.append("BNO055 must remain an explicit compatibility backend")

    joints = data.get("joints", [])
    if [joint.get("name") for joint in joints] != list(JOINT_ORDER):
        errors.append("joints must follow embodiment.joint_order exactly")

    selection_state = data.get("actuators", {}).get("selection_state")
    if selection_state != "HIL_PASS":
        blockers.append("actuator selection requires H1 C044/C046 measurements")

    bus_ids: list[int] = []
    for joint in joints:
        name = joint.get("name", "<unknown>")
        bus_id = joint.get("bus_id")
        if not isinstance(bus_id, int):
            blockers.append(f"{name}.bus_id is TBD_MEASURE")
        else:
            bus_ids.append(bus_id)
        limits = joint.get("soft_limit_rad")
        if (
            not isinstance(limits, list)
            or len(limits) != 2
            or not all(isinstance(value, (int, float)) for value in limits)
            or limits[0] >= limits[1]
        ):
            blockers.append(f"{name}.soft_limit_rad is not calibrated")
        joint_sku = joint.get("actuator_sku")
        if joint_sku is None:
            blockers.append(f"{name}.actuator_sku is not assigned")
        elif joint_sku not in candidate_skus:
            errors.append(f"{name}.actuator_sku is not a qualified candidate")
        elif candidate_states[joint_sku] != "HIL_PASS":
            blockers.append(f"{name}.actuator_sku has not passed HIL")

    if len(bus_ids) != len(set(bus_ids)):
        errors.append("joint bus IDs must be unique")
    if imu.get("calibration_state") != "HIL_PASS":
        blockers.append("BNO085 calibration has not passed HIL")
    if data.get("power", {}).get("full_body_peak_current_a") is None:
        blockers.append("full-body peak current is TBD_MEASURE")

    valid = not errors
    return {
        "schema_version": SCHEMA_VERSION,
        "platform_version": PLATFORM_VERSION,
        "hardware_revision": data.get("hardware_revision"),
        "valid": valid,
        "runtime_ready": valid and not blockers,
        "errors": errors,
        "runtime_blockers": blockers,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    report = audit_manifest(load_manifest(args.manifest))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
