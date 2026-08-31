from __future__ import annotations

import math

import mujoco

from mini_duck_lite.contracts import (
    ACTUATOR_NAMES,
    CONTROL_DECIMATION,
    CONTROL_FREQUENCY_HZ,
    JOINT_NAMES,
    PHYSICS_FREQUENCY_HZ,
    SENSOR_NAMES,
)
from mini_duck_lite.simulation import load_model


def _names(model: mujoco.MjModel, object_type: mujoco.mjtObj, count: int) -> tuple[str, ...]:
    return tuple(mujoco.mj_id2name(model, object_type, index) for index in range(count))


def test_joint_and_actuator_contract_is_exact() -> None:
    model = load_model()
    joint_names = _names(model, mujoco.mjtObj.mjOBJ_JOINT, model.njnt)
    actuator_names = _names(model, mujoco.mjtObj.mjOBJ_ACTUATOR, model.nu)

    assert joint_names[0] == "root"
    assert joint_names[1:] == JOINT_NAMES
    assert actuator_names == ACTUATOR_NAMES
    assert model.nu == 10
    assert model.nq == 17
    assert model.nv == 16


def test_sensor_contract_and_control_rate() -> None:
    model = load_model()
    sensor_names = _names(model, mujoco.mjtObj.mjOBJ_SENSOR, model.nsensor)

    assert sensor_names == SENSOR_NAMES
    assert math.isclose(model.opt.timestep, 1.0 / PHYSICS_FREQUENCY_HZ)
    assert CONTROL_DECIMATION == PHYSICS_FREQUENCY_HZ // CONTROL_FREQUENCY_HZ
    assert PHYSICS_FREQUENCY_HZ % CONTROL_FREQUENCY_HZ == 0


def test_all_servo_joints_have_finite_limits() -> None:
    model = load_model()
    for name in JOINT_NAMES:
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        assert model.jnt_limited[joint_id]
        lower, upper = model.jnt_range[joint_id]
        assert math.isfinite(float(lower))
        assert math.isfinite(float(upper))
        assert lower < upper
