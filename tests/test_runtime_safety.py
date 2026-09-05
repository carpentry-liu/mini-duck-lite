from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mini_duck_lite import runtime as runtime_module
from mini_duck_lite.hardware import (
    Bno055CompatibilityBackend,
    Bno085Backend,
    MockImuBackend,
    MockServoBus,
)
from mini_duck_lite.runtime import RuntimeConfig, SafeRuntime, load_runtime_config


ROOT = Path(__file__).resolve().parents[1]


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, duration: float) -> None:
        self.now += duration


class RecordingBus(MockServoBus):
    def __init__(self, bus_ids: list[int], *, clock: FakeClock) -> None:
        super().__init__(bus_ids, clock=clock)
        self.clock = clock
        self.events: list[tuple[str, int | None]] = []
        self.faults: dict[int, dict[str, object]] = {}
        self.read_delay = 0.0
        self.write_delay = 0.0

    def read(self, bus_id: int):
        self.events.append(("read", bus_id))
        self.clock.advance(self.read_delay)
        return replace(super().read(bus_id), **self.faults.get(bus_id, {}))

    def write_position(self, bus_id: int, position_rad: float) -> None:
        self.events.append(("write", bus_id))
        self.clock.advance(self.write_delay)
        super().write_position(bus_id, position_rad)

    def torque_off(self) -> None:
        self.events.append(("off", None))
        super().torque_off()


def config() -> RuntimeConfig:
    return RuntimeConfig(
        control_hz=50,
        command_timeout_ms=100.0,
        imu_timeout_ms=100.0,
        servo_timeout_ms=100.0,
        max_tick_late_ms=10.0,
        soft_limits_rad={1: (-0.8, 0.8), 2: (-0.8, 0.8)},
        safe_pose_rad={1: 0.0, 2: 0.0},
    )


def make_runtime(*, runtime_config: RuntimeConfig | None = None):
    clock = FakeClock()
    settings = runtime_config or config()
    bus = RecordingBus(list(settings.soft_limits_rad), clock=clock)
    imu = MockImuBackend(clock=clock)
    runtime = SafeRuntime(config=settings, servo_bus=bus, imu=imu, clock=clock)
    runtime.set_command({bus_id: 0.5 for bus_id in settings.soft_limits_rad})
    return runtime, bus, clock


@pytest.mark.parametrize(
    ("feedback", "expected_reason"),
    [
        ({"position_rad": 5.0}, "JOINT_LIMIT"),
        ({"position_rad": -5.0}, "JOINT_LIMIT"),
        ({"position_rad": float("nan")}, "SERVO_2_NAN"),
        ({"velocity_rad_s": float("inf")}, "SERVO_2_NAN"),
        ({"current_a": float("nan")}, "SERVO_2_NAN"),
        ({"voltage_v": float("nan")}, "SERVO_2_NAN"),
        ({"temperature_c": float("nan")}, "SERVO_2_NAN"),
        ({"latency_ms": float("nan")}, "SERVO_2_NAN"),
        ({"timestamp_s": float("nan")}, "SERVO_2_NAN"),
        ({"timestamp_s": 99.0}, "SERVO_2_STALE"),
        ({"timestamp_s": 101.0}, "SERVO_2_STALE"),
        ({"position_rad": None}, "SERVO_2_IO_ERROR"),
        ({"connected": False}, "SERVO_2_DISCONNECTED"),
        ({"bus_id": 1}, "SERVO_2_DISCONNECTED"),
    ],
)
def test_fault_on_last_joint_prevents_all_writes(feedback, expected_reason) -> None:
    runtime, bus, _ = make_runtime()
    bus.faults[2] = feedback

    assert runtime.tick() == {"status": "SAFE_STATE", "reason": expected_reason}
    assert bus.events == [("read", 1), ("read", 2), ("off", None)]

    # Restored feedback cannot silently resume a faulted runtime.
    bus.faults.clear()
    bus.events.clear()
    assert runtime.tick()["reason"] == expected_reason
    assert bus.events == [("off", None)]
    with pytest.raises(RuntimeError, match="latched"):
        runtime.set_command(config().safe_pose_rad)


def test_healthy_group_is_fully_read_before_the_first_write() -> None:
    runtime, bus, _ = make_runtime()
    assert runtime.tick()["status"] == "RUNNING"
    assert bus.events == [("read", 1), ("read", 2), ("write", 1), ("write", 2)]


