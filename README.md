# Mini Duck Lite

Mini Duck Lite 是一个个人可完成、分 Gate 投入的 10DOF 双足小鸭机器人项目。V0.1 的主线是先在 MuJoCo 中建立可验证的身体与控制契约，再逐步走向 PPO、ONNX、2 舵机 HIL 和真机 Sim2Real。

当前仓库交付的是第一步软件闭环：

- 10DOF 双腿 MJCF 模型；
- 500 Hz 物理步进与 50 Hz 控制节拍；
- 关节、执行器、IMU 与足底接触契约；
- WSL2 中可重复执行的无界面仿真；
- 关节周期动作、JSONL 遥测、摘要指标和可选 PNG 快照；
- CPU smoke test 与契约测试。

> 当前的“first step”使用调试 tether 固定躯干，只验证模型、关节和控制链路。它不是已训练的行走 policy，也不代表 G1 已完成。

## WSL2 快速启动

这台电脑已经安装 Ubuntu 24.04 WSL2、Python 3.12 和 `uv`。在 PowerShell 中执行：

```powershell
wsl -d Ubuntu -- bash -lc 'cd /mnt/d/vibe_code/02_sys3d/mini-duck-lite && bash scripts/wsl_bootstrap.sh'
wsl -d Ubuntu -- bash -lc 'cd /mnt/d/vibe_code/02_sys3d/mini-duck-lite && bash scripts/run_first_simulation.sh'
```

也可以进入 WSL 后逐步运行：

```bash
cd /mnt/d/vibe_code/02_sys3d/mini-duck-lite
uv sync --all-groups
uv run pytest
MUJOCO_GL=egl uv run mini-duck-sim \
  --duration 2 \
  --render \
  --output artifacts/g0-first-simulation
```

仿真输出：

```text
artifacts/g0-first-simulation/
├── summary.json
├── telemetry.jsonl
└── final-frame.png
```

如果 WSL 没有可用 EGL，可去掉 `--render`；动力学仿真与测试仍可运行。

## 验收命令

```bash
uv run pytest
uv run mini-duck-sim --duration 0.2 --output artifacts/smoke
```

成功时命令返回码为 0，`summary.json` 中应满足：

- `passed: true`；
- `actuator_count: 10`；
- `joint_count: 10`；
- 所有状态和控制量均为有限值；
- 遥测采样频率为 50 Hz。

## 项目结构

```text
mini-duck-lite/
├── src/mini_duck_lite/       # 合同、仿真入口和 MJCF
├── tests/                    # 无 GPU 契约与 smoke test
├── scripts/                  # WSL 初始化与第一步仿真
├── docs/                     # PRD、架构、路线、决策、进度和实验记录
├── pyproject.toml
└── uv.lock
```

## 当前边界

- 尚未训练 PPO walk/recovery policy；
- 尚未导出 ONNX；
- 尚未做执行器辨识、舵机 HIL 或真机控制；
- 质量、惯量、摩擦和执行器参数目前仅用于软件 smoke，不得直接当作真机参数；
- 任何硬件采购应等待对应 Gate 的软件验收完成。

详细范围见 [docs/PRD.md](docs/PRD.md)，当前事实见 [docs/PROGRESS.md](docs/PROGRESS.md)。
