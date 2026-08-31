# 上游基线

记录日期：2026-08-31

| 项目 | 分支 | 固定 commit | 本项目借鉴点 |
|---|---|---|---|
| [Microduck RL](https://github.com/pollen-robotics/microduck_rl) | develop | `d424a0c899f6b33cbd3daeb279913134349c0b63` | 50 Hz policy、smoke-first、PPO、recovery、ONNX 和 Sim2Real contract |
| [Open Duck Playground](https://github.com/apirrone/Open_Duck_Playground) | main | `b9be205ac64488c23504ca42e5ec790337adeec3` | 低成本双足 MJCF、添加新机器人、MuJoCo inference |
| [MuJoCo](https://github.com/google-deepmind/mujoco) | main | `b62c3e886adfcfe220a694408ca8a41cee50b976` | 原生物理仿真和 Python API |

Microduck RL 明确要求 CUDA GPU，并使用 mjlab/MuJoCo Warp + PPO；官方建议先用少量环境和 5 iterations 做 smoke。Open Duck Playground 通过 `uv` 管理环境，并给出了把新机器人接入 `playground/<robot>` 的目录方法。

上游源码不进入本仓库。后续如需引入代码或模型资产，必须先记录来源、commit、许可证和修改范围。
