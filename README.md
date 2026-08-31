# Mini Duck Physical AI Platform

一个以低成本双足机器人为第一载体的 Physical AI 实验平台：先让身体可靠行动，再理解空间，最后让不同 AI Agent 通过安全、标准化接口使用真实机器人。

Duck V0.1 是第一种 embodiment，目标为 10DOF 双腿、自主站立与行走、跌倒恢复、视觉找人和安全靠近。平台本身不写死到“小鸭外壳”或 10 个关节；未来的定位、地图、Spatial Memory、Skill Router 与 Agent Gateway 应能复用于轮式、四足等本体。

## 当前状态

**当前 Gate：G1 · 自有 10DOF 仿真 Walk。G0 已于 2026-08-31 通过。**

G0 已完成：

- 固定 Microduck RL、Open Duck Playground 与 MuJoCo 参考 commit；
- 检查 WSL2、Python、uv、Git、GPU 等开发环境；
- 复现官方 task registry、CPU tests、viewer/policy 与 GPU 训练；
- 保存真实命令、版本、日志、显存和失败证据。

下一步进入 G1：建立自有 10DOF MJCF、锁定 Policy Contract，并训练可评估的站立/行走策略。硬件采购、SLAM/3DGS 与外部 Agent 真机写操作仍不在当前 Gate。

### 启动与训练的真实状态

| 项目 | 状态 | 说明 |
|---|---|---|
| WSL2 / Python / uv / Git / NVIDIA GPU 检查 | ✅ 已完成 | 已在目标电脑实测，环境审计结果见 `docs/experiments/` |
| Microduck RL 固定版本与任务入口 | ✅ 已配置 | 已固定上游 commit 和 `Mjlab-Velocity-Flat-MicroDuck` task ID |
| 机器人初始姿态加载与仿真启动 | ✅ 已完成 | 官方 HOME_FRAME、reset/startup events 与 CUDA 仿真已运行 |
| 官方 checkpoint 加载与策略推理 | ✅ 已完成 | `model_4.pt` 已通过官方 `play` 加载并在 native viewer 运行 |
| 64 env / 5 iteration 最小训练 | ✅ 已完成 | 7,680 step；生成 `model_0.pt`、`model_4.pt` 与 ONNX |
| 4,096 env / 5 iteration 并行训练 | ✅ 已完成 | 491,520 step；GPU 峰值 70%，峰值显存约 6,378 MiB |
| 自有 10DOF 强化学习训练 | ⏳ 尚未开始 | 当前 G1 主任务；上游 14DOF smoke 不能冒充自有策略 |

完整证据见 [`docs/experiments/2026-08-31-g0-upstream-gpu-training.md`](docs/experiments/2026-08-31-g0-upstream-gpu-training.md)。5 iteration 只证明环境、GPU、PPO、checkpoint 和播放链路可用，不代表已经得到稳定步态。

## 强化学习到底在训练什么

训练目标是得到一个实时控制策略：输入机器人当前姿态、关节状态和“想往哪里走”，输出 14 个关节的下一步动作。它不是记住一段固定动画，而是通过仿真试错学习在不同速度、摩擦、质量误差和外力下保持平衡。

```mermaid
flowchart LR
  C[目标速度 / 转向] --> O[61 维观测]
  S[关节 / IMU / 接触] --> O
  O --> P[同一个共享策略]
  P --> A[14 维关节动作]
  A --> E[4096 个 GPU 并行机器人]
  E --> R[前进 · 直立 · 少摔 · 少打滑]
  R --> U[PPO 更新策略]
  U --> P
```

4,096 个环境不是 4,096 个不同模型，而是 4,096 只同步试错的虚拟小鸭，共同更新同一套策略参数。并行环境越多，每轮采样越充分，也越能利用 GPU。此次 4,096 环境 smoke 的平均训练吞吐约为 2.4–3.2 万 step/s；真正可用的上游步态通常需要数千轮，而不是本次 5 轮。

## 平台分层

```mermaid
flowchart TB
  A[Claude / Codex / ChatGPT / Local Agent] --> G[Agent Gateway\nMCP first · MHS-ready]
  G --> R[Embodied Agent / Skill Router]
  R --> S[Skills + Spatial Intelligence]
  S --> P[Perception / Localization / Mapping]
  S --> L[Locomotion + Safe Runtime]
  L --> H[Embodiment / Hardware]
```

