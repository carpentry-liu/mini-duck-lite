"""Pinned upstream references and the completed G0 smoke contract."""

from __future__ import annotations

from typing import Final


CURRENT_GATE: Final = "H1"
LAST_PASSED_GATE: Final = "H0"
G0_EVIDENCE: Final = "docs/experiments/2026-08-31-g0-upstream-gpu-training.md"
MICRODUCK_RL_COMMIT: Final = "d424a0c899f6b33cbd3daeb279913134349c0b63"
OPEN_DUCK_PLAYGROUND_COMMIT: Final = "b9be205ac64488c23504ca42e5ec790337adeec3"
MUJOCO_COMMIT: Final = "b62c3e886adfcfe220a694408ca8a41cee50b976"

UPSTREAM_REFS: Final = {
    "microduck_rl": {
        "url": "https://github.com/pollen-robotics/microduck_rl",
        "branch": "develop",
        "commit": MICRODUCK_RL_COMMIT,
    },
    "open_duck_playground": {
        "url": "https://github.com/apirrone/Open_Duck_Playground",
        "branch": "main",
        "commit": OPEN_DUCK_PLAYGROUND_COMMIT,
    },
    "mujoco": {
        "url": "https://github.com/google-deepmind/mujoco",
        "branch": "main",
        "commit": MUJOCO_COMMIT,
    },
}

MICRODUCK_TASK_ID: Final = "Mjlab-Velocity-Flat-MicroDuck"
TRAIN_SMOKE_ENV_COUNT: Final = 64
TRAIN_SMOKE_ITERATIONS: Final = 5
