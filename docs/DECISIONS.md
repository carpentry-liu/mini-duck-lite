# 决策记录

## D-001：项目定位为 Physical AI Platform

日期：2026-08-31

Duck V0.1 是第一种 embodiment。上层 Spatial、Skill、Agent 和 Gateway contract 不得写死到鸭子外壳或 10DOF。

## D-002：V0.3 严格执行 G0 -> G1

日期：2026-08-31

先复现官方 Microduck RL / Open Duck 基线，再建立自有 10DOF 模型。自制 tethered 几何模型不能替代官方 viewer/policy、task registry 或训练 smoke，因此从主线删除；历史仍可通过 Git commit 查询。V0.4 的当前 Gate 顺序由 D-009 更新，但“上游证据不能被自制演示替代”的原则继续有效。

## D-003：Hard loop 与 AI 分离

日期：2026-08-31

50 Hz runtime 不依赖 LLM、VLA、mapping、网络和远程 UI。持续动作由本地 Skill/Policy 执行，上层模型只做任务规划、监控和重规划。

## D-004：Contract first

日期：2026-08-31

Embodiment、Policy、Spatial、Skill、Capability、ControlLease 和 ExecutionReceipt 都在实现前定义版本边界。未测物理参数统一标记 `TBD_MEASURE`。

## D-005：MCP first，协议适配层可替换

日期：2026-08-31

Agent Gateway 优先提供 MCP；其他 Agent-Hardware 协议只通过 adapter 接入。外部 Agent 默认只读，物理写操作需要 scope、lease、approval、Safety Envelope 与 audit。

## D-006：MappingBackend 可替换

日期：2026-08-31

导航先依赖稳定几何和可通行性。Point cloud、TSDF、3DGS 与 semantic map 通过统一 MappingBackend 对比；Spatial Memory 不依赖 Gaussian 内部结构。

## D-007：上游保持外置并固定版本

日期：2026-08-31

- `pollen-robotics/microduck_rl` develop：`d424a0c899f6b33cbd3daeb279913134349c0b63`
- `apirrone/Open_Duck_Playground` main：`b9be205ac64488c23504ca42e5ec790337adeec3`
- `google-deepmind/mujoco` main：`b62c3e886adfcfe220a694408ca8a41cee50b976`

上游源码不进入本仓库。复制代码或模型资产前必须记录来源、commit、许可证和修改范围。

## D-008：用固定命令评估选择 checkpoint

日期：2026-08-31

长训练不以“跑满 iteration”或单轮 reward 作为完成条件。先用 128 个 domain-randomized 环境固定直行 10 秒，检查不摔比例、前向速度 RMSE、净横移、净偏航和 NaN；连续 seed 通过后可提前停止。官方 14DOF `model_1000.pt` 已按该规则选中，但只作为 H0 的训练/评估参考，不能替代自有 10DOF 策略。

## D-009：V0.4 改为 Hardware-First

日期：2026-08-31

H0 上游仿真通过后，当前 Gate 改为 H1 执行器/IMU 资格测试。第一批只验证 C044、C046 和 BNO085；先获得真实速度、温升、延迟、电流与断连数据，再决定 10DOF 执行器组合、仿真参数和批量采购。

## D-010：No Hardware, No Done

日期：2026-08-31

证据等级固定为 `SIM_PASS -> HIL_PASS -> REAL_PASS`。mock、仿真、视频观感和上游策略都不能替代真实硬件验收。任何站立、行走、恢复、测绘或 Agent 控制能力只有 `REAL_PASS` 可以标记完成。

## D-011：训练和真机运行分离

日期：2026-08-31

PPO 训练在 WSL2 + GPU 完成；Pi Zero 2 W 只运行 50 Hz ONNX inference、安全控制和 telemetry。部署包必须绑定 10DOF joint order、normalizer、action scale、control rate、training commit 和 SHA256；官方 14DOF policy 禁止直接下发给 Reference Prototype A。

## D-012：审查修复同时覆盖执行路径与证据

日期：2026-09-05。关联 [REF-0001](refactoring/REF-0001-review-corrections/01-动机与方案.md)。

安全反馈和期限必须在写入前校验；同步 runtime 不承诺抢占未知阻塞驱动，真实 backend 必须证明有界 I/O 并配本地 watchdog。mock 快进采用共享虚拟时钟，控制时长与墙钟耗时分开记录。

ONNX 打包使用官方库交叉验证模型与合同；依赖作为可选 `policy` extra 提供，不放入 hard loop。物理六维力矩采用关节原点、世界坐标轴，修正源补丁时同步重生成发布分析数据与视频。步态验收先逐环境计算误差，避免跨环境相互抵消。
