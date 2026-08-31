#!/usr/bin/env python3
"""Evaluate a pinned Microduck walking checkpoint with fixed commands.

Run this file from the upstream ``microduck_rl`` virtual environment. It does not
modify the upstream checkout; it only loads a checkpoint and writes one JSON
report supplied by the caller.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import torch

import mjlab.tasks  # noqa: F401 - populate the built-in task registry
import mjlab_microduck.tasks  # noqa: F401 - populate the Microduck task registry
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls
from mjlab.utils.torch import configure_torch_backends
from mjlab.utils.wrappers import VideoRecorder


TASK_ID = "Mjlab-Velocity-Flat-MicroDuck"
EXPECTED_UPSTREAM_COMMIT = "d424a0c899f6b33cbd3daeb279913134349c0b63"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a deterministic forward-walking checkpoint evaluation."
    )
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--num-envs", type=int, default=128)
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--burn-in-steps", type=int, default=50)
    parser.add_argument("--command-x", type=float, default=0.25)
    parser.add_argument("--command-yaw", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--with-pushes", action="store_true")
    parser.add_argument("--video-dir", type=Path)
    parser.add_argument("--video-width", type=int, default=1280)
    parser.add_argument("--video-height", type=int, default=720)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.checkpoint.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {args.checkpoint}")
    if args.num_envs <= 0 or args.steps <= 0:
        raise ValueError("num-envs and steps must be greater than zero")
    if not 0 <= args.burn_in_steps < args.steps:
        raise ValueError("burn-in-steps must be within [0, steps)")


def neutralize_pose_commands(env_cfg: Any, duration_s: float) -> None:
    for name in ("head_pose", "body_pose"):
        command_cfg = env_cfg.commands[name]
        command_cfg.ranges = tuple((0.0, 0.0) for _ in command_cfg.ranges)
        command_cfg.resampling_time_range = (duration_s + 1.0, duration_s + 1.0)


def configure_fixed_forward_env(args: argparse.Namespace) -> Any:
    env_cfg = load_env_cfg(TASK_ID, play=True)
    env_cfg.scene.num_envs = args.num_envs
    env_cfg.seed = args.seed
    if args.video_dir is not None:
        env_cfg.viewer.width = args.video_width
        env_cfg.viewer.height = args.video_height
    duration_s = args.steps * env_cfg.sim.mujoco.timestep * env_cfg.decimation

    twist_cfg = env_cfg.commands["twist"]
    twist_cfg.ranges.lin_vel_x = (args.command_x, args.command_x)
    twist_cfg.ranges.lin_vel_y = (0.0, 0.0)
    twist_cfg.ranges.ang_vel_z = (args.command_yaw, args.command_yaw)
    twist_cfg.resampling_time_range = (duration_s + 1.0, duration_s + 1.0)
    twist_cfg.rel_standing_envs = 0.0
    twist_cfg.rel_heading_envs = 0.0
    twist_cfg.rel_world_envs = 0.0
    twist_cfg.rel_forward_envs = 0.0
    twist_cfg.rel_turn_in_place_envs = 0.0
    twist_cfg.init_velocity_prob = 0.0

    neutralize_pose_commands(env_cfg, duration_s)
    env_cfg.curriculum = {}
    if not args.with_pushes:
        env_cfg.events.pop("push_robot", None)
    return env_cfg


def run_evaluation(args: argparse.Namespace) -> dict[str, Any]:
    configure_torch_backends()
    env_cfg = configure_fixed_forward_env(args)
    agent_cfg = load_rl_cfg(TASK_ID)

    base_env = ManagerBasedRlEnv(
        cfg=env_cfg,
        device=args.device,
        render_mode="rgb_array" if args.video_dir is not None else None,
    )
    rollout_env: Any = base_env
    if args.video_dir is not None:
        args.video_dir.mkdir(parents=True, exist_ok=True)
        rollout_env = VideoRecorder(
            base_env,
            video_folder=args.video_dir,
            step_trigger=lambda step: step == 0,
            video_length=args.steps,
            disable_logger=True,
        )
    env = RslRlVecEnvWrapper(rollout_env, clip_actions=agent_cfg.clip_actions)
    runner_cls = load_runner_cls(TASK_ID) or MjlabOnPolicyRunner
    runner = runner_cls(env, asdict(agent_cfg), device=args.device)
    runner.load(
        str(args.checkpoint),
        load_cfg={"actor": True},
        strict=True,
        map_location=args.device,
    )
    policy = runner.get_inference_policy(device=args.device)

    robot = base_env.scene["robot"]
    obs = env.get_observations()
    ever_fell = torch.zeros(args.num_envs, dtype=torch.bool, device=args.device)
    fall_events = 0
    nan_events = 0
    timeout_events = 0
    xy_squared_error = 0.0
    forward_squared_error = 0.0
    yaw_absolute_error = 0.0
    yaw_velocity = 0.0
    forward_velocity = 0.0
    lateral_velocity = 0.0
    lateral_absolute_velocity = 0.0
    action_rate_squared = 0.0
    reward_sum = 0.0
    measured_steps = 0
    previous_actions: torch.Tensor | None = None

    try:
        with torch.inference_mode():
            for step in range(args.steps):
                command = base_env.command_manager.get_command("twist")
                actual_linear = robot.data.root_link_lin_vel_b[:, :2]
                actual_yaw = robot.data.root_link_ang_vel_b[:, 2]
                actions = policy(obs)

                if step >= args.burn_in_steps:
                    xy_squared_error += torch.sum(
                        torch.square(command[:, :2] - actual_linear)
                    ).item()
                    forward_squared_error += torch.sum(
                        torch.square(command[:, 0] - actual_linear[:, 0])
                    ).item()
                    yaw_absolute_error += torch.sum(
                        torch.abs(command[:, 2] - actual_yaw)
                    ).item()
                    yaw_velocity += torch.sum(actual_yaw).item()
                    forward_velocity += torch.sum(actual_linear[:, 0]).item()
                    lateral_velocity += torch.sum(actual_linear[:, 1]).item()
                    lateral_absolute_velocity += torch.sum(
                        torch.abs(actual_linear[:, 1])
                    ).item()
                    if previous_actions is not None:
                        action_rate_squared += torch.sum(
                            torch.square(actions - previous_actions)
                        ).item()
                    measured_steps += 1

                obs, reward, _dones, _extras = env.step(actions)
                reward_sum += torch.sum(reward).item()
                fell = base_env.termination_manager.get_term("fell_over")
                nan = base_env.termination_manager.get_term("nan_state")
                timed_out = base_env.termination_manager.get_term("time_out")
                ever_fell |= fell
                fall_events += torch.count_nonzero(fell).item()
                nan_events += torch.count_nonzero(nan).item()
                timeout_events += torch.count_nonzero(timed_out).item()
                previous_actions = actions.clone()

        scalar_count = measured_steps * args.num_envs
        action_count = scalar_count * actions.shape[1]
        linear_velocity_rmse = (xy_squared_error / scalar_count) ** 0.5
        forward_velocity_rmse = (forward_squared_error / scalar_count) ** 0.5
        mean_forward_velocity = forward_velocity / scalar_count
        mean_lateral_velocity = lateral_velocity / scalar_count
        mean_yaw_velocity = yaw_velocity / scalar_count
        no_fall_fraction = 1.0 - torch.mean(ever_fell.float()).item()
        passed = (
            no_fall_fraction >= 0.95
            and forward_velocity_rmse <= 0.12
            and abs(mean_forward_velocity - args.command_x) <= 0.10
            and abs(mean_yaw_velocity) <= 0.15
            and abs(mean_lateral_velocity) <= 0.05
            and nan_events == 0
        )

        return {
            "schema_version": 1,
            "evaluated_at": datetime.now().astimezone().isoformat(),
            "task_id": TASK_ID,
            "expected_upstream_commit": EXPECTED_UPSTREAM_COMMIT,
            "checkpoint": str(args.checkpoint.resolve()),
            "device": args.device,
            "seed": args.seed,
            "num_envs": args.num_envs,
            "steps": args.steps,
            "burn_in_steps": args.burn_in_steps,
            "duration_seconds_per_environment": args.steps * base_env.step_dt,
            "command": {
                "linear_x_mps": args.command_x,
                "linear_y_mps": 0.0,
                "angular_z_radps": args.command_yaw,
            },
            "pushes_enabled": args.with_pushes,
            "video_directory": (
                str(args.video_dir.resolve()) if args.video_dir is not None else None
            ),
            "metrics": {
                "no_fall_environment_fraction": no_fall_fraction,
                "fall_events": fall_events,
                "timeout_events": timeout_events,
                "nan_events": nan_events,
                "linear_velocity_rmse_mps": linear_velocity_rmse,
                "forward_velocity_rmse_mps": forward_velocity_rmse,
                "yaw_absolute_error_radps": yaw_absolute_error / scalar_count,
                "mean_yaw_velocity_radps": mean_yaw_velocity,
                "mean_forward_velocity_mps": mean_forward_velocity,
                "mean_lateral_velocity_mps": mean_lateral_velocity,
                "mean_absolute_lateral_velocity_mps": (
                    lateral_absolute_velocity / scalar_count
                ),
                "action_delta_rms": (action_rate_squared / action_count) ** 0.5,
                "mean_reward_per_step": reward_sum / (args.steps * args.num_envs),
            },
            "acceptance": {
                "passed": passed,
                "criteria": {
                    "no_fall_environment_fraction_min": 0.95,
                    "forward_velocity_rmse_mps_max": 0.12,
                    "mean_forward_velocity_tolerance_mps": 0.10,
                    "absolute_mean_yaw_velocity_radps_max": 0.15,
                    "absolute_mean_lateral_velocity_mps_max": 0.05,
                    "nan_events_max": 0,
                },
            },
        }
    finally:
        env.close()


def main() -> None:
    args = parse_args()
    validate_args(args)
    report = run_evaluation(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
