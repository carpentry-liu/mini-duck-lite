#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

export MUJOCO_GL="${MUJOCO_GL:-egl}"

uv run mini-duck-sim \
  --duration 2 \
  --render \
  --output artifacts/g0-first-simulation

printf '\nSummary: %s\n' "$project_root/artifacts/g0-first-simulation/summary.json"
