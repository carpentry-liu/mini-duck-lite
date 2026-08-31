# 当前进度

更新时间：2026-08-31

## 当前 Gate

**G0 · 上游仿真基线复现，尚未通过。**

V0.3 要求先复现固定 commit 的官方 Microduck RL / Open Duck task registry、viewer/policy 和最小训练 smoke。此前自制的 tethered 10DOF 几何模型不属于 G0 验收，已从主线移除，避免把“模型可加载”误写成“上游基线复现”。

## 已确认

- WSL2 Ubuntu 24.04.3 可用；
- Python 3.12.3、uv 0.11.7 可用；
- NVIDIA GeForce RTX 5060 Ti 16 GB 可识别；
- 本仓库 `uv build`、`uv run pytest`（5 项）、G0 环境审计和 Bash 语法检查通过；
- 上游仓库与参考 commit 已记录到 `docs/UPSTREAM.md`；
- V0.3 产品、架构、接口、安全与完整 Gate 已转成仓库权威文档。

## 未完成

- Microduck RL 固定 commit 的依赖安装；
- 官方 `uv run list-envs`；
- 官方 CPU tests；
- 带有效 checkpoint 的官方 viewer/policy；
- 64 env / 5 iteration 或等价训练 smoke；
- G0 完整实验记录。

## 下一任务

在 WSL2 中将 Microduck RL 检出到本仓库之外的独立目录，固定到 `docs/UPSTREAM.md` 记录的 commit，执行 `scripts/run_g0_upstream_smoke.sh`。先跑依赖、registry 和 CPU tests；确认后再显式启用训练 smoke，禁止直接开始长训练。

## 已知环境提示

WSL 启动会报告 `/etc/wsl.conf` 中 `user.default` 重复。该提示当前不阻塞 Ubuntu 启动，本仓库不修改系统级配置。
