from __future__ import annotations

from pathlib import Path

from mini_duck_lite.upstream import (
    MICRODUCK_RL_COMMIT,
    MICRODUCK_TASK_ID,
    TRAIN_SMOKE_ENV_COUNT,
    TRAIN_SMOKE_ITERATIONS,
)


ROOT = Path(__file__).resolve().parents[1]


def test_required_v04_context_documents_exist() -> None:
    required = (
        "AGENTS.md",
        "docs/PRD.md",
        "docs/ARCHITECTURE.md",
        "docs/INTERFACES.md",
        "docs/ROADMAP.md",
        "docs/PROGRESS.md",
        "docs/HARDWARE_DEPLOYMENT.md",
        "docs/WSL2_TRAINING.md",
    )
    assert all((ROOT / path).is_file() for path in required)


def test_current_h1_does_not_ship_an_unverified_custom_robot_model() -> None:
    assert not list((ROOT / "src").rglob("*.xml"))
    assert not (ROOT / "src/mini_duck_lite/simulation.py").exists()


def test_hardware_first_configs_exist() -> None:
    required = (
        "config/hardware/reference-prototype-a.json",
        "config/qualification/h1-c044-c046.json",
        "config/runtime/mock-10dof.json",
        "config/policy/policy-contract-v1.template.json",
    )
    assert all((ROOT / path).is_file() for path in required)


def test_upstream_script_matches_the_versioned_smoke_contract() -> None:
    script = (ROOT / "scripts/run_g0_upstream_smoke.sh").read_text(encoding="utf-8")

    assert MICRODUCK_RL_COMMIT in script
    assert MICRODUCK_TASK_ID in script
    assert 'grep -Fq "$task_id"' in script
    assert f"--env.scene.num-envs {TRAIN_SMOKE_ENV_COUNT}" in script
    assert f"--agent.max_iterations {TRAIN_SMOKE_ITERATIONS}" in script


def test_walk_training_script_has_reproducible_logging_contract() -> None:
    script = (ROOT / "scripts/run_upstream_walk_training.sh").read_text(
        encoding="utf-8"
    )

    assert MICRODUCK_RL_COMMIT in script
    assert MICRODUCK_TASK_ID in script
    assert "readonly default_envs=4096" in script
    assert "readonly default_iterations=4000" in script
    assert "export WANDB_MODE=offline" in script
    assert "nvidia-smi" in script
    assert 'tee "$train_log"' in script
    assert 'printf \'command=\'' in script
    assert "--agent.run_name" in script
    assert "--agent.seed" in script
    assert 'final_status="interrupted"' in script


def test_walk_evaluator_uses_fixed_commands_and_quantitative_acceptance() -> None:
    script = (ROOT / "scripts/evaluate_upstream_walk.py").read_text(
        encoding="utf-8"
    )

    assert MICRODUCK_RL_COMMIT in script
    assert MICRODUCK_TASK_ID in script
    assert 'env_cfg.events.pop("push_robot", None)' in script
    assert 'get_term("fell_over")' in script
    assert 'get_term("nan_state")' in script
    assert '"linear_velocity_rmse_mps"' in script
    assert '"no_fall_environment_fraction"' in script
    assert '"forward_velocity_rmse_mps_max"' in script
    assert '"absolute_mean_yaw_velocity_radps_max"' in script
    assert '"absolute_mean_lateral_velocity_mps_max"' in script
    assert "VideoRecorder" in script
    assert 'render_mode="rgb_array"' in script
    assert "default=1280" in script
    assert "default=720" in script
