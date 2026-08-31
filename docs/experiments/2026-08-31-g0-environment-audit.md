# G0 开发机环境审计

日期：2026-08-31

## 目标

确认目标机器具备开始上游 Microduck RL G0 复现的基础条件。本记录不包含官方 registry、viewer/policy 或训练 smoke，因此不能证明 G0 通过。

## 已确认环境

- Windows + WSL2；
- Ubuntu 24.04.3 LTS；
- Python 3.12.3；
- uv 0.11.7；
- Git 2.43.0；
- NVIDIA GeForce RTX 5060 Ti，16311 MiB，driver 591.86。

## 命令

```bash
cd /mnt/d/vibe_code/02_sys3d/mini-duck-lite
uv lock
uv sync --all-groups
uv run pytest
uv run mini-duck-g0
bash -n scripts/wsl_bootstrap.sh scripts/run_g0_upstream_smoke.sh
uv lock --check
uv run python -m compileall -q src tests
uv build
```

## 结果

- `uv lock` / `uv sync --all-groups`：通过；
- `uv run pytest`：`5 passed`；
- `uv run mini-duck-g0`：Git、uv、NVIDIA GPU 三项可用，`environment_ready: true`；
- Bash 语法检查：通过；
- `uv lock --check`、Python compileall 与 `uv build`：通过，生成 0.3.0 sdist/wheel；
- 审计结果固定输出 `gate_passed: false`，因为上游 registry/viewer/policy/smoke 尚未执行。

基础环境可进入上游依赖安装阶段。此前执行过的自制 10DOF tethered MuJoCo articulation 与 V0.3 G0 验收无关，已从主线文档和代码删除。

## 下一步

在仓库外检出固定 commit 的 Microduck RL，依次执行依赖安装、`uv run list-envs`、CPU tests、官方 viewer/policy 和 64 env / 5 iteration smoke，并将真实命令和结果补充为新的实验记录。