硬实时控制、感知定位、Skill 和 Agent 分属不同频率与故障域。Agent 只能调用白名单 Skill；50 Hz 控制环不依赖 LLM、网络或地图优化。

## 本机快速检查

在 PowerShell 中：

```powershell
wsl -d Ubuntu -- bash -lc 'cd /mnt/d/vibe_code/02_sys3d/mini-duck-lite && bash scripts/wsl_bootstrap.sh'
wsl -d Ubuntu -- bash -lc 'cd /mnt/d/vibe_code/02_sys3d/mini-duck-lite && uv run mini-duck-g0'
```

输出是环境审计 JSON，只表示本机前置条件；G0 的真实训练与播放结果以实验记录为准。

## 上游 G0 验证

先在本仓库之外检出 `docs/UPSTREAM.md` 固定的 Microduck RL commit，然后执行：

```bash
bash scripts/run_g0_upstream_smoke.sh /path/to/microduck_rl
```

该命令验证 commit、依赖、task registry 和上游 CPU tests。只有明确授权 GPU 小规模训练时才执行：

```bash
bash scripts/run_g0_upstream_smoke.sh /path/to/microduck_rl --train-smoke
```

本机已完成一次上述 smoke，并用生成的 checkpoint 启动官方 viewer。重新执行时，实际命令与结果仍必须记录到 `docs/experiments/`，不能用自制 tether 模型替代。

## 文档入口

- [产品范围](docs/PRD.md)
- [系统架构](docs/ARCHITECTURE.md)
- [核心接口](docs/INTERFACES.md)
- [Gate 路线](docs/ROADMAP.md)
- [当前进度](docs/PROGRESS.md)
- [决策记录](docs/DECISIONS.md)
- [上游基线](docs/UPSTREAM.md)

## 开发看板

### 已完成

- [x] 按 Physical AI Platform V0.3 重构产品范围、分层架构和 Gate 路线；
- [x] 固定 Microduck RL、Open Duck Playground 与 MuJoCo 上游版本；
- [x] 完成目标电脑的 WSL2、Python、uv、Git、GPU 环境审计；
- [x] 提供 G0 命令行审计工具、自动化测试和可复现构建；
- [x] 提供上游 registry、CPU tests 与最小训练 smoke 的统一脚本入口；
- [x] 建立实验记录目录，区分“已实测结果”和“计划执行项”；
- [x] 完成官方 checkpoint 播放和 64 环境训练 smoke；
- [x] 完成 4,096 个同步环境的 GPU 并行训练验证。

### G0 验收：已完成

- [x] 在仓库外检出 Microduck RL 固定 commit，并完成 `uv sync`；
- [x] 运行 `uv run list-envs`，确认官方任务已正确注册；
- [x] 运行上游 CPU tests，结果为 154 passed、1 skipped；
- [x] 启动官方 viewer，执行 HOME_FRAME reset 与 CUDA 仿真；
- [x] 使用 smoke checkpoint 启动官方 policy 推理；
- [x] 完成 64 env / 5 iteration 最小训练；
- [x] 完成 4,096 env / 5 iteration GPU 并行负载验证；
- [x] 记录命令、耗时、显存、训练指标、checkpoint 和失败信息。

### TODO：当前 Gate G1

- [ ] 基于真实结构参数建立自有 10DOF MJCF 与执行器配置；
- [ ] 定义可复现的中立站立姿态、reset 流程、关节限位和自碰撞规则；
- [ ] 锁定 observation、action、控制频率和 Policy Contract；
- [ ] 设计站立、行走、扰动恢复 reward 与 curriculum；
- [ ] 增加摩擦、质量、时延和执行器误差的 domain randomization；
- [ ] 完成长时间 PPO 训练、checkpoint 评估与 ONNX CPU replay。

详细 Gate 验收条件以 [`docs/ROADMAP.md`](docs/ROADMAP.md) 为准；README 只展示最近状态。

## 当前明确不做

- 不把持续遥控作为 Hero Demo 输入；
- 不让 LLM/VLA 直接输出舵机角度；
- 不把 5 iteration smoke 描述成“已经学会稳定走路”；
- 不在 G1 完成前购买整套舵机；
- 不把 3DGS 写死为导航地图；
- 不以卡通几何代理冒充 Microduck/Open Duck 工业结构；
- 不将未实测物理参数包装成 Sim2Real 结果。
