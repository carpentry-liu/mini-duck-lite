# 决策记录

## D-001：项目定位为 Physical AI Platform

日期：2026-08-31

Duck V0.1 是第一种 embodiment。上层 Spatial、Skill、Agent 和 Gateway contract 不得写死到鸭子外壳或 10DOF。

## D-002：严格执行 G0 -> G1

日期：2026-08-31

先复现官方 Microduck RL / Open Duck 基线，再建立自有 10DOF 模型。自制 tethered 几何模型不能替代官方 viewer/policy、task registry 或训练 smoke，因此从主线删除；历史仍可通过 Git commit 查询。

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
