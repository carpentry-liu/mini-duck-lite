# 当前进度

更新时间：2026-08-31

## 当前 Gate

**G1 · 自有 10DOF 仿真 Walk。G0 已通过。**

固定 commit 的官方 Microduck RL task registry、CPU tests、viewer/policy、64 环境 smoke、4,096 环境 GPU 并行负载验证和正式行走训练均已完成。官方 `model_1000.pt` 已通过固定直行量化验收和高清回放，但它是 14DOF 上游参考，不能替代当前 G1 的自有 10DOF 策略。

## 已确认

- WSL2 Ubuntu 24.04.3 可用；
- Python 3.12.3、uv 0.11.7 可用；
- NVIDIA GeForce RTX 5060 Ti 16 GB 可识别；
- 本仓库 `uv build`、`uv run pytest`（7 项）、G0 环境审计和 Bash/Python 语法检查通过；
- 上游仓库与参考 commit 已记录到 `docs/UPSTREAM.md`；
- Microduck RL 依赖安装成功，官方 task registry 包含目标任务；
- 官方 CPU tests 为 154 passed、1 skipped；
- 64 env / 5 iteration 训练完成，共 7,680 step，并生成 checkpoint 与 ONNX；
- 4,096 env / 5 iteration 训练完成，共 491,520 step，GPU 峰值 70%、峰值显存约 6,378 MiB；
- `model_4.pt` 已通过官方 `play` 加载并在 WSLg native viewer 中运行；
- 官方 14DOF 正式训练运行到第 1,048 轮，共 103,120,896 step；第 1,000 轮 checkpoint 累计 98,402,304 step；
- 正式训练 GPU 平均/峰值利用率 57.94%/88%，峰值显存 6,934 MiB，`nan_state` 为 0；
- `model_1000.pt` 在 128 环境、10 秒、0.25 m/s 固定直行评估中 128/128 不摔，前向 RMSE 0.0808 m/s，净横向速度 0.00634 m/s，净偏航 -0.0500 rad/s；
- `model_750.pt` 在 seed 42 与 seed 2026 的同口径评估中均 128/128 不摔；
- 固定命令 5 秒、250 帧、50 FPS、1280×720 回放已生成并再次通过 0 摔倒/0 NaN 验收；
- V0.3 产品、架构、接口、安全与完整 Gate 已转成仓库权威文档；
- G0 证据已记录到 `docs/experiments/2026-08-31-g0-upstream-gpu-training.md`；
- 正式训练证据已记录到 `docs/experiments/2026-08-31-upstream-walk-training.md`。

## G1 未完成

- 自有 10DOF MJCF、真实结构参数来源与中立站立姿态；
- 自有 observation/action/normalization/control-rate Policy Contract；
- 自有站立、行走、扰动恢复 reward、curriculum 与 domain randomization；
- 自有策略长时间 PPO、checkpoint 对照评估和 ONNX CPU replay。

## 下一任务

先依据 Microduck/Open Duck 的真实结构资料定义自有 10DOF 权威模型与 Policy Contract；通过静态姿态、自由落体、接触和 reset 测试后，再运行自有 64 env / 5 iteration smoke。smoke 通过后复用本次的日志采集、固定命令评估和视频回放流程，禁止直接开始无验收口径的长训练。

## 已知环境提示

WSL 启动会报告 `/etc/wsl.conf` 中 `user.default` 重复。该提示当前不阻塞 Ubuntu 启动，本仓库不修改系统级配置。
