from __future__ import annotations

from pathlib import Path

from mini_duck_lite.upstream import (
    MICRODUCK_RL_COMMIT,
    MICRODUCK_TASK_ID,
    TRAIN_SMOKE_ENV_COUNT,
    TRAIN_SMOKE_ITERATIONS,
)


ROOT = Path(__file__).resolve().parents[1]


def test_required_v03_context_documents_exist() -> None:
    required = (
        "AGENTS.md",
        "docs/PRD.md",
        "docs/ARCHITECTURE.md",
        "docs/INTERFACES.md",
        "docs/ROADMAP.md",
        "docs/PROGRESS.md",
    )
    assert all((ROOT / path).is_file() for path in required)


def test_current_g0_does_not_ship_a_custom_robot_model() -> None:
    assert not list((ROOT / "src").rglob("*.xml"))
    assert not (ROOT / "src/mini_duck_lite/simulation.py").exists()


def test_upstream_script_matches_the_versioned_smoke_contract() -> None:
    script = (ROOT / "scripts/run_g0_upstream_smoke.sh").read_text(encoding="utf-8")

    assert MICRODUCK_RL_COMMIT in script
    assert MICRODUCK_TASK_ID in script
    assert 'grep -Fq "$task_id"' in script
    assert f"--env.scene.num-envs {TRAIN_SMOKE_ENV_COUNT}" in script
    assert f"--agent.max_iterations {TRAIN_SMOKE_ITERATIONS}" in script
