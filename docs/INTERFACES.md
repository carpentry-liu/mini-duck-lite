# V0.4 核心接口

## HardwareManifest V1

权威模板位于 `config/hardware/reference-prototype-a.json`，最少包含：

- `hardware_revision`、完整 actuator SKU/gear ratio；
- 10DOF `joint_order`、bus ID、执行器分配、软限位；
- BNO085 primary 与 BNO055 compatibility；
- Pi Zero 2 W runtime、舵机电压域与峰值电流；
- 未实测字段必须是 `null`/`TBD_MEASURE`。

manifest 可用于文档和 H1 准备，但在 bus ID、软限位、执行器分配、IMU HIL 和峰值电流完成前，`runtime_ready=false`。

## ActuatorProfile V1

H1 每颗候选执行器输出：

```text
sku / gear_ratio / voltage
hardware_revision / bus_id / firmware
step_response[10,30,60] ×20
no_load_speed / loaded_speed
tracking_rmse / latency / jitter / packet_loss
current / voltage / temperature time series
deadband_backlash_proxy
disconnect_and_recovery
raw_csv_ref / summary_json_ref / video_ref
```

Mock logger 只生成 `SIM_PASS`，不能回写为真实 ActuatorProfile。

## ServoBus

```text
read(bus_id) -> ServoState
write_position(bus_id, position_rad)
torque_off()
close()
```

`ServoState` 包含 position、velocity、current、voltage、temperature、latency、connected 和 timestamp。真实 backend 必须完整报告单位和失败，不得用 0 填充不可读字段。

## ImuBackend

```text
read() -> ImuSample
close()
```

`ImuSample` 固定 `quaternion_wxyz`、angular velocity、linear acceleration、calibration 和 monotonic timestamp。V0.4 默认 BNO085；BNO055 adapter 只用于上游对照。

## Policy Contract V1

```text
joint_pos[10]          rad
joint_vel[10]          rad/s
base_orientation[4]    quaternion wxyz
base_ang_vel[3]        rad/s
command[3]             vx, vy, yaw_rate
prev_action[10]        按 schema 决定

PolicyOutput.action[10]
```

部署 metadata 必须携带 embodiment version、joint order、units、normalization、action scale、control_hz=50、training commit/config/seed 和模型哈希。官方 14DOF policy 与 10DOF contract 不匹配时必须 fail closed。

## SafeRuntime V1

本地 runtime 持有校准后的 HardwareManifest、ActuatorProfile 和 Policy Bundle。安全事件至少包括：

```text
NO_COMMAND
COMMAND_TIMEOUT
CONTROL_DEADLINE_MISS
IMU_STALE
IMU_NAN
IMU_IO_ERROR
SERVO_<id>_DISCONNECTED
JOINT_LIMIT
POLICY_CONTRACT_MISMATCH
```

安全事件不依赖网络或 Agent，立即进入 safe state，并写入 telemetry。

## Evidence Contract

状态只能向前推进：`SIM_PASS -> HIL_PASS -> REAL_PASS`。

HIL/REAL 必须记录 Git commit、hardware revision、config、telemetry、视频、尝试次数和成功次数；REAL 还要记录每次失败原因。每个物理能力只有 `REAL_PASS` 可以标记 DONE。

## Agent 边界

未来 Gateway 只暴露 `stand`、`recover`、`walk_to` 等白名单 Skill。`set_joint_angle`、`set_torque` 和 `raw_bus_write` 永久不对 Agent 暴露；写操作必须有 scope、ControlLease、approval 与 ExecutionReceipt。
