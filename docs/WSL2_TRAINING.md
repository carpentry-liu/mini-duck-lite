# WSL2 强化学习开发与训练

## 结论

本项目的真实强化学习训练运行在 **Windows 11 的 WSL2 Ubuntu** 中，GPU 通过 NVIDIA WSL CUDA 映射给 Linux。训练不是在 PowerShell 原生 Python 中运行，也不是云端训练。

本机已验证环境：Ubuntu 24.04.3、Python 3.12.3、uv 0.11.7、RTX 5060 Ti 16 GB、PyTorch 2.9.1+cu128、MuJoCo 3.10.0、mjlab 1.3.0。

## 本机目录映射

| 内容 | Windows 路径 | WSL2 路径 |
|---|---|---|
| 本项目 | `D:\vibe_code\02_sys3d\mini-duck-lite` | `/mnt/d/vibe_code/02_sys3d/mini-duck-lite` |
| 固定上游 Microduck RL | `D:\vibe_code\02_sys3d\_upstream\microduck_rl` | `/mnt/d/vibe_code/02_sys3d/_upstream/microduck_rl` |
| 正式训练运行目录 | `D:\vibe_code\02_sys3d\_upstream\microduck_rl\logs\rsl_rl\velocity\2026-08-31_17-15-10_walk-baseline-4096x4000-20260831` | `/mnt/d/vibe_code/02_sys3d/_upstream/microduck_rl/logs/rsl_rl/velocity/2026-08-31_17-15-10_walk-baseline-4096x4000-20260831` |
| 选中的 checkpoint | `D:\vibe_code\02_sys3d\_upstream\microduck_rl\logs\rsl_rl\velocity\2026-08-31_17-15-10_walk-baseline-4096x4000-20260831\model_1000.pt` | `/mnt/d/vibe_code/02_sys3d/_upstream/microduck_rl/logs/rsl_rl/velocity/2026-08-31_17-15-10_walk-baseline-4096x4000-20260831/model_1000.pt` |
| W&B offline | `D:\vibe_code\02_sys3d\_upstream\microduck_rl\wandb\offline-run-20260831_171521-jn8wveeb` | `/mnt/d/vibe_code/02_sys3d/_upstream/microduck_rl/wandb/offline-run-20260831_171521-jn8wveeb` |
| 汇总日志与视频 | `D:\vibe_code\02_sys3d\mini-duck-lite\artifacts\walk-training-2026-08-31-run2` | `/mnt/d/vibe_code/02_sys3d/mini-duck-lite/artifacts/walk-training-2026-08-31-run2` |

`artifacts/`、上游 `logs/` 和 W&B offline 目录默认不提交 Git；README 和 `docs/experiments/` 保存可审查摘要、命令、指标与哈希。

## 训练代码在哪里改

当前正式结果来自外置、固定 commit `d424a0c899f6b33cbd3daeb279913134349c0b63` 的官方 Microduck 14DOF task。常用入口如下：

| 想调整什么 | 上游文件 |
|---|---|
| 机器人关节、执行器与 HOME_FRAME | `src/mjlab_microduck/robot/microduck_constants.py` |
| MJCF、碰撞、质量和几何 | `src/mjlab_microduck/robot/microduck/*.xml` |
| 速度命令、reward 权重、domain randomization、curriculum | `src/mjlab_microduck/tasks/microduck_velocity_env_cfg.py` |
| 自定义 reward、reset、观测或 curriculum 函数 | `src/mjlab_microduck/tasks/mdp.py` |
| PPO CLI 与训练参数入口 | `src/mjlab_microduck/train_cli.py` |
| ONNX 导出 | `scripts/export.py` 及 task exporter metadata |

固定上游目录用于复现，不建议直接改。自有 10DOF 开发应从个人 fork 或新分支开始，并把新 commit、模型结构和许可证重新写入 `docs/UPSTREAM.md`。`scripts/run_upstream_walk_training.sh` 会拒绝脏目录和 commit 漂移，这是为了防止日志与代码版本对不上。

## 推荐修改循环

1. 在自有分支修改 MJCF、执行器、reward 或 DR。
2. 先跑 CPU tests 和 64 env / 5 iteration smoke，确认 registry、reset 和 NaN 正常。
3. 用固定命令评估初始 checkpoint，避免只看 mean reward。
4. 再扩大到 4,096 env 长训练，同时记录终端、TensorBoard、W&B offline 和 GPU CSV。
5. 选中的 checkpoint 导出 ONNX，并验证 PyTorch、ONNX 与 CPU MuJoCo replay 的输出一致。
6. 只有 action size、joint order、单位、normalizer 和 50 Hz contract 全部一致，才允许生成真机部署 bundle。

## 已执行的正式训练

```bash
cd /mnt/d/vibe_code/02_sys3d/mini-duck-lite

bash scripts/run_upstream_walk_training.sh \
  /mnt/d/vibe_code/02_sys3d/_upstream/microduck_rl \
  /mnt/d/vibe_code/02_sys3d/mini-duck-lite/artifacts/walk-training-2026-08-31-run2 \
  --envs 4096 --iterations 4000 --seed 42 \
  --run-name walk-baseline-4096x4000-20260831
```

训练在 `model_1000.pt` 通过固定直行评估后于第 1,048 轮主动停止，共 103,120,896 step。该模型是官方 14DOF 参考，不能直接下发给 V0.4 的 10DOF 实体。

## 调参时必须保留的证据

- Git commit、dirty state、task ID、seed、并行环境数；
- 完整训练命令、stdout/stderr、依赖和 GPU 信息；
- TensorBoard/W&B offline、checkpoint、ONNX 和 SHA256；
- 固定命令评估、不同 seed、摔倒数、NaN、速度误差与视频；
- 对 reward、DR、执行器模型和结构参数的每一次有意义修改。

只保存一个“看起来会走”的视频不足以证明策略变好。
