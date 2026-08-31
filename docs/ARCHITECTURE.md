# V0.4 系统架构

## Hardware-First 主线

```mermaid
flowchart TB
  H1[H1 执行器/IMU 实测] --> PROFILE[ActuatorProfile + HardwareManifest]
  CAD[10DOF CAD / MJCF] --> TRAIN[WSL2 MuJoCo + GPU PPO]
  PROFILE --> TRAIN
  TRAIN --> POLICY[ONNX + normalizer + Policy Contract]
  POLICY --> REPLAY[CPU replay]
  REPLAY --> HIL[单舵机/单腿 HIL]
  HIL --> RT[Pi Zero 2 W · 50 Hz runtime]
  RT --> SAFE[watchdog · limits · physical cut]
  SAFE --> BODY[10DOF Duck]
```

训练模型必须吸收真实执行器、重心、质量、摩擦和时延数据。仿真负责高并发试错，真实 Gate 负责证明它能控制物理设备。

## 三台“计算机”的职责

| 位置 | 职责 | 不做什么 |
|---|---|---|
| Windows 宿主 | 文件管理、Codex 开发、视频与实验材料 | 不运行硬实时控制 |
| WSL2 Ubuntu + RTX GPU | MuJoCo/mjlab、PPO、评估、ONNX 导出 | 不直接连真机舵机母线 |
| Pi Zero 2 W | 50 Hz ONNX inference、watchdog、telemetry、servo/IMU I/O | 不训练大模型，不等待 LLM/网络 |

## 真实硬件结构

```mermaid
flowchart LR
  PI[Pi Zero 2 W] -->|UART TTL DATA| ADAPTER[Servo Adapter]
  ADAPTER --> LEFT[Left leg · 5 servos]
  ADAPTER --> RIGHT[Right leg · 5 servos]
  IMU[BNO085] -->|I2C/UART| PI
  PSU[7.4V PSU / 2S] --> FUSE[Main Fuse + Physical Cut]
  FUSE --> LEFT
  FUSE --> RIGHT
  UBEC[5V UBEC] --> PI
```

Adapter 是通讯组件，不是 10DOF PDB。舵机电源与逻辑 5V 分离，首次全身测试使用限流外部电源。

## 本地控制循环

```mermaid
flowchart LR
  READ[servo + BNO085 read] --> OBS[PolicyInputV1]
  OBS --> NORM[normalization]
  NORM --> ONNX[10DOF ONNX]
  ONNX --> SCALE[action scale + joint sign]
  SCALE --> LIMIT[soft limit + safety]
  LIMIT --> WRITE[servo write]
  WRITE --> LOG[JSONL telemetry]
  WATCH[timeout · stale · NaN · deadline] --> LIMIT
```

控制周期为 20 ms。任何 command timeout、sensor stale、NaN、舵机断连、超限或 deadline miss 都进入 safe state。LLM、VLA、mapping 和远程 UI 不进入这个 hard loop。

## 上层平台仍然保留

```mermaid
flowchart TB
  EXT[Claude / Codex / ChatGPT / Local Agent]
  GW[Agent Gateway · Auth · Scope · Lease · Audit]
  SKILL[Whitelisted Skills]
  SPATIAL[Localization · Mapping · Spatial Memory]
  RT[Safe Local Runtime]
  BODY[Embodiment]
  EXT --> GW --> SKILL
  SKILL --> SPATIAL
  SKILL --> RT --> BODY
```

这些层只在对应真实 Gate 实现。外部 Agent 永远不获得 raw bus、joint angle 或 torque 写权限。

## 当前落地模块

| 模块 | V0.4 状态 |
|---|---|
| `manifest` | 10DOF HardwareManifest 校验与 fail-closed readiness |
| `hardware` | ServoBus/ImuBackend、mock、BNO085、BNO055 compatibility |
| `qualification` | H1 plan、CSV/JSON logger、mock dry run |
| `runtime` | 50 Hz mock loop、安全状态基础 |
| `policy_bundle` | 10DOF ONNX/contract/hash 部署包 |
| `evidence` | SIM/HIL/REAL 证据字段校验 |

真实 STS3215 backend、ONNX provider 和 Pi service 要等 H1 数据与硬件 revision 锁定后实现。
