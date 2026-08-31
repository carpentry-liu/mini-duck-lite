# V0.4 Hardware-First 工具链验证

日期：2026-08-31

结论：**V0.4 软件已安装并通过 SIM 级验证；H1 仍等待真实 C044/C046、BNO085 与供电硬件。**

## 环境

- WSL2 Ubuntu 24.04.3；
- Python 3.12.3；
- uv 0.11.7；
- 项目包 `mini-duck-lite==0.4.0`；
- 验证发生时仓库存在本轮未提交改动，mock metadata 如实记录 `git_dirty=true`。

## 执行命令

```bash
uv lock
uv sync --all-groups
uv run pytest
uv run mini-duck-hardware-audit config/hardware/reference-prototype-a.json

uv run mini-duck-qualify \
  config/qualification/h1-c044-c046.json \
  artifacts/v04-validation4/c044 \
  --sku STS3215-C044 --backend mock --quick

uv run mini-duck-qualify \
  config/qualification/h1-c044-c046.json \
  artifacts/v04-validation4/c046 \
  --sku STS3215-C046 --backend mock --quick

uv run mini-duck-runtime \
  config/runtime/mock-10dof.json \
  artifacts/v04-validation4/runtime.jsonl \
  --backend mock --cycles 100

uv build
```

## 结果

| 检查 | 结果 |
|---|---|
| Python tests | 16 passed |
| package build | sdist 与 wheel 成功 |
| HardwareManifest | `valid=true`、`runtime_ready=false` |
| C044 mock logger | 92 samples；step/velocity/thermal/disconnect/reconnect 字段完整 |
| C046 mock logger | 92 samples；step/velocity/thermal/disconnect/reconnect 字段完整 |
| 50 Hz mock runtime | 100/100 `RUNNING`，0 safety event |
| 证据等级 | `SIM_PASS`、`gate_eligible=false` |

两颗候选的 mock 数值相同，因为 mock 只验证总线抽象、测试序列和日志结构，不模拟 C044/C046 的真实差异；不得用它做执行器选型。真实 H1 必须换成 STS3215 backend、限流电源和实际负载，并记录视频、hardware revision、telemetry 与失败原因。

## 本地证据

原始输出保存在忽略的 `artifacts/v04-validation4/`：

- `c044/metadata.json`、`samples.csv`、`summary.json`；
- `c046/metadata.json`、`samples.csv`、`summary.json`；
- `runtime.jsonl`，包含 session、100 个 tick 和 summary。
