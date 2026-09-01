# 连续轮滑障碍秀：带速甩弯与动态低头穿杆

日期：2026-09-01。证据等级：**SIM**。对象是上游 Microduck 14DOF roller 模型，不是本项目尚未完成的 10DOF 真机模型。

## 本轮解决的问题

旧版路线虽然包含转弯和穿杆，但转弯更像原地换向；下蹲策略也会在横杆附近明显停顿。新版把验收条件改成真实轮滑的连续动作：

1. 从远处持续滑入转向点；
2. 保留入弯速度，以弧线“甩”入新赛道，而不是原地旋转；
3. 在接近横杆时边滑边低头；
4. 整个穿杆窗口保持运动，禁止停在杆下；
5. 完全离开横杆后再用约 1.2 秒缓慢起身；
6. 继续滑入圆形区域，完成旋转、急停和歪头定格。

整段仿真连续推进，不改写 base 位姿，不使用关节关键帧伪造动作。

## 策略与训练

路线组合三个能力：

- `roller.onnx`：远距离接近、直线滑行、出杆与制动；
- `spin_model_500.onnx`：经相位压缩后负责弧线转向和原地旋转；
- `dynamic_crouch_model_400.onnx`：本轮新训练的动态低头穿杆策略。

转弯先用 `scripts/calibrate_spin_turn.py` 扫描相位周期、混合时间和策略占比。最终控制器持续混合 roller 与 spin 两个策略：以 0.535 m/s 入弯，弯中不低于 0.258 m/s，在 34.8 cm 的实际轨迹中完成 92.6° 转向；它不是停稳后的原地 pivot。

横杆不再按预设赛道角度摆放。脚本先运行无碰撞探测路线，从完全下蹲时的实测轨迹反算穿越点与运动切线，再把横杆中心放到 `(-0.583, 1.224)`，并旋转到与该切线垂直的 `22.2°`。最终验收重新启用横杆碰撞。

动态下蹲使用 PPO 在 WSL2 Ubuntu、RTX 5060 Ti 上训练：

- 并行环境：4,096；
- 选定检查点：第 400 轮；
- 有效采样量：约 39.3M step；
- 训练重点：0.30 m/s 速度跟踪、航向保持、低位滑行、头部前俯、动作平滑和离杆后恢复；
- 训练到第 442 轮后手动停止，因为第 400 轮已经通过固定路线验收，继续堆轮次没有替代路线实测的意义。

## 本机位置与复现

实现位于外置 Microduck RL 工作树：

```text
Windows: D:\vibe_code\02_sys3d\_worktrees\microduck_roller_showcase
WSL2:   /mnt/d/vibe_code/02_sys3d/_worktrees/microduck_roller_showcase
branch: experiment/roller-showcase
```

最终回放命令：

```bash
MUJOCO_GL=egl uv run python scripts/run_roller_showcase.py \
  --crouch policies/trained/dynamic_crouch_model_400.onnx \
  --spin policies/trained/spin_model_500.onnx \
  --video artifacts/showcase/roller_fast_carve_gate_final_50fps.mp4 \
  --metrics artifacts/showcase/roller_fast_carve_gate_final_metrics.csv \
  --summary artifacts/showcase/roller_fast_carve_gate_final_summary.json \
  --fps 50 --width 1280 --height 720
```

## 固定路线验收

| 指标 | 结果 | 判定 |
|---|---:|---|
| 视频规格 | 1280×720，50 fps，19.48 s | 通过 |
| 完整路径长度 | 4.631 m | 通过 |
| 入弯 / 弯中最低速度 | 0.535 / 0.258 m/s | 通过 |
| 转弯弧线长度 | 0.348 m | 通过 |
| 连续转弯角度 | 92.6° | 通过 |
| 横杆交叉速度 | 0.390 m/s | 通过 |
| 横杆窗口最低速度 | 0.344 m/s | 通过，未在杆下停车 |
| 穿杆时躯干 / 嘴尖高度 | 7.2 cm / 16.1 cm | 通过 |
| 穿杆时低头角 | 0.856 rad（49.0°） | 通过 |
| 下蹲阶段滑行距离 | 1.290 m | 通过 |
| 完全离杆后才恢复站姿 | 是 | 通过 |
| 旋转角度 | 344.8° | 通过 |
| 旋转区域内漂移 | 6.8 cm | 通过 |
| 最终平面速度 | 0.0002 m/s | 通过 |

最终回放、逐控制步 CSV、JSON 摘要、训练日志、TensorBoard event、checkpoint、ONNX 与可重放源码补丁现已组成 [`roller-fast-carve-v1`](../../training/releases/roller-fast-carve-v1/README.md) 公开发布包。模型与视频使用 Git LFS，`MANIFEST.json` 保存逐文件 SHA-256；发布标签为 `roller-showcase-v1.0.0`。

## 限制

- 这是固定路线的策略组合与新下蹲策略训练，还不是带视觉感知的未知赛道导航；
- 横杆是仿真场景中的固定物体，真机需要相机或 ToF 估计距离后触发动作；
- 当前 14DOF roller policy 不能直接下发给规划中的 10DOF 硬件；
- 真机上线前仍要完成舵机限位、低速吊架和跌倒保护测试。
