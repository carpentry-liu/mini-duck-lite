"""SIM/HIL/REAL evidence contracts for honest Physical AI progress."""

from __future__ import annotations

from enum import Enum
from typing import Any


class EvidenceLevel(str, Enum):
    SIM_PASS = "SIM_PASS"
    HIL_PASS = "HIL_PASS"
    REAL_PASS = "REAL_PASS"


def can_transition(previous: EvidenceLevel | None, current: EvidenceLevel) -> bool:
    """Allow retries at one level and forward movement one level at a time."""

    if previous is None:
        return current is EvidenceLevel.SIM_PASS
    order = {
        EvidenceLevel.SIM_PASS: 0,
        EvidenceLevel.HIL_PASS: 1,
        EvidenceLevel.REAL_PASS: 2,
    }
    return order[current] in {order[previous], order[previous] + 1}


def validate_evidence(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        level = EvidenceLevel(record.get("level"))
    except ValueError:
        return ["level must be SIM_PASS, HIL_PASS, or REAL_PASS"]

    for field in ("git_commit", "config_ref", "telemetry_ref"):
        if not record.get(field):
            errors.append(f"{field} is required")

    attempts = record.get("attempts")
    successes = record.get("successes")
    if not isinstance(attempts, int) or attempts <= 0:
        errors.append("attempts must be a positive integer")
    if not isinstance(successes, int) or successes < 0:
        errors.append("successes must be a non-negative integer")
    if isinstance(attempts, int) and isinstance(successes, int) and successes > attempts:
        errors.append("successes cannot exceed attempts")

    if level in {EvidenceLevel.HIL_PASS, EvidenceLevel.REAL_PASS}:
        if not record.get("hardware_revision"):
            errors.append("hardware_revision is required for HIL/REAL")
        if not record.get("video_ref"):
            errors.append("video_ref is required for HIL/REAL")
    if level is EvidenceLevel.REAL_PASS:
        reasons = record.get("failure_reasons")
        if not isinstance(reasons, list):
            errors.append("failure_reasons must be a list for REAL_PASS")
    return errors
