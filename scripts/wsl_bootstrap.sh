#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

if ! command -v uv >/dev/null 2>&1; then
  printf 'uv is required. Install it from https://docs.astral.sh/uv/\n' >&2
  exit 1
fi

uv sync --all-groups
uv run pytest
uv run mini-duck-g0

printf '\nLocal prerequisites are ready for the upstream G0 reproduction.\n'
