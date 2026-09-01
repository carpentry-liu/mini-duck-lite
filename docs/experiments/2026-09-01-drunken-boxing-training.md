# “醉鸭拳”传播动作训练

日期：2026-09-01。证据等级：**SIM**。训练对象是上游 Microduck 14DOF roller 模型，不是本项目尚未完成的 10DOF 真机模型。

## 目标

训练一套在无声短视频里也能被快速读懂的动作，而不是只让机器人“动起来”。最终动作时长 5 秒，分成九个平滑关键姿态：

1. 站立起势；
2. 左右醉步与反向歪头；
3. 再次侧倾蓄力；
4. 下沉马步；
5. 探头出招；
6. 回撤；
7. 歪头定格；
8. 回到 HOME。

动作选择利用了 Microduck 的长颈、可偏航/横滚的头部和 roller 双腿。相比“月球漫步”，这套动作不会在画面上退化成普通倒车；相比固定关节动画，策略还要处理接触、惯性和扰动。

## 实现

训练代码位于外置 Microduck RL 工作树：

```text
Windows: D:\vibe_code\02_sys3d\_worktrees\microduck_roller_showcase
WSL2:   /mnt/d/vibe_code/02_sys3d/_worktrees/microduck_roller_showcase
branch: experiment/roller-showcase
```

新增 task id 为 `Mjlab-DrunkenBoxing-Flat-MicroDuck`。策略继续使用与 roller / crouch / spin 相同的 61D actor observation；前三个 command 槽用 `cos(2πφ), sin(2πφ), 0` 表示五秒相位。关键姿态经过 cubic smoothstep 插值，PPO 输出全部 14 个执行器目标，没有在回放脚本中直接写关节轨迹。

主要目标不是单一总 reward：

| 信号 | 用途 |
|---|---|
| `drunken_pose_track` + `drunken_pose_l1` | 跟踪九个姿态，兼顾近目标精度和远目标可学性 |
| `upright`、`feet_grounded`、`feet_flat` | 保持机身直立和双 roller 接触 |
| `spin_stay_in_place` | 防止动作被学成滑走 |
| `action_rate_l2` curriculum | 逐步从“先学会大动作”切到“降低控制跳变” |
| `neck_action_rate_l2` | 抑制头部高频抖动，不削掉可读的歪头幅度 |

## 本机训练

训练运行在 WSL2 Ubuntu、RTX 5060 Ti 16 GB 上，4,096 个环境并行采样，seed 42：

```bash
PYTHONUNBUFFERED=1 CUDA_VISIBLE_DEVICES=0 uv run train \
  Mjlab-DrunkenBoxing-Flat-MicroDuck \
  --env.scene.num-envs 4096 \
  --env.seed 42 \
  --agent.max-iterations 1000 \
  --agent.save-interval 100 \
  --agent.logger tensorboard \
  --agent.run-name drunken-boxing-v2-4096x1000-20260901
```

正式 run：

```text
logs/rsl_rl/drunken_boxing/2026-09-01_12-45-46_drunken-boxing-v2-4096x1000-20260901
```

## 检查点选择

每个候选 checkpoint 先导出包含 observation normalizer 的 ONNX，再在 CPU MuJoCo 中执行固定 5 秒回放。以下误差均来自物理仿真状态，不是从视频像素估计：

| checkpoint | 平均姿态误差 | 控制步变化 RMS | 95% 控制步变化 | 收招 HOME 误差 | 最大平面漂移 | 最低直立度 |
|---|---:|---:|---:|---:|---:|---:|
| 200 | 0.0558 rad | 0.01199 | 0.02564 | 0.0313 rad | 2.55 cm | 0.9942 |
| 400 | 0.0428 rad | 0.01121 | 0.02283 | 0.0175 rad | 2.70 cm | 0.9945 |
| 600 | 0.0399 rad | 0.01140 | 0.02409 | 0.0124 rad | 2.80 cm | 0.9943 |
| **700** | **0.0341 rad** | **0.01097** | **0.02249** | **0.0068 rad** | **3.03 cm** | **0.9946** |
| 800 | 0.0361 rad | 0.01105 | 0.02392 | 0.0076 rad | 3.03 cm | 0.9948 |
| 900 | 0.0356 rad | 0.01123 | 0.02280 | 0.0100 rad | 3.13 cm | 0.9954 |
| 999 | 0.0356 rad | **0.01087** | 0.02335 | 0.0098 rad | 2.96 cm | 0.9946 |

训练完整执行 1,000 iteration（编号 0–999），累计 98,304,000 step，耗时 46 分 14 秒。最终轮的平均控制步变化略小，但姿态误差、95% 控制步变化、收招误差和头部动作幅度均不及第 700 轮，因此最终选择 **`model_700.pt`**，不以 iteration 最大或单轮总 reward 代替固定回放验收。

## 验收与回放

`scripts/run_drunken_boxing.py` 在 50 Hz 控制频率下输出 250 帧、5 秒 MP4，同时保存逐控制步 CSV 和 JSON 摘要。验收门槛包括：

- 最低直立度不低于 0.85；
- 最大平面漂移不超过 15 cm；
- 平均姿态误差不超过 0.30 rad；
- 头部左右摆幅不少于 0.50 rad、横滚摆幅不少于 0.22 rad；
- ONNX 直接驱动 MuJoCo 执行器，回放脚本不得用关键帧替代策略动作。

本次所有候选轮次均通过硬门槛；第 700 轮头部左右摆幅 1.593 rad、横滚摆幅 0.640 rad。代表性回放为 960×540、50 fps、250 帧，舞台几何只用于取景，不参与碰撞，也不改变策略训练时的接触。

最终文件：

```text
checkpoint: logs/rsl_rl/drunken_boxing/2026-09-01_12-45-46_drunken-boxing-v2-4096x1000-20260901/model_700.pt
ONNX SHA256: 18937D7A7C588CBB9ED710B685087E07ABC8A71898E9367AF115E0CBE5CBE1E0
checkpoint SHA256: 454CFF8C4264D7B25497D1687A2EAD89F2CC57BBBBD48F239A457F70940B8202
```

## 限制

- 这是上游 14DOF roller 模型的 SIM 结果，不能直接下发给自有 10DOF 实体；
- “传播度”只能通过动作辨识度和视频表达设计提高，尚无真实发布后的完播率、互动率数据；
- 进入真机前必须补齐 roller 机械结构、目标舵机参数、关节软限位、质量/惯量和真实急停；
- 当前 policy 完成的是单段动作，不是对音乐 beat 的在线感知或多动作编舞器。
