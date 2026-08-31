"""Headless first-step MuJoCo simulation for Mini Duck Lite."""

from __future__ import annotations

import argparse
from importlib.resources import as_file, files
import json
import math
from pathlib import Path
import time
from typing import Any

import mujoco
import numpy as np
from PIL import Image

from mini_duck_lite.contracts import (
    ACTUATOR_NAMES,
    CONTRACT_VERSION,
    CONTROL_DECIMATION,
    CONTROL_FREQUENCY_HZ,
    HOME_POSE,
    JOINT_NAMES,
)


def load_model() -> mujoco.MjModel:
    resource = files("mini_duck_lite.models") / "mini_duck_lite.xml"
    with as_file(resource) as model_path:
        return mujoco.MjModel.from_xml_path(str(model_path))


def _joint_position(model: mujoco.MjModel, data: mujoco.MjData, name: str) -> float:
    joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
    return float(data.qpos[model.jnt_qposadr[joint_id]])


def _actuator_targets(sim_time: float) -> dict[str, float]:
    phase = 2.0 * math.pi * 0.75 * sim_time
    swing = 0.16 * math.sin(phase)
    lift_left = 0.10 * max(0.0, math.sin(phase))
    lift_right = 0.10 * max(0.0, -math.sin(phase))
    targets = dict(HOME_POSE)
    targets["left_hip_pitch"] = -swing
    targets["right_hip_pitch"] = swing
    targets["left_knee_pitch"] = lift_left
    targets["right_knee_pitch"] = lift_right
    targets["left_ankle_pitch"] = -0.5 * lift_left
    targets["right_ankle_pitch"] = -0.5 * lift_right
    return targets


def _apply_targets(
    model: mujoco.MjModel, data: mujoco.MjData, targets: dict[str, float]
) -> None:
    for actuator_name, joint_name in zip(ACTUATOR_NAMES, JOINT_NAMES, strict=True):
        actuator_id = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_ACTUATOR, actuator_name
        )
        data.ctrl[actuator_id] = targets[joint_name]


def _render_frame(model: mujoco.MjModel, data: mujoco.MjData, path: Path) -> None:
    renderer = mujoco.Renderer(model, height=720, width=960)
    try:
        renderer.update_scene(data, camera="overview")
        Image.fromarray(renderer.render()).save(path)
    finally:
        renderer.close()


def run_simulation(
    *, duration: float, output: Path, render: bool = False, tether: bool = True
) -> dict[str, Any]:
    if duration <= 0:
        raise ValueError("duration must be positive")

    output.mkdir(parents=True, exist_ok=True)
    model = load_model()
    data = mujoco.MjData(model)

    data.qpos[:] = model.qpos0
    tether_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_EQUALITY, "debug_tether")
    data.eq_active[tether_id] = 1 if tether else 0
    _apply_targets(model, data, dict(HOME_POSE))
    mujoco.mj_forward(model, data)

    requested_steps = int(round(duration / model.opt.timestep))
    telemetry_path = output / "telemetry.jsonl"
    max_abs_qvel = 0.0
    max_step_wall_ms = 0.0
    telemetry_count = 0

    with telemetry_path.open("w", encoding="utf-8") as telemetry:
        for step in range(requested_steps):
            if step % CONTROL_DECIMATION == 0:
                _apply_targets(model, data, _actuator_targets(data.time))

            started = time.perf_counter()
            mujoco.mj_step(model, data)
            max_step_wall_ms = max(
                max_step_wall_ms, (time.perf_counter() - started) * 1000.0
            )
            max_abs_qvel = max(max_abs_qvel, float(np.max(np.abs(data.qvel))))

            if step % CONTROL_DECIMATION == 0:
                record = {
                    "time_s": round(float(data.time), 6),
                    "base_z_m": round(float(data.qpos[2]), 6),
                    "joint_position_rad": {
                        name: round(_joint_position(model, data, name), 6)
                        for name in JOINT_NAMES
                    },
                    "control_target_rad": {
                        name: round(float(data.ctrl[index]), 6)
                        for index, name in enumerate(JOINT_NAMES)
                    },
                }
                telemetry.write(json.dumps(record, ensure_ascii=False) + "\n")
                telemetry_count += 1

    finite = bool(
        np.isfinite(data.qpos).all()
        and np.isfinite(data.qvel).all()
        and np.isfinite(data.ctrl).all()
    )
    summary: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "mujoco_version": mujoco.__version__,
        "duration_s": round(float(data.time), 6),
        "physics_timestep_s": float(model.opt.timestep),
        "control_frequency_hz": CONTROL_FREQUENCY_HZ,
        "physics_steps": requested_steps,
        "telemetry_samples": telemetry_count,
        "joint_count": len(JOINT_NAMES),
        "actuator_count": int(model.nu),
        "sensor_count": int(model.nsensor),
        "tether_enabled": tether,
        "finite_state": finite,
        "final_base_z_m": round(float(data.qpos[2]), 6),
        "max_abs_qvel_rad_s": round(max_abs_qvel, 6),
        "max_step_wall_ms": round(max_step_wall_ms, 6),
    }
    summary["passed"] = bool(
        finite
        and model.nu == len(JOINT_NAMES)
        and telemetry_count > 0
        and requested_steps > 0
    )

    if render:
        try:
            frame_path = output / "final-frame.png"
            _render_frame(model, data, frame_path)
            summary["rendered_frame"] = frame_path.name
        except Exception as error:  # Rendering is optional; dynamics remain testable.
            summary["render_error"] = f"{type(error).__name__}: {error}"

    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=2.0)
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/g0-first-simulation")
    )
    parser.add_argument("--render", action="store_true")
    parser.add_argument(
        "--untethered",
        action="store_true",
        help="Disable the debug weld. This is a fall test, not a walking policy.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_simulation(
        duration=args.duration,
        output=args.output,
        render=args.render,
        tether=not args.untethered,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not summary["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
