#!/usr/bin/env bash
set -euo pipefail

readonly expected_commit="d424a0c899f6b33cbd3daeb279913134349c0b63"
readonly task_id="Mjlab-Velocity-Flat-MicroDuck"

usage() {
  printf 'Usage: %s <microduck_rl_checkout> [--train-smoke]\n' "$0" >&2
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 2
fi

checkout="$1"
mode="${2:-}"
if [[ -n "$mode" && "$mode" != "--train-smoke" ]]; then
  usage
  exit 2
fi

if [[ ! -d "$checkout/.git" ]]; then
  printf 'Not a git checkout: %s\n' "$checkout" >&2
  exit 1
fi

actual_commit="$(git -C "$checkout" rev-parse HEAD)"
if [[ "$actual_commit" != "$expected_commit" ]]; then
  printf 'Microduck RL commit mismatch. Expected %s, got %s\n' \
    "$expected_commit" "$actual_commit" >&2
  exit 1
fi

if [[ -n "$(git -C "$checkout" status --short)" ]]; then
  printf 'Microduck RL checkout must be clean before evidence collection.\n' >&2
  exit 1
fi

cd "$checkout"
uv sync

# mjlab 1.3.0's `list-envs` currently returns the number of registered tasks
# from main(). The generated console entry point forwards that value to
# sys.exit(), so a healthy non-empty registry has a non-zero process status.
# Validate the required task in the rendered registry instead of treating that
# upstream status as a failure.
set +e
registry_output="$(uv run list-envs 2>&1)"
registry_status=$?
set -e
printf '%s\n' "$registry_output"
if ! grep -Fq "$task_id" <<<"$registry_output"; then
  printf 'Required task is missing from the registry: %s\n' "$task_id" >&2
  exit 1
fi
if [[ $registry_status -ne 0 ]]; then
  printf '\nRegistry command returned %s after listing tasks; required task is present.\n' \
    "$registry_status"
fi

uv run --with pytest pytest tests/

if [[ "$mode" == "--train-smoke" ]]; then
  uv run train "$task_id" \
    --env.scene.num-envs 64 \
    --agent.max_iterations 5
else
  printf '\nTraining smoke skipped. Re-run with --train-smoke after reviewing registry/tests.\n'
fi

printf '\nRegistry and CPU checks completed at pinned commit %s.\n' "$actual_commit"
printf 'This command does not run checkpoint viewer/policy; record that verification separately.\n'
