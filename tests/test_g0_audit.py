from __future__ import annotations

from collections.abc import Sequence

from mini_duck_lite.g0 import CommandResult, build_report


def _available(command: str, arguments: Sequence[str]) -> CommandResult:
    del arguments
    return CommandResult(command, True, f"{command} test-version")


def test_audit_reports_prerequisites_without_claiming_gate_passed() -> None:
    report = build_report(_available)

    assert report["current_gate"] == "G0"
    assert report["environment_ready"] is True
    assert report["gate_passed"] is False
    assert set(report["upstream_refs"]) == {
        "microduck_rl",
        "open_duck_playground",
        "mujoco",
    }


def test_gpu_can_be_optional_for_documentation_only_hosts() -> None:
    def without_gpu(command: str, arguments: Sequence[str]) -> CommandResult:
        del arguments
        return CommandResult(command, command != "nvidia-smi", "test")

    report = build_report(without_gpu, require_gpu=False)

    assert report["environment_ready"] is True
    assert report["checks"][2]["available"] is False
