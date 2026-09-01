# 长路线轮滑障碍秀

日期：2026-09-01。证据等级：**SIM**。对象是上游 Microduck 14DOF roller 模型，不是本项目尚未完成的 10DOF 真机模型。

## 为什么重新编排

上一版“轮滑加速 → 下蹲穿杆 → 360° 旋转 → 急停歪头”有动作，但路线太短，主体几乎贴着障碍出现，缺少入场、转折和离场。新版改成一条连续 22 秒路线：

1. 从距离横杆约 2 m 的远端入场并持续加速；
2. 在蓝色转向点减速，用旋转策略完成约 90° 转弯；
3. 沿垂直赛道重新加速并下蹲穿杆；
4. 出杆后继续滑到独立圆形区域；
5. 完成 360° 旋转；
6. 急停并以歪头姿态定格。

这不是移动相机伪造转弯，也没有直接改写 base 位姿。所有执行器目标来自 ONNX 策略，MuJoCo 在同一条连续物理状态中推进。

## 策略组合与转弯标定

本次没有重新启动一轮 PPO。它复用已经训练/公开的三个动作能力：

- `roller.onnx`：直线轮滑、加速、制动和头部命令；
- `roller_crouch.onnx`：滑行中下蹲；
- `spin_model_500.onnx`：旋转策略。

现有 roller 训练的偏航命令范围为 0，不能直接执行转弯。`scripts/calibrate_spin_turn.py` 因此只改变旋转策略的相位时钟，不篡改关节输出，测量它在不同周期下的转角、漂移、落稳角速度和直立度。1.2 s 周期得到约 89° 转角、2.6 cm 漂移和 0.995 最低直立度，因此被用作赛道拐角控制器。

## 本机运行

实现位于外置 Microduck RL 工作树：

```text
Windows: D:\vibe_code\02_sys3d\_worktrees\microduck_roller_showcase
WSL2:   /mnt/d/vibe_code/02_sys3d/_worktrees/microduck_roller_showcase
branch: experiment/roller-showcase
```

最终回放命令：

```bash
MUJOCO_GL=egl uv run python scripts/run_roller_showcase.py \
  --spin policies/trained/spin_model_500.onnx \
  --video artifacts/showcase/roller_long_route_final_50fps.mp4 \
  --metrics artifacts/showcase/roller_long_route_final_50fps_metrics.csv \
  --summary artifacts/showcase/roller_long_route_final_50fps_summary.json
```

## 验收结果

| 指标 | 结果 | 判定 |
|---|---:|---|
| 视频规格 | 960×540，50 fps，1,100 帧，22.0 s | 通过 |
| 完整路径长度 | 3.907 m | 通过 |
| 远端加速段位移 | 2.011 m | 通过 |
| 转弯角度 | 94.8° | 通过 |
| 转弯对线角速度 | 0.279 rad/s | 通过 |
| 下蹲阶段穿过横杆 | 是 | 通过 |
| 旋转角度 | 368.5° | 通过 |
| 旋转区域内漂移 | 14.1 cm | 通过 |
| 旋转最低直立度 | 0.984 | 通过 |
| 最终平面速度 | 0.0001 m/s | 通过 |

最终回放、逐控制步 CSV 和 JSON 摘要保存在外置工作树的 `artifacts/showcase/`。这些大文件不提交到 Git；脚本、场景和复现命令进入版本控制。

## 限制

- 这是策略编排与部署标定，不是为整条路线重新训练一个端到端 policy；
- 横杆位置和相机轨迹用于该固定赛道的可读性，仍需随机障碍训练才能泛化到未知路线；
- 旋转区有 14.1 cm 平面漂移，视觉上仍在 24 cm 半径标记内，但真机前需要更严格的落点控制；
- 当前结果不能直接下发给 10DOF 目标硬件。
