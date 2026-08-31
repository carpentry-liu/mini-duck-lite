#!/usr/bin/env bash
set -euo pipefail

readonly expected_commit="d424a0c899f6b33cbd3daeb279913134349c0b63"
readonly task_id="Mjlab-Velocity-Flat-MicroDuck"
readonly default_envs=4096
readonly default_iterations=4000
readonly default_seed=42

usage() {
  printf 'Usage: %s <microduck_rl_checkout> <artifact_dir> [--envs N] [--iterations N] [--seed N] [--run-name NAME]\n' "$0" >&2
}

if [[ $# -lt 2 ]]; then
  usage
  exit 2
fi

checkout="$1"
artifact_dir="$2"
shift 2

envs="$default_envs"
iterations="$default_iterations"
seed="$default_seed"
run_name="walk-baseline-$(date +%Y%m%d-%H%M%S)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --envs)
      envs="${2:-}"
      shift 2
      ;;
    --iterations)
      iterations="${2:-}"
      shift 2
      ;;
    --seed)
      seed="${2:-}"
      shift 2
      ;;
    --run-name)
      run_name="${2:-}"
      shift 2
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

for value_name in envs iterations seed; do
  value="${!value_name}"
  if [[ ! "$value" =~ ^[0-9]+$ ]]; then
    printf '%s must be a non-negative integer, got: %s\n' "$value_name" "$value" >&2
    exit 2
  fi
done
if [[ "$envs" -eq 0 || "$iterations" -eq 0 ]]; then
  printf 'envs and iterations must be greater than zero.\n' >&2
  exit 2
fi
if [[ ! "$run_name" =~ ^[A-Za-z0-9._-]+$ ]]; then
  printf 'run-name may contain only letters, digits, dot, underscore, and hyphen.\n' >&2
  exit 2
fi

for required_command in git uv nvidia-smi; do
  if ! command -v "$required_command" >/dev/null 2>&1; then
    printf 'Required command is unavailable: %s\n' "$required_command" >&2
    exit 1
  fi
done

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
  printf 'Microduck RL checkout must be clean before training.\n' >&2
  exit 1
fi

mkdir -p "$artifact_dir"
artifact_dir="$(cd "$artifact_dir" && pwd)"
manifest="$artifact_dir/manifest.txt"
train_log="$artifact_dir/train.log"
gpu_log="$artifact_dir/gpu.csv"

if [[ -e "$train_log" || -e "$gpu_log" ]]; then
  printf 'Artifact directory already contains training logs: %s\n' "$artifact_dir" >&2
  exit 1
fi

export PYTHONUNBUFFERED=1
export UV_HTTP_TIMEOUT=600
export WANDB_MODE=offline

train_command=(
  uv run train "$task_id"
  --env.scene.num-envs "$envs"
  --agent.max_iterations "$iterations"
  --agent.run_name "$run_name"
  --agent.seed "$seed"
)

{
  printf 'status=running\n'
  printf 'started_at=%s\n' "$(date --iso-8601=seconds)"
  printf 'task_id=%s\n' "$task_id"
  printf 'upstream_checkout=%s\n' "$(cd "$checkout" && pwd)"
  printf 'upstream_commit=%s\n' "$actual_commit"
  printf 'environment_count=%s\n' "$envs"
  printf 'max_iterations=%s\n' "$iterations"
  printf 'seed=%s\n' "$seed"
  printf 'run_name=%s\n' "$run_name"
  printf 'wandb_mode=%s\n' "$WANDB_MODE"
  printf 'uv_version=%s\n' "$(uv --version)"
  printf 'python_version=%s\n' "$(cd "$checkout" && uv run python --version 2>&1)"
  printf 'gpu=%s\n' "$(nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader | tr '\n' ';')"
  printf 'command='
  printf '%q ' "${train_command[@]}"
  printf '\n'
} >"$manifest"

printf 'timestamp,gpu_index,name,memory_used_mib,memory_total_mib,utilization_gpu_percent,temperature_c,power_w\n' >"$gpu_log"
(
  while true; do
    timestamp="$(date --iso-8601=seconds)"
    nvidia-smi \
      --query-gpu=index,name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw \
      --format=csv,noheader,nounits \
      | while IFS= read -r sample; do
          printf '%s,%s\n' "$timestamp" "$sample"
        done
    sleep 1
  done
) >>"$gpu_log" 2>&1 &
gpu_monitor_pid=$!

stop_gpu_monitor() {
  if kill -0 "$gpu_monitor_pid" >/dev/null 2>&1; then
    kill "$gpu_monitor_pid" >/dev/null 2>&1 || true
    wait "$gpu_monitor_pid" 2>/dev/null || true
  fi
}
trap stop_gpu_monitor EXIT INT TERM

printf 'Starting %s with %s environments for %s iterations.\n' \
  "$task_id" "$envs" "$iterations"
printf 'Artifacts: %s\n' "$artifact_dir"

cd "$checkout"
set +e
"${train_command[@]}" 2>&1 | tee "$train_log"
train_status=${PIPESTATUS[0]}
set -e

stop_gpu_monitor
trap - EXIT INT TERM

run_dir="$(find logs/rsl_rl/velocity -mindepth 1 -maxdepth 1 -type d \
  -name "*_${run_name}" -printf '%T@ %p\n' 2>/dev/null \
  | sort -nr | head -n 1 | cut -d' ' -f2-)"

if [[ "$train_status" -eq 0 ]]; then
  final_status="completed"
elif [[ "$train_status" -eq 130 ]]; then
  final_status="interrupted"
else
  final_status="failed"
fi

{
  printf 'finished_at=%s\n' "$(date --iso-8601=seconds)"
  printf 'exit_code=%s\n' "$train_status"
  printf 'status=%s\n' "$final_status"
  printf 'run_directory=%s\n' "$run_dir"
} >>"$manifest"

if [[ "$train_status" -ne 0 ]]; then
  printf 'Training ended with status %s (%s). See %s\n' \
    "$train_status" "$final_status" "$train_log" >&2
  exit "$train_status"
fi
if [[ -z "$run_dir" ]]; then
  printf 'Training completed, but the run directory could not be resolved.\n' >&2
  exit 1
fi

printf 'Training completed. Run directory: %s\n' "$run_dir"
printf 'Manifest: %s\n' "$manifest"
