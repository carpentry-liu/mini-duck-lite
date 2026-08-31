# Roadmap 与 Gate

Gate 是预算和范围的硬边界。未满足上一 Gate 的可复现验收，不进入下一 Gate。

| Phase / Gate | 目标 | 预算或增量 | 通过条件 |
|---|---|---:|---|
| A · G0 | 上游仿真基线 | ¥0 | 固定 commit 的官方 task registry、viewer/policy 与最小 smoke 可复现 |
| A · G1 | 自有 10DOF 仿真 Walk | ¥0 | 自有 model 连续走；Policy Contract 锁定；ONNX CPU replay |
| A · G2 | 2 Servo HIL | ¥300-500 | 50 Hz 连续 30 min 稳定；获得 actuator 实测数据 |
| A · G3 | 10DOF 真机 Stand | 累计 ¥1,700-2,300 | 10 次上电至少 8 次安全站立 |
| A · G4 | Sim2Real Walk | 累计 ¥1,900-2,600 | 10 次 2 m 至少 7 次不摔 |
| A · G5 | Recovery | 累计 ¥2,000-2,700 | 标准跌倒至少 70% 恢复，且无需重启 |
| A · G6 | 自主找人 | 累计 ¥2,100-3,000 | 完整 Body Intelligence Hero Demo |
| A · G6.5 | Agent Gateway Foundation | ¥0 | MCP client 在 SIM/replay 可受控调用并产生审计回执 |
| B · G7 | Rough Terrain | 先仿真 ¥0 | 按 T1/T2 profile 报告可复现成功率 |
| C · G8 | Localization / Data | ¥0-500 起 | RGB/IMU/Pose 可重放、标定和时间可追溯 |
| C · G9 | Mapping / 3DGS | 独立核价 | 路线生成可重建 3D artifact，backend 可替换 |
| C · G10 | Spatial Memory | 软件为主 | 语义实体可查询并返回证据 |
| D · G11 | Skill Agent | 软件为主 | 长时任务失败可返回 failure code 并 replan |
| D · G11.5 | External Agent Physical Interop | 软件为主 | 至少两类 Agent 通过同一 contract 受控调用真机 Skill |
| D · G12/G13 | VLA / WAM Research | 按模型与算力核价 | 对照实验相对 baseline 有量化增益 |
| E · G14 | Cross-Embodiment | 另行设计 | 第二本体复用高层 stack |

## G0：已于 2026-08-31 通过

### 验收清单

- [x] WSL2 Ubuntu、Python、uv、Git 与 NVIDIA GPU 可识别；
- [x] Microduck RL、Open Duck Playground、MuJoCo 固定 commit 已记录；
- [x] 固定 commit 的 Microduck RL 依赖安装可复现；
- [x] `uv run list-envs` 输出官方 task registry；
- [x] 官方 CPU tests 通过；
- [x] 官方 viewer/policy 使用有效 smoke checkpoint 成功运行；
- [x] 64 env / 5 iteration 最小训练 smoke 完成；
- [x] 4,096 env / 5 iteration GPU 并行负载验证完成；
- [x] 命令、版本、日志、耗时、显存和失败记录入 `docs/experiments/`。

通过证据：[`2026-08-31-g0-upstream-gpu-training.md`](experiments/2026-08-31-g0-upstream-gpu-training.md)。smoke checkpoint 只证明链路，不代表稳定步态。

## 当前 Gate：G1

官方 14DOF `model_1000.pt` 已完成 103.1M step 训练并通过固定直行评估，可作为训练、日志和 checkpoint 验收流程参考；由于自有 10DOF model/contract 尚不存在，G1 验收项仍全部按自有实现判断。

### 验收清单

- [ ] 自有 10DOF MJCF 的结构来源、joint order、axis、sign 和 limit 可追溯；
- [ ] 中立站立姿态、reset、接触、自碰撞和自由落体测试通过；
- [ ] Policy Contract 锁定 observation、action、normalizer、action scale 与 50 Hz 控制频率；
- [ ] 64 env / 5 iteration 自有训练 smoke 无 NaN；
- [ ] 长训练产出可重复 checkpoint，并通过固定命令集评估；
- [ ] ONNX 携带 normalizer，并在 CPU MuJoCo replay 与 PyTorch 输出一致。

### 当前非目标

- 舵机、控制板、IMU 或 SBC 采购；
- HIL、真机站立、真机行走与 Sim2Real 宣称；
- SLAM、3DGS、Spatial Memory、VLA/WAM；
- 外部 Agent 真机写操作。

## 复杂地形分级

| 等级 | 定义 | 主要技术 |
|---|---|---|
| T0 | 平整硬地面 | Flat locomotion |
| T1 | 地毯、摩擦变化、轻坡 | DR + robust proprioceptive policy |
| T2 | 小高度扰动、低矮障碍、不规则地面 | heightfield curriculum + contact robustness |
| T3 | 明显斜坡、草地、碎石、低台阶 | terrain perception + traversability |
| T4 | 复杂落脚点或连续障碍 | footstep planning / policy / WBC integration |

进入 G6.5、G7、G9、G11、G11.5、G12 或 G13 前，必须重新核验相关论文、GitHub 项目和 Agent-Hardware protocol；路线图保留接口位置，不锁定快速变化的实现。
