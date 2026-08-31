# 路线与 Gate

## G0：参考环境与本机软件栈

验收：

- [x] WSL2 Ubuntu、Python、uv 和 GPU 可识别；
- [x] 上游仓库与 commit 已记录；
- [x] MuJoCo 无界面模型加载和短仿真可运行；
- [x] CPU 契约测试可运行；
- [ ] 上游 Microduck 官方 task registry / viewer 完整复现。

## G1：自己的 10DOF 仿真鸭

验收：

- [x] MJCF 和 `JointContractV1`；
- [x] 关节/执行器/传感器 invariant 测试；
- [x] tethered articulation smoke；
- [ ] 自由站立模型与接触检查；
- [ ] walk PPO smoke；
- [ ] walk ONNX 与 CPU inference rehearsal。

## G2：2 舵机 HIL

验证 STS3215 总线、反馈、IMU、50 Hz loop、电源和安全边界；通过前不采购整套舵机。

## G3～G6

- G3：10DOF 结构站立；
- G4：Sim2Real 平地行走；
- G5：至少一种姿态的摔倒恢复；
- G6：无持续遥控的找人和靠近 Hero Demo。