@pytest.mark.parametrize(
    ("delay", "reason"),
    [(0.2, "COMMAND_TIMEOUT"), (0.025, "CONTROL_DEADLINE_MISS")],
)
def test_slow_imu_read_cannot_write_an_expired_command(delay, reason) -> None:
    runtime, bus, clock = make_runtime()

    class SlowImu(MockImuBackend):
        def read(self):
            clock.advance(delay)
            return super().read()

    runtime.imu = SlowImu(clock=clock)
    assert runtime.tick() == {"status": "SAFE_STATE", "reason": reason}
    assert bus.events == [("off", None)]


def test_slow_servo_reads_exhaust_budget_without_writing() -> None:
    runtime, bus, _ = make_runtime()
    bus.read_delay = 0.012
    assert runtime.tick()["reason"] == "CONTROL_DEADLINE_MISS"
    assert not any(event == "write" for event, _ in bus.events)


@pytest.mark.parametrize(
    ("command_age", "write_delay", "reason"),
    [(0.09, 0.015, "COMMAND_TIMEOUT"), (0.0, 0.025, "CONTROL_DEADLINE_MISS")],
)
def test_expiry_during_one_write_prevents_the_next(command_age, write_delay, reason) -> None:
    runtime, bus, clock = make_runtime()
    clock.advance(command_age)
    bus.write_delay = write_delay
    assert runtime.tick()["reason"] == reason
    assert [bus_id for event, bus_id in bus.events if event == "write"] == [1]
    assert bus.events[-1] == ("off", None)


def test_deadline_missed_by_final_write_is_not_reported_running() -> None:
    single = replace(config(), soft_limits_rad={1: (-0.8, 0.8)}, safe_pose_rad={1: 0.0})
    runtime, bus, _ = make_runtime(runtime_config=single)
    bus.write_delay = 0.025
    assert runtime.tick()["reason"] == "CONTROL_DEADLINE_MISS"
    assert bus.events[-1] == ("off", None)


def test_sensor_expiry_during_final_write_is_not_reported_running() -> None:
    single = replace(config(), soft_limits_rad={1: (-0.8, 0.8)},
                     safe_pose_rad={1: 0.0}, imu_timeout_ms=10.0)
    runtime, bus, _ = make_runtime(runtime_config=single)
    bus.write_delay = 0.012
    assert runtime.tick()["reason"] == "IMU_STALE"
    assert bus.events[-1] == ("off", None)


def test_feedback_that_ages_out_during_group_reads_cannot_be_written() -> None:
    runtime, bus, clock = make_runtime(runtime_config=replace(config(), servo_timeout_ms=10.0))
    bus.faults[1] = {"timestamp_s": clock() - 0.005}
    bus.read_delay = 0.004
    assert runtime.tick()["reason"] == "SERVO_1_STALE"
    assert not any(event == "write" for event, _ in bus.events)


def test_imu_that_ages_out_during_writes_stops_remaining_joints() -> None:
    runtime, bus, _ = make_runtime(runtime_config=replace(config(), imu_timeout_ms=10.0))
    bus.write_delay = 0.012
    assert runtime.tick()["reason"] == "IMU_STALE"
    assert [bus_id for event, bus_id in bus.events if event == "write"] == [1]


@pytest.mark.parametrize(
    "quaternion",
    [(1.0, 0.0, 0.0, 0.0), (2**-0.5, 2**-0.5, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)],
)
def test_bno055_preserves_native_wxyz_for_known_rotations(quaternion) -> None:
    sensor = SimpleNamespace(
        quaternion=quaternion, gyro=(0.0, 0.0, 0.0),
        linear_acceleration=(0.0, 0.0, 0.0), calibration_status=(3, 3, 3, 3),
    )
    assert Bno055CompatibilityBackend(sensor).read().quaternion_wxyz == quaternion


def test_bno085_still_converts_native_xyzw_to_wxyz() -> None:
    sensor = SimpleNamespace(
        quaternion=(0.0, 0.0, 0.0, 1.0), gyro=(0.0, 0.0, 0.0),
        acceleration=(0.0, 0.0, 9.80665), calibration_status=3,
    )
    assert Bno085Backend(sensor).read().quaternion_wxyz == (1.0, 0.0, 0.0, 0.0)


def test_bno055_unavailable_fusion_sample_enters_safe_state() -> None:
    runtime, bus, _ = make_runtime()
    runtime.imu = Bno055CompatibilityBackend(SimpleNamespace(quaternion=(None,) * 4))
    assert runtime.tick()["reason"] == "IMU_IO_ERROR"
    assert bus.events == [("off", None)]


