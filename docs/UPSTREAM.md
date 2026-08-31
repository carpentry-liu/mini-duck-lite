# 上游基线

记录日期：2026-08-31

| 项目 | 分支 | 固定 commit | V0.4 用途 |
|---|---|---|---|
| [Microduck](https://github.com/pollen-robotics/microduck) | main | 在线跟踪，不复制硬件定义 | 官方端侧 runtime、50 Hz 控制环、设备服务、安全与升级架构参考 |
| [Microduck RL](https://github.com/pollen-robotics/microduck_rl) | develop | `d424a0c899f6b33cbd3daeb279913134349c0b63` | 官方 task registry、mjlab/MuJoCo Warp、PPO smoke、viewer/policy、ONNX |
| [Open Duck Playground](https://github.com/apirrone/Open_Duck_Playground) | main | `b9be205ac64488c23504ca42e5ec790337adeec3` | Open Duck Mini v2 MJCF、viewer/inference 与接入目录范式 |
| [MuJoCo](https://github.com/google-deepmind/mujoco) | main | `b62c3e886adfcfe220a694408ca8a41cee50b976` | 原生物理仿真和 Python API |
| [Open Duck Mini](https://github.com/apirrone/Open_Duck_Mini/tree/v2) | v2 | `b23317a485b3cec7d8417f352478778b3475173c` | 约 42 cm、5DOF×2、CAD/BOM/Sim2Real 与机械参考 |
| [Open Duck Mini Runtime](https://github.com/apirrone/Open_Duck_Mini_Runtime) | v2 | `32037347dc43186a017f2116bcfde7c461b81f54` | Pi Zero 2 W、IMU、motor controller、offset 与 ONNX 部署范式 |

## 模型格式核对

Microduck RL 的机器人模型位于 `src/mjlab_microduck/robot/microduck/`，主入口是 `robot_walk.xml`、`robot_allcollisions.xml` 等 **MJCF**；视觉资产为 Onshape 导出的 STL。当前目录没有以 URDF 作为官方训练入口。

Open Duck Playground 的 Open Duck Mini v2 同样以 Onshape 导出的 MJCF/XML 和 STL 资产为主要仿真模型。自有 10DOF CAD/MJCF 必须在 H1/H2 定义权威源与转换链，不能把推测的 URDF 当成上游事实。

## 许可证边界

Microduck RL 代码使用 Apache-2.0；其 README 另行声明 3D model files 为 Creative Commons BY-SA-NC。H0 仅外置检出和运行，不复制模型资产。后续如决定复用网格，必须先完成署名、ShareAlike、NonCommercial 影响评审。

`pollen-robotics/microduck` 是官方软件运行栈参考，不等于公开的 Microduck 硬件 BOM。本项目不声称是官方分支，也不根据公开软件反推或复制其未公开机械、电控设计；自有 10DOF 硬件采用独立设计和 H1/H2 实测参数。

## H0/H1 执行约束

- 上游检出目录必须位于本仓库之外；
- 执行前校验 `git rev-parse HEAD` 与固定 commit；
- 先安装依赖、列 task registry、跑 CPU tests；
- 上游固定目录保持干净；自有 10DOF 修改进入个人 fork/新分支并重新固定 commit；
- viewer/policy 必须使用真实 checkpoint；
- 每次结果写入 `docs/experiments/`，包括失败和环境警告。
- Open Duck 的执行器、offset、joint order 和硬件参数只能作为参考，不能替代 H1/H2 实测。
