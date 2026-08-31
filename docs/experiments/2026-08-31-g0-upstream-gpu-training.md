# G0 上游仿真启动与 GPU 并行训练

日期：2026-08-31  
结论：**G0 通过；进入 G1。**

## 目标

在目标电脑真实复现固定版本 Microduck RL 的依赖、任务注册、CPU tests、HOME_FRAME/reset、CUDA 仿真、PPO smoke、checkpoint 和官方 viewer/policy。不得将环境审计或静态模型加载冒充训练成功。

## 固定输入

- 本仓库起始提交：`2c142d0`；
- Microduck RL：`d424a0c899f6b33cbd3daeb279913134349c0b63`，仓库外独立检出且工作区干净；
- Task：`Mjlab-Velocity-Flat-MicroDuck`；
- Seed：`42`；
- WSL2 Ubuntu 24.04.3、Python 3.12.3、uv 0.11.7；
- NVIDIA GeForce RTX 5060 Ti 16 GB、驱动 591.86；
- PyTorch 2.9.1+cu128、mjlab 1.3.0、MuJoCo 3.10.0、Warp 1.12.0。

## 执行与结果

### 依赖、注册表与测试

```bash
uv sync
uv run list-envs
uv run --with pytest pytest tests/ -q
```

- 首次同步安装 142 个包；
- 注册表输出 45 个任务，包含目标 Task；
- CPU tests：`154 passed, 1 skipped in 50.13s`。

### 64 环境最小训练

```bash
WANDB_MODE=offline uv run train Mjlab-Velocity-Flat-MicroDuck \
  --env.scene.num-envs 64 \
  --agent.max_iterations 5 \
  --agent.run-name g0-smoke-2026-08-31
```

- 运行设备：`cuda:0`；
- 环境数：64，physics step 0.005 s，environment step 0.02 s；
- 5 iteration，共 7,680 step，训练段约 8 s；
- 采样峰值：GPU 38%，显存 1,697 MiB；
- `nan_state` 始终为 0；
- 生成 `model_0.pt`、`model_4.pt` 和带 normalizer 的 ONNX。

### 4,096 环境 GPU 并行验证

用户要求验证大量同步环境和真实 GPU 负载，因此在保持 5 iteration 的前提下扩大环境数：

```bash
WANDB_MODE=offline uv run train Mjlab-Velocity-Flat-MicroDuck \
  --env.scene.num-envs 4096 \
  --agent.max_iterations 5 \
  --agent.run-name g0-parallel-4096-2026-08-31
```

- 4,096 个环境共享同一套策略参数，不是训练 4,096 个独立模型；
- 5 iteration，共 491,520 step，训练段约 16 s；
- 吞吐从 23,870 提升到约 32,000 step/s；
- GPU 峰值 70%，峰值显存 6,378 MiB；
- mean reward 从 -0.03 变为 0.38；
- `nan_state` 始终为 0；
- 生成 `model_0.pt`、`model_4.pt` 和 ONNX。

### Checkpoint 播放

```bash
uv run play Mjlab-Velocity-Flat-MicroDuck \
  --checkpoint-file logs/rsl_rl/velocity/2026-08-31_16-44-04_g0-smoke-2026-08-31/model_4.pt \
  --num-envs 1 \
  --viewer native
```

官方 `play` 明确输出 `Loading checkpoint: model_4.pt`，在 `cuda:0` 创建单环境，执行 reset/startup events，解析 61 维 actor observation、76 维 critic observation 和 14 维 action，并在 WSLg native viewer 中持续运行，最后由 120 s 实验窗口发送 Ctrl+C 正常关闭。

## 初始姿态与训练目的

官方任务从 `HOME_FRAME` reset：腿部使用 STAND2 站立姿态、关节初速度为 0；每个环境再执行 base/joint/action-history reset 和质量、摩擦、编码器等随机化。PPO 学习的是从 61 维观测与速度命令到 14 维关节动作的共享策略，奖励同时约束速度跟踪、直立、姿态、摆腿、打滑、碰撞和动作平滑。

5 iteration 的作用是验证模型可以 reset、仿真可以 step、reward 可以计算、PPO 可以更新、checkpoint/ONNX 可以导出。它不能证明策略已学会稳定走路；上游可用步态通常需要 4,096 环境下数千 iteration 和独立评估。

## 异常与处理

- Windows 侧首次 GitHub DNS 解析失败，改用 WSL 网络完成固定 commit 检出；
- mjlab 1.3.0 的 `list-envs` 将任务数量作为 `main()` 返回值，console entry point 因此产生非零退出码；本仓库脚本改为检查目标 Task 是否真实出现在输出中；
- 首次 viewer 的 20 s/45 s 窗口不足以完成 Windows 挂载盘冷启动导入；延长到 120 s 后成功加载 checkpoint 并运行；
- `/etc/wsl.conf` 的 `user.default` 重复提示仍存在，不阻塞本实验；
- 原始日志、GPU CSV、checkpoint、ONNX 与 W&B offline run 保存在忽略的 `artifacts/` 和仓库外上游目录，不提交第三方资产或大文件。
