# 官方 Microduck 14DOF 正式行走训练

日期：2026-08-31
结论：**官方 14DOF 基线已真实训练并通过固定直行验收；自有 10DOF G1 仍未通过。**

> V0.4 注：本文保留实验发生时的 G0/G1 命名；当前路线将该仿真基线归入 H0，当前 Gate 为 H1 Hardware Qualification。训练数据与结论不变。

## 目标与边界

本实验把 G0 的 5 iteration 链路 smoke 扩展为可播放、可量化评估的正式步态训练。训练对象仍是外置、固定 commit 的官方 Microduck 14DOF task，不是本项目尚未建立的自有 10DOF 模型，也不是 Sim2Real 或真机结果。

## 固定输入

- Microduck RL commit：`d424a0c899f6b33cbd3daeb279913134349c0b63`，外置检出且训练前工作区干净；
- Task：`Mjlab-Velocity-Flat-MicroDuck`；
- Seed：`42`；
- 4,096 个同步环境、每个 iteration 24 step、50 Hz policy；
- RTX 5060 Ti 16 GB、PyTorch 2.9.1+cu128、mjlab 1.3.0、MuJoCo 3.10.0、Warp 1.12.0；
- W&B 使用 offline 模式，所有命令、终端输出和 GPU 样本写入本地日志。

## 正式训练

仓库提供可复现入口：

```bash
bash scripts/run_upstream_walk_training.sh \
  /path/to/microduck_rl \
  /path/to/artifacts/walk-training \
  --envs 4096 \
  --iterations 4000 \
  --seed 42 \
  --run-name walk-baseline-4096x4000-20260831
```

`4000` 是上限，不是必须消耗完的配额。第 1,000 轮 checkpoint 通过预先固化的固定直行验收后，训练在第 1,048 轮有意发送 SIGINT，避免继续消耗约 2.4 小时。终端因此保留 `KeyboardInterrupt` 和 exit 130；manifest 最后一项明确覆盖为 `status=accepted_early_stop`，不能将其解释为训练崩溃。

### 训练结果

| 指标 | 结果 |
|---|---:|
| 选择的 checkpoint | `model_1000.pt` |
| 选择 checkpoint 累计 step | 98,402,304 |
| 实际训练停止 iteration / step | 1,048 / 103,120,896 |
| 实际墙钟时间 | 约 58 分 20 秒 |
| 第 1,000 轮吞吐 | 36,392 step/s |
| 第 1,000 轮 mean reward | 117.56 |
| 第 1,000 轮 mean episode length | 951.43 |
| 第 1,000 轮 `nan_state` | 0 |
| GPU 平均 / 峰值利用率 | 57.94% / 88% |
| 峰值显存 | 6,934 MiB |
| 峰值温度 / 功耗 | 60°C / 89.32 W |

训练同时生成 TensorBoard event、W&B offline run、`model_0/250/500/750/1000.pt` 和带 normalizer 的 ONNX。

## 固定命令验收

`scripts/evaluate_upstream_walk.py` 会关闭 curriculum 和随机推扰，固定头部/身体命令为中立值，并让所有环境执行 `0.25 m/s` 直行。验收使用 128 个带质量、摩擦、编码器等 domain randomization 的环境，每个运行 10 秒，前 1 秒作为 burn-in。

通过条件：

- 未摔环境比例至少 95%；
- 前向速度 RMSE 不高于 0.12 m/s；
- 平均前向速度与命令差不超过 0.10 m/s；
- 净横向速度绝对值不高于 0.05 m/s；
- 净偏航速度绝对值不高于 0.15 rad/s；
- `nan_state` 为 0。

不使用“每帧横向速度绝对值”作为直行失败条件，因为双足步态会周期性左右摆动；是否走歪应由净横移和净偏航判断。

### `model_1000.pt` 结果

| 指标 | 结果 | 结论 |
|---|---:|---|
| 未摔环境 | 128 / 128 | 通过 |
| `nan_state` | 0 | 通过 |
| 平均前向速度 | 0.1732 m/s | 通过 |
| 前向速度 RMSE | 0.0808 m/s | 通过 |
| 净横向速度 | 0.00634 m/s | 通过 |
| 净偏航速度 | -0.0500 rad/s | 通过 |
| action delta RMS | 0.1133 | 比 `model_750` 的 0.1363 更平滑 |

`model_750.pt` 在 seed 42 和 seed 2026 下也各自完成 128/128 不摔，证明结果不依赖单一随机种子。额外压力测试将推扰频率从训练时的每 3–6 秒提高到 play 模式的每 0.5–1 秒，115/128 环境未摔、无 NaN；该测试未达到 95% 门槛，作为后续鲁棒性改进项，不否定无推扰平地行走结论。

## 视频与人工检查

量化评估器使用同一固定命令离屏录制 5 秒、250 帧、50 FPS、1280×720 H.264 视频。首尾与中间帧均保持直立，腿部和躯干姿态随步态周期变化，地面网格相对位置持续变化。视频录制过程再次得到 0 摔倒、0 NaN 和通过结果。

## 本地证据

原始证据不提交第三方模型资产或大文件，保存在：

- 训练 run：`D:\vibe_code\02_sys3d\_upstream\microduck_rl\logs\rsl_rl\velocity\2026-08-31_17-15-10_walk-baseline-4096x4000-20260831`；
- 日志目录：`D:\vibe_code\02_sys3d\mini-duck-lite\artifacts\walk-training-2026-08-31-run2`；
- 汇总：`summary.json`；
- 训练终端：`train.log`；
- GPU 1 秒采样：`gpu.csv`；
- manifest：`manifest.txt`；
- 最终评估：`eval-model-1000.json`；
- 高清固定直行视频：`final-fixed-video-720p/rl-video-step-0.mp4`。

关键产物 SHA-256：

- `model_1000.pt`：`EE39ABF658CD1CCD0E6DDE9DA95E84EDEFE3AB2B8570AC2F612B81E17B783BB5`；
- ONNX：`57C1840E3135A4AF2EBA7D6BC85300E8961301A317AC309377737ADCCCD37C41`；
- 720p 视频：`4ACC78C74C5606EAB811E5FDC424F78631219BB6238972C8A98F5FF1357061C0`。

## 失败记录

- 首次正式命令错误使用 `--seed`，上游 CLI 要求 `--agent.seed`；未进入训练，失败日志单独保留，脚本已修正并加测试；
- 首次回放将布尔参数写成 `--video`，Tyro 要求 `--video True`；失败日志保留；
- CPU 回放首次编译 Warp 内核只录到 0.7 秒；后续改用 GPU，并最终由固定命令评估器完整录制；
- 官方 native viewer 在超时前只录到 5.64 秒随机命令素材，因此不作为最终固定直行证据；
- 达标停训产生 exit 130，manifest 保留原始退出码并追加 `accepted_early_stop` 最终状态。

## 后续

这次结果证明 GPU 训练、checkpoint 选择、定量评估和高清回放链路可用。V0.4 先在 H1/H2 获取执行器与单腿实测数据，再建立自有 10DOF MJCF 与 Policy Contract，并复用同样的 smoke、长训练、固定命令验收和 ONNX CPU replay 流程。
