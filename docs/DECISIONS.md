# 决策记录

## D-001：使用 WSL2 Ubuntu 作为训练和仿真主环境

日期：2026-08-31

原因：现有 Ubuntu 24.04、Python 3.12、uv 和 NVIDIA GPU 均可用，后续 MuJoCo Warp / JAX / PyTorch 训练路径也以 Linux 为主。

## D-002：第一步先做原生 MuJoCo contract smoke

日期：2026-08-31

原因：Microduck RL 完整环境需要 CUDA、mjlab、PyTorch 和较大的依赖下载。先用小型原生 MuJoCo 模型锁定 10DOF、传感器、节拍和输出证据，再接入上游训练框架，可以更快区分环境问题与机器人模型问题。

## D-003：允许 debug tether，但禁止把它当成行走结果

日期：2026-08-31

第一步仿真通过可切换 weld 固定躯干，验证双腿关节周期和控制链路。任何 walk/recovery 验收必须关闭 tether，并使用自由基座和地面接触。

## D-004：只记录上游 commit，本轮不复制上游源码

日期：2026-08-31

- `pollen-robotics/microduck_rl` develop：`d424a0c899f6b33cbd3daeb279913134349c0b63`
- `apirrone/Open_Duck_Playground` main：`b9be205ac64488c23504ca42e5ec790337adeec3`
- `google-deepmind/mujoco` main：`b62c3e886adfcfe220a694408ca8a41cee50b976`

本轮实现不包含上述仓库的代码或模型资产。
