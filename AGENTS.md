# Mini Duck Physical AI Platform agent guide

本仓库按 `docs/PRD.md` 实施 Mini Duck Physical AI Platform V0.3。Duck V0.1 是第一个 embodiment，不是整个平台的边界。

## 开始任务前

1. 依次读取 `docs/PROGRESS.md`、`docs/ROADMAP.md`、`docs/ARCHITECTURE.md`、`docs/INTERFACES.md` 和本文件。
2. 执行 `git status --short`，保留用户已有改动。
3. 确认当前 Gate、通过条件和明确非目标；未经用户授权不得跨 Gate 实施。
4. 非平凡改动先更新设计或决策文档，再修改代码。

## 当前唯一 Gate

当前是 **G0：上游仿真基线复现**。只有官方 Microduck RL / Open Duck 的固定 commit、task registry、viewer/policy 与最小 smoke 在目标机器可复现后，才进入 G1 自有 10DOF 模型。

以下内容当前只允许设计接口，不允许实施：自有 MJCF、PPO 长训练、舵机采购、HIL、真机控制、SLAM/3DGS、VLA/World Model、外部 Agent 真机写操作。

## 工程原则

- Body first：先证明可靠 locomotion，再接入高层 AI。
- Contract first：joint、policy、frame、time、calibration、skill、capability 全部版本化。
- Hard loop 与 AI 隔离：50 Hz runtime 不等待网络、LLM、VLA 或 mapping。
- Skill first：Agent 只能调用白名单 Skill，永不直接写 servo、torque 或 raw bus。
- Backend 可替换：localization、mapping、policy provider 通过接口接入。
- Gate 控 scope：每次提交只解决当前 Gate 的一个可审查问题。
- 参数诚实：未实测质量、惯量、摩擦、时延和载荷统一标记 `TBD_MEASURE`。
- 证据化：记录命令、版本、commit、config、seed、指标、日志与失败。

## AI 与真机安全边界

- 默认权限顺序：`OBSERVE -> SIMULATE -> PROPOSE -> EXECUTE_SAFE_SKILL`。
- 物理写操作必须经过 scope、ControlLease、approval、Safety Envelope 与审计。
- 断线、超时、lease 过期、sensor stale、NaN 或超限时，本地 runtime 必须独立进入 safe state。
- 新 Agent / 新 Tool 的验证顺序固定为 `SIM -> replay -> HIL -> 支架/软垫 -> PHYSICAL`。

## 上游与许可证

- 上游仓库放在本仓库之外，并固定 commit；来源见 `docs/UPSTREAM.md`。
- 不复制上游代码或模型资产，除非同时记录来源、commit、许可证与修改范围。
- `E:\tongyuan\pe-next-robot` 仅作只读工程规范参考，不得从本项目修改。

## 验证与提交

本仓库自身最小检查：

```bash
uv sync --all-groups
uv run pytest
uv run mini-duck-g0
```

上游 G0 验证使用 `scripts/run_g0_upstream_smoke.sh <microduck_rl_checkout>`；训练 smoke 默认不执行，必须显式传入 `--train-smoke`。

完成任务时同步更新 `docs/PROGRESS.md`；重大取舍写入 `docs/DECISIONS.md`；实验记录放在 `docs/experiments/`。Commit 使用清晰的 Conventional Commit 类型和中文全角冒号，例如 `docs：对齐 Physical AI Platform V0.3`。
