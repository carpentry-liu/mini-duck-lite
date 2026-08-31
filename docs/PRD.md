# Mini Duck Physical AI Platform V0.3

本文档是 `Mini_Duck_Physical_AI_Platform_V0.3_PRD.docx` 的仓库执行版。原始 Word 文档是产品需求来源；本文件用于开发接力与 Gate 管理。

## 产品定义

Mini Duck Physical AI Platform 是一个以低成本双足机器人为第一载体的长期机器人实验项目。平台价值不在鸭子外壳，而在于建立五层可复用能力：

1. **身体智能**：自主站立、移动和跌倒恢复。
2. **空间智能**：知道自身位置、环境内容、可通行区域和目标位置。
3. **具身 Agent**：理解任务、调用 Skill、观察结果并在失败后重规划。
4. **跨本体复用**：未来更换轮式或四足本体时复用地图、记忆、Agent 与任务系统。
5. **Agent-Hardware 互操作**：外部 Agent 只通过受控 Gateway + Skill 访问设备，模型可替换，真机安全边界不变。

## 北极星体验

### Duck V0.1 · Body Intelligence

开机安全初始化后自主站立；摄像头发现前方的人；机器人调整朝向并双足走近 1-2 m，在安全距离停止；被轻推倒后检测 fallen，执行 recovery，重新站起并继续任务。全过程不依赖手机、手柄或持续遥控。

### V1 · Spatial AI Scout

机器人进入未建图室内空间，自主探索并输出画面与位姿；建立几何地图，可选生成 3DGS；把电脑、门、桌子等记录为 Spatial Entity；接受自然语言目标后查询 Spatial Memory、规划路径、调用 Skill，并在失败时重规划。

V1 是长期北极星，只用于约束今天的数据、坐标、接口和硬件预留，不是当前开发任务。

## 工程原则

| 原则 | 要求 |
|---|---|
| Body first | 没有可靠 locomotion，不做套壳大模型。 |
| Contract first | Joint、Policy、Frame、Time、Sensor、Skill 全部版本化。 |
| Hard loop 与 AI 隔离 | 50 Hz runtime 不等待 LLM、VLA、3DGS 或网络。 |
| Skill first | 高层 Agent 调用稳定 Skill，不直接发送 joint action。 |
| Backend 可替换 | Localization、mapping、VLA/WAM 都通过 adapter 接入。 |
| Embodiment 可替换 | Duck 是第一本体，上层不得写死到 10DOF。 |
| Gate 控 scope | 热点只先占接口位置，到对应 Gate 才实现。 |
| Hardware-safe | 外部 Agent 默认只读；写操作必须经过 lease、approval、安全与审计。 |

## Duck V0.1 成功指标

### Stand / Walk

- 平地连续行走首次验收不少于 2 m，后续目标不少于 5 m；
- 10 次上电至少 8 次进入稳定站立；
- 10 次 2 m 行走至少 7 次不摔；
- runtime 目标 50 Hz，deadline miss、NaN、sensor stale 可检测。

### Recovery

- 至少一种标准跌倒姿态 10 次中不少于 7 次恢复；
- 恢复后可返回 stand/walk，无需重启。

### Autonomous Approach

- 感知输出 `target_visible`、`target_bearing`、`confidence`、`distance_proxy`；
- 从约 1-2 m 自主转向、靠近并停止；
- 感知失败进入 search/safe，禁止盲走。

## V0.1 硬件边界

| 模块 | V0.1 方向 | 当前状态 |
|---|---|---|
| 双腿 | 10DOF；每腿 hip yaw/roll/pitch + knee + ankle | G1 才锁定 axis/sign/home |
| 执行器 | STS3215 7.4V 或同级反馈总线舵机 | `TBD_MEASURE`，G2 前不采购整套 |
| IMU | 1 个 | 姿态、角速度、跌倒判断 |
| 视觉 | 1 个 RGB camera | G6 找人；从首次接入起保存标定与时间戳 |
| 计算 | Pi Zero 2W / Radxa Zero 3W / 其他 Linux SBC 候选 | G2 前不锁死；重 AI 优先 PC offboard |

Sensor Head 必须可拆卸，并预留 RGB-D、Stereo、ToF、Event、Thermal 的标准安装面与数据接口。载荷能力只能通过重量、重心和步态测试确定。

## 范围控制

Agent-Hardware、Spatial AI、复杂地形、VLA 和 World Model 进入架构与 Roadmap，但不会提前进入实现。G0 已在目标开发机完成固定版本的官方 viewer/policy、64 环境 smoke 与 4,096 环境 GPU 并行验证；当前唯一主任务是 G1：自有 10DOF 仿真 Walk。

## 预算原则

G0/G1 使用现有电脑，预算为 ¥0。G2 只采购 2 舵机、总线板、IMU 和必要电源小件。Duck V0.1 真机总预算目标约 ¥2,000-3,000，所有型号和价格在采购 Gate 前重新核验。
