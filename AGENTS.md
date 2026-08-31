# Mini Duck Lite agent guide

This repository implements the staged Sim2Real plan in `docs/PRD.md`.

## Start every task

1. Read `docs/PROGRESS.md`, `docs/ROADMAP.md`, `docs/ARCHITECTURE.md`, and this file.
2. Confirm the current Gate and its acceptance criteria.
3. Keep the change inside that Gate unless the user explicitly expands scope.

## Non-negotiable rules

- Treat joint order, sign, units, limits, observation layout, action scaling, and IMU frames as versioned Sim2Real contracts.
- Run a short CPU/headless smoke test before any viewer run or long training.
- Do not start long PPO training without explicit approval and a passing smoke test.
- Do not send real actuator commands until watchdog, emergency stop, limits, and staged HIL checks exist.
- Never hide a model or control error by changing rewards first; validate physics and contracts before reward tuning.
- Record important choices in `docs/DECISIONS.md`, current facts in `docs/PROGRESS.md`, and experimental evidence in `docs/experiments/`.
- Keep upstream repositories external and pinned by commit. Do not copy code or assets without recording their license.
- If `E:\tongyuan\pe-next-robot` exists, it is read-only reference material. Never modify it from this project.
- One commit should solve one reviewable problem. Do not mix unrelated refactors or dependency upgrades.
- Completion requires commands, test output, and measured results; avoid unsupported claims such as “basically working.”

## Required checks

```bash
uv sync --all-groups
uv run pytest
MUJOCO_GL=egl uv run mini-duck-sim --duration 2 --render
```

Generated simulation data belongs in `artifacts/` and is not committed. Summaries and selected evidence belong in `docs/experiments/`.
