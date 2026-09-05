# V0.4 核心接口

## HardwareManifest V1

权威模板位于 `config/hardware/reference-prototype-a.json`，最少包含：

- `hardware_revision`、完整 actuator SKU/gear ratio；
- 10DOF `joint_order`、bus ID、执行器分配、软限位；
- BNO085 primary 与 BNO055 compatibility；
- Pi Zero 2 W runtime、舵机电压域与峰值电流；
- 未实测字段必须是 `null`/`TBD_MEASURE`。

manifest 可用于文档和 H1 准备，但在 bus ID、软限位、执行器分配、IMU HIL 和峰值电流完成前，`runtime_ready=false`。

峰值电流必须是有限正数，且 `power.measurement_state=HIL_PASS`；`null`、`TBD_MEASURE`、NaN/Infinity 不表示实测完成。软限位必须是有限且严格递增的两端点，bus ID 必须为 0–253 内的整数且不重复。

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

Mock logger 只生成软件/SIM 证据，不能回写为真实 ActuatorProfile。

只有完整执行的 mock run 才输出 `SIM_PASS`；温度达到 `stop_temperature_c`（上限 55°C）或 I/O 失败时停止动作、关闭扭矩，输出失败摘要和非零 CLI 退出码。摘要记录已完成/计划样本数、`failure_reason` 及控制时长/墙钟耗时。启动元数据只记录 `SIM` 类型，不提前宣布通过。

实时执行使用单调绝对采样时刻调度，周期为 20 ms；mock CLI 使用共享虚拟时钟快进，`timing_mode=simulated`，bus 样本时间戳和采样调度必须来自同一时基。`elapsed_control_seconds` 可大于真实运行耗时，不得把虚拟 30 分钟作为实物热测试证据。

## ServoBus

```text
read(bus_id) -> ServoState
write_position(bus_id, position_rad)
torque_off()
close()
```

`ServoState` 包含 position、velocity、current、voltage、temperature、latency、connected 和 timestamp。真实 backend 必须完整报告单位和失败，不得用 0 填充不可读字段。

所有 I/O（含关闭扭矩）必须由 backend 设置有限传输超时，总预算适配 20 ms 周期；调用返回后不得再执行隐藏队列中的位置写入。时间戳标记采样时刻并与 runtime 单调时钟同域，读取缓存不能刷新时间戳。同步 Python runtime 无法抢占已阻塞的驱动调用；真实 backend 的时延验收及本地硬件 watchdog 是接入前置条件。

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

打包时使用 ONNX 官方 checker 验证实际图。当前只接受单个 float32 输入 `[1, observation_size]` 和单个 float32 输出 `[1, 10]`，批次和特征维固定；多输入/输出、外部 tensor 文件及动态维度暂不支持。验证后的实际名称、维度与类型写入 bundle manifest。

`normalization` 必须显式采用下列模式之一：

- `{"mode":"standard","mean":[...],"std":[...]}`：计算 `(obs - mean) / std`，两个数组长度均等于 `observation_size`，所有参数有限且 std 严格为正。
- `{"mode":"identity"}`：显式不做额外归一化；必须与训练/模型导出约定一致。

`observation_size` 为正整数，`action_scale` 为有限数值。模板中的 null 和未测占位值不能用于打包。使用打包工具前运行 `uv sync --extra policy`，或安装 `mini-duck-lite[policy]`；基础 mock/runtime 导入不加载 ONNX。

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
SERVO_<id>_STALE
SERVO_<id>_NAN
SERVO_<id>_IO_ERROR
JOINT_LIMIT
POLICY_CONTRACT_MISMATCH
```

安全事件不依赖网络或 Agent，立即进入 safe state，并写入 telemetry。

一个周期先读取、校验全组反馈，再写入任何关节；每次写入前重新检查命令时效、20 ms 周期预算和传感器新鲜度。故障状态锁存，需关闭并重新初始化 runtime 才能接受新命令；关闭扭矩失败时显式报告 `torque_off_failed`。mock CLI 遇到首个安全故障即结束并输出 `SIM_FAIL` / exit 1，全部请求周期正常完成才输出 `SIM_PASS`。

## Evidence Contract

状态只能向前推进：`SIM_PASS -> HIL_PASS -> REAL_PASS`。

HIL/REAL 必须记录 Git commit、hardware revision、config、telemetry、视频、尝试次数和成功次数；REAL 还要记录每次失败原因。每个物理能力只有 `REAL_PASS` 可以标记 DONE。

## Agent 边界

未来 Gateway 只暴露 `stand`、`recover`、`walk_to` 等白名单 Skill。`set_joint_angle`、`set_torque` 和 `raw_bus_write` 永久不对 Agent 暴露；写操作必须有 scope、ControlLease、approval 与 ExecutionReceipt。
