# 实验记录

每次上游复现、训练、replay、HIL 或真机实验单独记录：

- 日期、目标、当前 Gate 与 git commit；
- 上游仓库、固定 commit、许可证状态；
- 环境、依赖锁、GPU/驱动版本；
- 完整命令、task id、config、seed；
- 指标、耗时、显存、日志/视频/快照路径；
- 失败现象、限制、判断与下一步。

完整原始数据放在忽略的 `artifacts/`；仓库只保留可审查摘要和少量代表性证据。实验标题必须准确，例如“环境审计”“registry 复现”“5-iteration smoke”，不得把模型加载或 tethered articulation 描述成站立/行走成功。
