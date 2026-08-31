# 当前进度

更新时间：2026-08-31

## 当前 Gate

**G1 · 自有 10DOF 仿真 Walk。G0 已通过。**

固定 commit 的官方 Microduck RL task registry、CPU tests、viewer/policy、64 环境 smoke 和 4,096 环境 GPU 并行负载验证均已完成。此前自制的 tethered 10DOF 几何模型不属于 G0 验收，已从主线移除。

## 已确认

- WSL2 Ubuntu 24.04.3 可用；
- Python 3.12.3、uv 0.11.7 可用；
- NVIDIA GeForce RTX 5060 Ti 16 GB 可识别；
- 本仓库 `uv build`、`uv run pytest`（5 项）、G0 环境审计和 Bash 语法检查通过；
- 上游仓库与参考 commit 已记录到 `docs/UPSTREAM.md`；
- Microduck RL 依赖安装成功，官方 task registry 包含目标任务；
- 官方 CPU tests 为 154 passed、1 skipped；
- 64 env / 5 iteration 训练完成，共 7,680 step，并生成 checkpoint 与 ONNX；
- 4,096 env / 5 iteration 训练完成，共 491,520 step，GPU 峰值 70%、峰值显存约 6,378 MiB；
- `model_4.pt` 已通过官方 `play` 加载并在 WSLg native viewer 中运行；
- V0.3 产品、架构、接口、安全与完整 Gate 已转成仓库权威文档；
- G0 证据已记录到 `docs/experiments/2026-08-31-g0-upstream-gpu-training.md`。

## G1 未完成

- 自有 10DOF MJCF、真实结构参数来源与中立站立姿态；
- 自有 observation/action/normalization/control-rate Policy Contract；
- 自有站立、行走、扰动恢复 reward、curriculum 与 domain randomization；
- 自有策略长时间 PPO、checkpoint 对照评估和 ONNX CPU replay。

## 下一任务

先依据 Microduck/Open Duck 的真实结构资料定义自有 10DOF 权威模型与 Policy Contract；通过静态姿态、自由落体、接触和 reset 测试后，再运行自有 64 env / 5 iteration smoke，禁止直接开始长训练。

## 已知环境提示

WSL 启动会报告 `/etc/wsl.conf` 中 `user.default` 重复。该提示当前不阻塞 Ubuntu 启动，本仓库不修改系统级配置。
