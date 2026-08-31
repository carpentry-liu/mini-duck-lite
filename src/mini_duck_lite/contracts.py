"""Versioned contracts shared by simulation, training, and future runtime code."""

from __future__ import annotations

from typing import Final


CONTRACT_VERSION: Final = "joint-contract-v1"
PHYSICS_FREQUENCY_HZ: Final = 500
CONTROL_FREQUENCY_HZ: Final = 50
CONTROL_DECIMATION: Final = PHYSICS_FREQUENCY_HZ // CONTROL_FREQUENCY_HZ

JOINT_NAMES: Final = (
    "left_hip_yaw",
    "left_hip_roll",
    "left_hip_pitch",
    "left_knee_pitch",
    "left_ankle_pitch",
    "right_hip_yaw",
    "right_hip_roll",
    "right_hip_pitch",
    "right_knee_pitch",
    "right_ankle_pitch",
)

ACTUATOR_NAMES: Final = tuple(f"{name}_act" for name in JOINT_NAMES)

HOME_POSE: Final = {
    "left_hip_yaw": 0.0,
    "left_hip_roll": 0.0,
    "left_hip_pitch": 0.0,
    "left_knee_pitch": 0.0,
    "left_ankle_pitch": 0.0,
    "right_hip_yaw": 0.0,
    "right_hip_roll": 0.0,
    "right_hip_pitch": 0.0,
    "right_knee_pitch": 0.0,
    "right_ankle_pitch": 0.0,
}

SENSOR_NAMES: Final = (
    "imu_gyro",
    "imu_accelerometer",
    "imu_orientation",
    "left_foot_contact",
    "right_foot_contact",
)
