"""Replaceable hardware interfaces with fail-closed optional real backends."""

from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any, Protocol


@dataclass(frozen=True)
class ServoState:
    bus_id: int
    position_rad: float
    velocity_rad_s: float
    current_a: float
    voltage_v: float
    temperature_c: float
    latency_ms: float
    connected: bool
    timestamp_s: float


@dataclass(frozen=True)
class ImuSample:
    quaternion_wxyz: tuple[float, float, float, float]
    angular_velocity_rad_s: tuple[float, float, float]
    linear_acceleration_m_s2: tuple[float, float, float]
    calibration: int
    timestamp_s: float


class ServoBus(Protocol):
    def read(self, bus_id: int) -> ServoState: ...

    def write_position(self, bus_id: int, position_rad: float) -> None: ...

    def torque_off(self) -> None: ...

    def close(self) -> None: ...


class ImuBackend(Protocol):
    def read(self) -> ImuSample: ...

    def close(self) -> None: ...


class MockServoBus:
    """Deterministic servo model for CI and dry runs; never HIL evidence."""

    def __init__(self, bus_ids: list[int]) -> None:
        if not bus_ids or len(bus_ids) != len(set(bus_ids)):
            raise ValueError("mock bus IDs must be non-empty and unique")
        self._positions = {bus_id: 0.0 for bus_id in bus_ids}
        self._targets = dict(self._positions)
        self._connected = {bus_id: True for bus_id in bus_ids}
        self._torque_enabled = True

    def write_position(self, bus_id: int, position_rad: float) -> None:
        if bus_id not in self._positions:
            raise KeyError(f"unknown mock servo ID: {bus_id}")
        if not self._connected[bus_id]:
            raise ConnectionError(f"mock servo {bus_id} is disconnected")
        if not self._torque_enabled:
            raise RuntimeError("mock servo torque is disabled")
        if not math.isfinite(position_rad):
            raise ValueError("servo target must be finite")
        self._targets[bus_id] = position_rad

    def read(self, bus_id: int) -> ServoState:
        if bus_id not in self._positions:
            raise KeyError(f"unknown mock servo ID: {bus_id}")
        connected = self._connected[bus_id]
        previous = self._positions[bus_id]
        if connected and self._torque_enabled:
            self._positions[bus_id] += 0.35 * (
                self._targets[bus_id] - self._positions[bus_id]
            )
        velocity = (self._positions[bus_id] - previous) * 50.0
        error = abs(self._targets[bus_id] - self._positions[bus_id])
        current_a = (
            0.18 + min(error, 1.0) * 0.55
            if connected and self._torque_enabled
            else 0.0
        )
        return ServoState(
            bus_id=bus_id,
            position_rad=self._positions[bus_id],
            velocity_rad_s=velocity,
            current_a=current_a,
            voltage_v=7.4,
            temperature_c=28.0 + min(error, 1.0) * 2.0,
            latency_ms=1.5 + bus_id * 0.1,
            connected=connected,
            timestamp_s=time.monotonic(),
        )

    def set_connected(self, bus_id: int, connected: bool) -> None:
        if bus_id not in self._connected:
            raise KeyError(f"unknown mock servo ID: {bus_id}")
        self._connected[bus_id] = connected

    def torque_off(self) -> None:
        self._torque_enabled = False

    def close(self) -> None:
        self.torque_off()


class MockImuBackend:
    def __init__(self) -> None:
        self._closed = False

    def read(self) -> ImuSample:
        if self._closed:
            raise RuntimeError("mock IMU is closed")
        return ImuSample(
            quaternion_wxyz=(1.0, 0.0, 0.0, 0.0),
            angular_velocity_rad_s=(0.0, 0.0, 0.0),
            linear_acceleration_m_s2=(0.0, 0.0, 9.80665),
            calibration=3,
            timestamp_s=time.monotonic(),
        )

    def close(self) -> None:
        self._closed = True


class Bno085Backend:
    """Adapter around Adafruit's BNO08x driver, imported only on the SBC."""

    def __init__(self, sensor: Any) -> None:
        self._sensor = sensor

    @classmethod
    def from_i2c(cls, i2c: Any) -> "Bno085Backend":
        try:
            from adafruit_bno08x import BNO_REPORT_ACCELEROMETER
            from adafruit_bno08x import BNO_REPORT_GYROSCOPE
            from adafruit_bno08x import BNO_REPORT_ROTATION_VECTOR
            from adafruit_bno08x.i2c import BNO08X_I2C
        except ImportError as error:
            raise RuntimeError(
                "Install adafruit-circuitpython-bno08x on the Raspberry Pi"
            ) from error
        sensor = BNO08X_I2C(i2c)
        sensor.enable_feature(BNO_REPORT_ROTATION_VECTOR)
        sensor.enable_feature(BNO_REPORT_GYROSCOPE)
        sensor.enable_feature(BNO_REPORT_ACCELEROMETER)
        return cls(sensor)

    def read(self) -> ImuSample:
        quaternion_xyzw = tuple(float(value) for value in self._sensor.quaternion)
        gyro = tuple(float(value) for value in self._sensor.gyro)
        acceleration = tuple(float(value) for value in self._sensor.acceleration)
        return ImuSample(
            quaternion_wxyz=(
                quaternion_xyzw[3],
                quaternion_xyzw[0],
                quaternion_xyzw[1],
                quaternion_xyzw[2],
            ),
            angular_velocity_rad_s=gyro,
            linear_acceleration_m_s2=acceleration,
            calibration=int(getattr(self._sensor, "calibration_status", 0)),
            timestamp_s=time.monotonic(),
        )

    def close(self) -> None:
        return None


class Bno055CompatibilityBackend:
    """Compatibility adapter for upstream comparison; not the V0.4 default."""

    def __init__(self, sensor: Any) -> None:
        self._sensor = sensor

    def read(self) -> ImuSample:
        quaternion_xyzw = tuple(float(value) for value in self._sensor.quaternion)
        gyro = tuple(float(value) for value in self._sensor.gyro)
        acceleration = tuple(float(value) for value in self._sensor.linear_acceleration)
        calibration = min(int(value) for value in self._sensor.calibration_status)
        return ImuSample(
            quaternion_wxyz=(
                quaternion_xyzw[3],
                quaternion_xyzw[0],
                quaternion_xyzw[1],
                quaternion_xyzw[2],
            ),
            angular_velocity_rad_s=gyro,
            linear_acceleration_m_s2=acceleration,
            calibration=calibration,
            timestamp_s=time.monotonic(),
        )

    def close(self) -> None:
        return None
