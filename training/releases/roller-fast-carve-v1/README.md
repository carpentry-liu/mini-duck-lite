# Roller Fast Carve Gate · 可复现训练发布包

这是 2026-09-01 完成的 Microduck **连续轮滑障碍秀 v1.0.0**。目标不是做一段关键帧动画，而是在连续物理仿真中组合三个 50 Hz ONNX 策略，完成：

> 远距离加速 → 带速甩弯 → 边滑边低头穿杆 → 出杆渐起 → 360° 旋转 → 急停歪头

![四阶段真实仿真截图](evidence/roller_fast_carve_gate_final_contact_sheet.jpg)

[下载 1280×720 / 50 fps 最终回放](evidence/roller_fast_carve_gate_final_50fps.mp4)

## 结果

| 指标 | 实测值 |
|---|---:|
| 时长 / 帧数 | 19.48 s / 974 |
| 完整路径 | 4.631 m |
| 入弯 / 弯中最低速度 | 0.535 / 0.258 m/s |
| 连续转弯 | 92.6°，弧长 0.348 m |
| 横杆交叉 / 窗口最低速度 | 0.390 / 0.344 m/s |
| 穿杆躯干 / 嘴尖高度 | 0.072 / 0.161 m |
| 低头角 | 0.856 rad（49.0°） |
| 下蹲阶段滑行距离 | 1.290 m |
| 旋转 / 区域漂移 | 344.8° / 0.068 m |
| 最终平面速度 | 0.0002 m/s |

逐控制步数据见 [`evidence/roller_fast_carve_gate_final_metrics.csv`](evidence/roller_fast_carve_gate_final_metrics.csv)，机器可读验收结果见 [`evidence/roller_fast_carve_gate_final_summary.json`](evidence/roller_fast_carve_gate_final_summary.json)。

## 发布了什么

| 目录 | 内容 | 用途 |
|---|---|---|
| `weights/` | 两组本机 PPO checkpoint、对应 ONNX，以及上游 roller ONNX | 继续训练、评估和 50 Hz 回放 |
| `logs/` | 终端全量日志、TensorBoard event | 查看 reward、termination、吞吐和学习过程 |
| `source-patches/` | 相对上游固定 commit 的两个干净补丁 | 复现环境、reward、场景、控制器和测试 |
| `evidence/` | 最终 MP4、截图、CSV、JSON | 人眼检查与自动验收 |
| `MANIFEST.json` | 版本、环境、来源、SHA-256 与字节数 | 防止下载或 LFS 文件损坏 |

三个策略的来源必须分开理解：

- `dynamic_crouch_model_400.*`：本机训练，约 39.3M step；用于保持速度的动态低头穿杆；
- `spin_model_500.*`：本机训练，约 49.2M step；用于弧线转向和旋转；
- `upstream_roller.onnx`：Pollen Robotics 发布的上游策略，负责基础轮滑推进、制动和姿态命令，SHA-256 与上游记录一致。

## 训练环境

- Windows 11 + WSL2 Ubuntu 24.04.3 LTS；
- NVIDIA GeForce RTX 5060 Ti 16 GB；
- CUDA Toolkit 12.9，`cuda:0`；
- seed `42`；
- 4,096 个并行环境；
- physics step `0.005 s`，policy/control step `0.02 s`（50 Hz）；
- 上游仓库：[pollen-robotics/microduck_rl](https://github.com/pollen-robotics/microduck_rl)；
- 补丁基线：`d424a0c899f6b33cbd3daeb279913134349c0b63`；
- 本地实验 commit：`98701254cd78e3d197dd8e2a0366b61cdf121073`。

## 从上游复现源码

```bash
git clone https://github.com/pollen-robotics/microduck_rl.git
cd microduck_rl
git checkout d424a0c899f6b33cbd3daeb279913134349c0b63
git apply /path/to/0001-add-forward-speed-tracking-reward.patch
git apply /path/to/0002-add-continuous-roller-showcase.patch
uv sync
uv run pytest tests/test_roller_crouch_cfg.py tests/test_showcase_timeline.py
```

这两个补丁已在一份新的、固定到上述 commit 的 worktree 中顺序执行 `git apply --check` 和完整应用验证。它们刻意不包含同一实验分支中的其他传播动作，便于上游审查。

## 训练与查看曲线

动态穿杆策略：

```bash
uv run train Mjlab-RollerCrouch-Flat-MicroDuck \
  --env.scene.num-envs 4096 \
  --agent.max_iterations 1000 \
  --agent.run-name dynamic-gate-4096x1000-20260901
```

训练在第 442 轮手动停止，固定路线选择 `model_400.pt`。旋转策略：

```bash
uv run train Mjlab-Spin-Flat-MicroDuck \
  --env.scene.num-envs 4096 \
  --agent.max_iterations 8000 \
  --agent.run-name spin-showcase-4096x8000-20260901
```

训练在第 514 轮停止，固定路线选择 `model_500.pt`。`max_iterations` 是上限，不代表应盲目跑满；本次按固定路线量化验收选择检查点。

查看 TensorBoard：

```bash
tensorboard --logdir training/releases/roller-fast-carve-v1/logs --port 6007
```

优先看 `Episode_Reward/forward_speed_tracking`、`Episode_Reward/spin_rate_track`、`Episode_Termination/fell_over`、mean reward 和 steps/s；原始 stdout 已完整保留，能确认设备确实是 `cuda:0`，不是只凭 GPU 截图判断。

## 回放

把发布包中的 ONNX 路径传给脚本：

```bash
MUJOCO_GL=egl uv run python scripts/run_roller_showcase.py \
  --roller /path/to/weights/upstream_roller.onnx \
  --crouch /path/to/weights/dynamic_crouch_model_400.onnx \
  --spin /path/to/weights/spin_model_500.onnx \
  --video roller_fast_carve_gate_final_50fps.mp4 \
  --metrics roller_fast_carve_gate_final_metrics.csv \
  --summary roller_fast_carve_gate_final_summary.json \
  --fps 50 --width 1280 --height 720
```

验证下载内容：

```bash
python training/releases/roller-fast-carve-v1/verify_release.py
```

## 能否直接上真机

不能。证据等级是 **SIM**，对象是上游 14DOF roller 模型；本项目规划的真机是独立 10DOF 硬件。ONNX 只有在 joint order、observation、normalizer、action scale、执行器方向/零位/限位与训练模型完全一致时才能部署。真机前仍需 CPU replay、HIL、吊架、限流与跌倒保护。

## 许可证与归属

代码补丁和训练链路基于 Pollen Robotics 的 `microduck_rl`，随包保留 [`UPSTREAM_LICENSE.txt`](UPSTREAM_LICENSE.txt)。上游 3D 资产有单独的 CC BY-SA-NC 条款；本发布包没有复制其网格资产。详情以原项目许可证和文件头为准。
