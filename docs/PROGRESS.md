# 当前进度

更新时间：2026-08-31

## 当前 Gate

G0 软件栈与本项目的第一步 MuJoCo 仿真已经通过。下一任务仍属于 G0/G1 交界：复现上游 task registry，并为自由基座建立真正的站立控制或 PPO smoke。

## 已完成

- PRD 已转成仓库内执行文档；
- WSL2 Ubuntu 24.04、Python 3.12、uv 0.11.7、NVIDIA GPU 已识别；
- 上游基线 commit 已固定；
- 项目骨架、MJCF、合同和测试已创建；
- `uv.lock` 已生成，MuJoCo 3.12.0 环境可复现；
- 4 个 CPU 测试全部通过；
- 2 秒 tethered articulation simulation 通过并成功生成 EGL 快照；
- 视觉代理已重做为圆身、大头、亮眼、短翅和圆润鸭掌，保持 10DOF、actuator 与 sensor contract 不变；
- 2 秒自由基座仿真保持数值有限，但最终跌倒，符合当前尚无 stand/walk policy 的事实。

## 实测摘要

- tethered：1,000 physics steps，100 telemetry samples，final base z `0.340597 m`，passed；
- free base：1,000 physics steps，100 telemetry samples，final base z `0.085670 m`，状态有限但已经倒下；
- 10 joints、10 actuators、5 sensors；
- 详细记录：`docs/experiments/2026-08-31-g0-first-simulation.md`。

## 下一验收点

- 完成 Microduck RL `uv run list-envs` 或等价上游 registry 复现；
- 为 home pose 增加静态接触与质心检查；
- 建立少量环境、少量 iteration 的 stand/walk PPO smoke；
- 训练前明确 observation/action schema，禁止直接开始长训练。

## 已知环境提示

WSL 启动会报告 `/etc/wsl.conf` 中 `user.default` 重复。该提示当前不阻塞 Ubuntu 启动或仿真，本轮不修改系统级配置。