@pytest.mark.parametrize(
    ("fault", "reason"),
    [
        ({"linear_acceleration_m_s2": (0.0, float("nan"), 0.0)}, "IMU_NAN"),
        ({"timestamp_s": float("nan")}, "IMU_NAN"),
        ({"timestamp_s": 101.0}, "IMU_STALE"),
        ({"timestamp_s": 99.0}, "IMU_STALE"),
        ({"quaternion_wxyz": (1.0, 0.0)}, "IMU_IO_ERROR"),
    ],
)
def test_invalid_imu_fields_fail_closed(fault, reason) -> None:
    runtime, bus, clock = make_runtime()

    class FaultyImu(MockImuBackend):
        def read(self):
            return replace(super().read(), **fault)

    runtime.imu = FaultyImu(clock=clock)
    assert runtime.tick()["reason"] == reason
    assert bus.events == [("off", None)]


def test_failed_torque_off_does_not_mask_the_original_fault() -> None:
    runtime, bus, _ = make_runtime()
    bus.faults[2] = {"connected": False}

    def fail_shutdown():
        raise OSError("transport disconnected")

    bus.torque_off = fail_shutdown
    assert runtime.tick() == {
        "status": "SAFE_STATE", "reason": "SERVO_2_DISCONNECTED", "torque_off_failed": True,
    }
    assert runtime.tick()["reason"] == "SERVO_2_DISCONNECTED"


def test_mock_servo_timestamp_uses_the_injected_clock() -> None:
    clock = FakeClock()
    bus = MockServoBus([1], clock=clock)
    assert bus.read(1).timestamp_s == 100.0
    clock.advance(0.02)
    assert bus.read(1).timestamp_s == 100.02


def test_runtime_schedule_includes_io_cost_without_drift(tmp_path, monkeypatch) -> None:
    clock = FakeClock()
    starts = []

    class TimedImu(MockImuBackend):
        def read(self):
            starts.append(clock())
            clock.advance(0.004)
            return super().read()

    monkeypatch.setattr(runtime_module.time, "monotonic", clock)
    monkeypatch.setattr(runtime_module.time, "sleep", clock.advance)
    monkeypatch.setattr(runtime_module, "MockImuBackend", TimedImu)
    log = tmp_path / "runtime.jsonl"
    summary = runtime_module.run_mock_runtime(config(), 5, log)

    assert starts == pytest.approx([100.0, 100.02, 100.04, 100.06, 100.08])
    assert summary["status"] == "SIM_PASS"
    assert summary["running_cycles"] == 5
    records = [json.loads(line) for line in log.read_text().splitlines()]
    assert records[0]["evidence_level"] is None
    assert records[-1]["evidence_level"] == "SIM_PASS"


def test_runtime_cli_reports_failure_and_nonzero_exit(tmp_path, monkeypatch, capsys) -> None:
    class FailedImu(MockImuBackend):
        def read(self):
            raise OSError("injected IMU bus failure")

    log = tmp_path / "runtime.jsonl"
    monkeypatch.setattr(runtime_module, "MockImuBackend", FailedImu)
    monkeypatch.setattr("sys.argv", [
        "mini-duck-runtime", str(ROOT / "config/runtime/mock-10dof.json"),
        str(log), "--cycles", "3",
    ])
    with pytest.raises(SystemExit) as exit_info:
        runtime_module.main()

    assert exit_info.value.code == 1
    assert json.loads(capsys.readouterr().out)["status"] == "SIM_FAIL"
    records = [json.loads(line) for line in log.read_text().splitlines()]
    assert records[-1]["running_cycles"] == 0
    assert records[-1]["safe_events"] == 1
    assert records[-1]["status"] == "SIM_FAIL"
    assert all(record.get("evidence_level") != "SIM_PASS" for record in records)
    assert records[1]["reason"] == "IMU_IO_ERROR"


@pytest.mark.parametrize("field", ["command_timeout_ms", "imu_timeout_ms", "servo_timeout_ms", "max_tick_late_ms"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1.0])
def test_runtime_config_rejects_watchdog_values_that_disable_checks(tmp_path, field, value) -> None:
    data = json.loads((ROOT / "config/runtime/mock-10dof.json").read_text())
    data[field] = value
    path = tmp_path / "invalid-runtime.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=field):
        load_runtime_config(path, allow_sim_limits=True)


def test_runtime_config_rejects_infinite_limits() -> None:
    with pytest.raises(ValueError, match="finite"):
        replace(config(), soft_limits_rad={1: (-float("inf"), 0.8), 2: (-0.8, 0.8)})
