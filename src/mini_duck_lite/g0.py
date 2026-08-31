"""Audit local prerequisites for the G0 upstream reproduction."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import platform
import shutil
import subprocess
import sys
from typing import Callable, Sequence

from mini_duck_lite.upstream import (
    CURRENT_GATE,
    G0_EVIDENCE,
    LAST_PASSED_GATE,
    UPSTREAM_REFS,
)


@dataclass(frozen=True)
class CommandResult:
    """Result of one prerequisite probe."""

    name: str
    available: bool
    detail: str


Runner = Callable[[str, Sequence[str]], CommandResult]


def _probe(command: str, arguments: Sequence[str]) -> CommandResult:
    executable = shutil.which(command)
    if executable is None:
        return CommandResult(command, False, "not found")

    try:
        completed = subprocess.run(
            [executable, *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return CommandResult(command, False, f"{type(error).__name__}: {error}")

    output = (completed.stdout or completed.stderr).strip().splitlines()
    detail = output[0] if output else f"exit={completed.returncode}"
    return CommandResult(command, completed.returncode == 0, detail)


def build_report(runner: Runner = _probe, *, require_gpu: bool = True) -> dict[str, object]:
    """Return a machine-readable environment audit without changing the host."""

    checks = [
        runner("git", ("--version",)),
        runner("uv", ("--version",)),
        runner(
            "nvidia-smi",
            (
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader",
            ),
        ),
    ]
    required = checks if require_gpu else checks[:2]
    return {
        "project": "Mini Duck Physical AI Platform",
        "project_version": "0.4",
        "current_gate": CURRENT_GATE,
        "last_passed_gate": LAST_PASSED_GATE,
        "gate_passed": False,
        "g0_evidence": G0_EVIDENCE,
        "scope": "local prerequisites only; this command does not execute the current H1",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "checks": [asdict(check) for check in checks],
        "environment_ready": all(check.available for check in required),
        "upstream_refs": UPSTREAM_REFS,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-no-gpu",
        action="store_true",
        help="Do not fail the local prerequisite audit when nvidia-smi is unavailable.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(require_gpu=not args.allow_no_gpu)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["environment_ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
