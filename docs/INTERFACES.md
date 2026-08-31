# 核心接口

本文档定义跨 Gate 保持稳定的接口边界。字段在实现前允许细化，但不得绕过安全层或把上层写死到 Duck 10DOF。

## Embodiment Contract

必须版本化：

- joint name、order、axis、sign、home、limit；
- actuator mode、unit、action scale；
- `world`、`map`、`odom`、`base_link`、`imu_link`、`camera_*`、`payload_*` frame；
- mass、CoM、inertia 的来源与测量状态；
- sensor timestamp、calibration version；
- `CapabilityManifest`。

未知物理参数使用 `TBD_MEASURE`，不得从 Microduck/Open Duck 直接照搬到自有结构。

## Policy Contract V1

```text
PolicyInputV1
  joint_pos[10]          rad
  joint_vel[10]          rad/s
  base_orientation[4]    quaternion; ordering is versioned
  base_ang_vel[3]        rad/s
  command[3]             vx, vy, yaw_rate
  prev_action[10]        optional by schema

PolicyOutputV1
  action[10]

ArtifactMetadata
  schema_version
  embodiment_version
  joint_order
  units
  normalization
  action_scale
  control_hz
  training_commit
  config
  seed
  model_hash
```

ONNX 必须包含或明确绑定 observation normalizer。任何 joint order、单位或 action scale 不匹配都应 fail closed。

## Spatial Contract

### Time 与 Calibration

- 使用 monotonic timestamp；保留 source time、receive time 与 sequence id；
- camera intrinsics、sensor-to-base extrinsics、IMU orientation 全部带版本；
- 首次相机数据采集就保存标定与时间来源，不能等到 SLAM 阶段补录。

### PoseEstimate

```text
pose
velocity
quality
frame_id
source_timestamp
receive_timestamp
sequence_id
calibration_version
```

### MapArtifact

```text
backend
frame_id
trajectory_ref
calibration_version
source_dataset_ref
artifact_ref
metrics
created_at
```

### SpatialEntity

```text
entity_id
semantic_label
embedding_ref
pose
bounds
confidence
first_seen
last_seen
map_version
evidence_observation_refs
```

Spatial Memory 依赖统一 frame 与实体接口，不依赖 3DGS 内部数据结构。

## Skill Contract

| 字段 | 说明 |
|---|---|
| `name` / `version` | 稳定标识 |
| `preconditions` | 执行前条件 |
| `inputs` | 结构化参数 |
| `progress` | 进度与 telemetry reference |
| `result` | `success/failure/cancelled/timeout` |
| `failure_code` | 供 Agent 重规划 |
| `required_capabilities` | 避免写死本体 |

长时 Skill 必须支持取消、超时和进度事件；执行失败返回机器可读 failure code，不只返回自然语言。

## CapabilityManifest

Gateway 只能暴露 manifest 声明的能力。最小字段：

```text
device_id
embodiment_type
contract_version
capabilities[]
skill_versions{}
sensor_streams[]
safety_state
allowed_permission_levels[]
```

## ControlLease

物理写操作必须持有有效 lease：

```text
lease_id
subject
device_id
scope
issued_at
expires_at
approval_policy
revocation_state
```

scope 不允许使用无限制通配；lease 过期、断线或安全状态变化时，本地 runtime 立即撤销执行权。

## ExecutionReceipt

每次真机 Tool/Skill 调用输出可审计回执：

```text
request_id
tool_or_skill
version
lease_id
started_at
finished_at
result
failure_code
telemetry_ref
media_refs[]
map_artifact_refs[]
safety_events[]
runtime_version
```

## 外部 Agent 权限面

| 类别 | Tool 示例 | 默认权限 |
|---|---|---|
| 观察 | `get_robot_state`、`get_health`、`camera_snapshot` | `OBSERVE` |
| 空间 | `get_map_status`、`query_spatial_memory` | `OBSERVE` |
| 仿真 | `simulate_task`、`dry_run` | `SIMULATE` |
| 动作 | `stand`、`recover`、`navigate_to`、`explore`、`inspect` | `PHYSICAL` + lease/approval |
| 安全 | `stop` | 高优先级独立路径 |
| 永久禁止 | `set_joint_angle`、`set_torque`、`raw_bus_write` | 不暴露 |

验证等级固定为 `OBSERVE -> SIMULATE -> PROPOSE -> EXECUTE_SAFE_SKILL`；新 Agent / Tool 固定经过 `SIM -> replay -> HIL -> 支架/软垫 -> PHYSICAL`。
