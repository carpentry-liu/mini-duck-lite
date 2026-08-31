# Mini Duck Physical AI Platform V0.4

本文件是 `Mini_Duck_Physical_AI_Platform_V0.4_PRD.docx` 的仓库执行版。V0.4 把完成定义从“仿真方法成立”改为“真实 Duck 在目标场景通过”，当前状态为 **Hardware Qualification Ready**。

## 北极星体验

上电后自主站立、双足行走、发现人并靠近；被轻推倒后自主恢复并继续任务。过程不依赖持续遥控。SLAM、3DGS、VLA 和 Agent 只有在真实 Duck 数据与动作闭环中产生可复现结果才算完成。

## Hardware-First 硬规则

- H0 复现上游仿真基线；H1 立即验证真实执行器与 IMU；
- 第一批只验证 STS3215-C044 ×1、STS3215-C046 ×1 和 BNO085，不一次买满 10 个；
- H1 数据决定每个关节的执行器组合、速度/延迟/热模型和后续采购；
- H2 先做一条 5DOF 实体腿，H3 再做 10DOF 全身；
- 首次全身站立使用限流外部电源，实测峰值电流后才确定电池/BMS/线径；
- `SIM_PASS`、`HIL_PASS`、`REAL_PASS` 不得互相冒充；物理能力只有 `REAL_PASS` 可以标记 DONE。

## Reference Prototype A

首台实体参考 Open Duck Mini v2 的约 42 cm class、每腿 5DOF、STS3215 总线和 Pi Zero 2 W runtime 思路，但外观、Sensor Head、配置和接口独立设计。

```text
固定/轻量 Sensor Head
       │
      Torso
  ┌────┴────┐
 Left      Right
  5DOF      5DOF
  │           │
 Hip Yaw   Hip Yaw
 Hip Roll  Hip Roll
 Hip Pitch Hip Pitch
 Knee      Knee
 Ankle     Ankle
  └──── 10 active joints ────┘
```

头部第一版固定，嘴和翅膀不做，相机到 H6 再加。重心、外壳和 Sensor Head 等效质量必须进入自有 MJCF 和 Sim2Real 记录。

## H1 执行器资格测试

C044（1:191）偏负载，C046（1:147）偏速度。宣传参数只用于筛选，仿真参数必须来自真实测试：

- 10°/30°/60° step response ×20；
- 空载与杠杆负载速度；
- 50 Hz command/read jitter 与丢包；
- 电流、电压、温度、tracking RMSE、deadband/backlash proxy；
- 拔线/断电后的 fail-safe 与恢复；
- 30 min 连续动作。

第一批目标预算约 ¥600–1,000；无实物、无数据时字段统一写 `TBD_MEASURE`。

## 计算与电气边界

- Pi Zero 2 W：本地 50 Hz runtime、watchdog、telemetry 和 ONNX inference；
- 现有 PC/GPU：训练、视觉、3DGS、VLA 等 offboard 工作；
- BNO085：V0.4 新购主 IMU；BNO055 仅作上游兼容；
- 舵机 7.4V 母线与逻辑 5V 分离；10DOF 不经 5A adapter 供电；
- 保险、物理断电、限流和左右腿电源注入是 H3 前置条件。

## 当前软件交付

- `HardwareManifest`：完整 SKU、候选 gear ratio、joint order、bus ID、hardware revision；
- `ActuatorProfile` 日志结构与 mock 资格测试；
- `ServoBus`、BNO085-first `ImuBackend` 和 BNO055 compatibility adapter；
- 50 Hz runtime 的 timeout、deadline、NaN、soft-limit 和断连基础；
- SIM/HIL/REAL evidence contract；
- 10DOF ONNX policy bundle 与哈希/contract 校验；
- WSL2 训练目录、调参入口和真机部署手册。

## 当前不做

完整 3DGS 平台、VLA 万能策略、World Gym、自研 PCB、复杂云服务和外部 Agent 真机写操作均不属于 H1。真实硬件到货前，mock 只能证明工具链可运行，不能算 HIL。
