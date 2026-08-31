# 上游基线

记录日期：2026-08-31

| 项目 | 分支 | 固定 commit | G0 用途 |
|---|---|---|---|
| [Microduck RL](https://github.com/pollen-robotics/microduck_rl) | develop | `d424a0c899f6b33cbd3daeb279913134349c0b63` | 官方 task registry、mjlab/MuJoCo Warp、PPO smoke、viewer/policy、ONNX |
| [Open Duck Playground](https://github.com/apirrone/Open_Duck_Playground) | main | `b9be205ac64488c23504ca42e5ec790337adeec3` | Open Duck Mini v2 MJCF、viewer/inference 与接入目录范式 |
| [MuJoCo](https://github.com/google-deepmind/mujoco) | main | `b62c3e886adfcfe220a694408ca8a41cee50b976` | 原生物理仿真和 Python API |

## 模型格式核对

Microduck RL 的机器人模型位于 `src/mjlab_microduck/robot/microduck/`，主入口是 `robot_walk.xml`、`robot_allcollisions.xml` 等 **MJCF**；视觉资产为 Onshape 导出的 STL。当前目录没有以 URDF 作为官方训练入口。

Open Duck Playground 的 Open Duck Mini v2 同样以 Onshape 导出的 MJCF/XML 和 STL 资产为主要仿真模型。若后续 CAD 流程需要 URDF，应在 G1 单独定义权威源与转换链，不能把推测的 URDF 当成上游事实。

## 许可证边界

Microduck RL 代码使用 Apache-2.0；其 README 另行声明 3D model files 为 Creative Commons BY-SA-NC。G0 仅外置检出和运行，不复制模型资产。G1 如决定复用网格，必须先完成署名、ShareAlike、NonCommercial 影响评审。

## G0 执行约束

- 上游检出目录必须位于本仓库之外；
- 执行前校验 `git rev-parse HEAD` 与固定 commit；
- 先安装依赖、列 task registry、跑 CPU tests；
- 训练只允许 64 env / 5 iteration 或上游等价 smoke；
- viewer/policy 必须使用真实 checkpoint；
- 每次结果写入 `docs/experiments/`，包括失败和环境警告。
