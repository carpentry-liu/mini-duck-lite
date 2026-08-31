# H1 硬件采购与资格测试指南

更新时间：2026-08-31

## 结论

**现在可以买 H1 第一批资格测试硬件，但不要一次买满 10 个舵机。**

软件侧已经具备下单前应完成的最小准备：10DOF `HardwareManifest`、候选执行器配置、`ServoBus` / `ImuBackend` 接口、50 Hz qualification logger、安全 runtime 基础，以及 SIM/HIL/REAL 证据约束。实物到货后需要补的是真实 STS3215 通讯 backend、BNO085 总线校准和实测参数；这些工作依赖设备本身，不适合继续用 mock 猜测。

## 第一批只买这些

| 物料 | 数量 | 下单时必须核对 | 用途 |
|---|---:|---|---|
| FEETECH `ST-3215-C044` | 1 | 完整后缀 `C044`、7.4 V、1:191 | 负载型候选执行器 |
| FEETECH `ST-3215-C046` | 1 | 完整后缀 `C046`、7.4 V、1:147 | 速度型候选执行器 |
| Waveshare Bus Servo Adapter (A) | 1 | A 版、USB/UART 能连接 PC | H1 通讯与单舵机测试 |
| BNO085 breakout | 1 | 确认为 BNO085，不用 BNO055 替代首选型号 | IMU 数据率、时间戳与标定测试 |
| 7.4 V 可限流台式电源 | 1 | 至少 5 A，优先 10 A；已有则不重复买 | H1 外部安全供电 |
| 保险丝、急停/物理断电、线材和端子 | 1 套 | 16/18 AWG 主电源线、绝缘与应力释放 | 防短路和快速切断 |
| 万用表 | 1 | 已有则不重复买 | 接线、压降与连续性检查 |

官方 7.4 V 数据用于理解候选差异，不作为整机选型结论：

| 型号 | 减速比 | 空载速度 | 额定负载 | 堵转扭矩 | 额定/堵转电流 |
|---|---:|---:|---:|---:|---:|
| C044 | 1:191 | 0.116 s/60°，86 RPM | 9 kg·cm | 27.4 kg·cm | 1.2 / 3.8 A |
| C046 | 1:147 | 0.094 s/60°，106 RPM | 4.8 kg·cm | 14.4 kg·cm | 1.1 / 3.3 A |

来源：[C044 官方规格书](https://files.seeedstudio.com/products/Feetech/101090141_Feetech_ST-3215-C044_Datasheet.pdf)、[C046 官方规格书](https://files.seeedstudio.com/products/Feetech/101090142_Feetech_ST-3215-C046_Datasheet.pdf)。两个型号的输入范围均为 5–8.4 V、重量约 55 g，并支持位置、速度、电压、电流和温度反馈。堵转扭矩不能当作持续工作扭矩使用。

## 这些暂时不要买

| 暂缓物料 | 采购触发条件 |
|---|---|
| 剩余 8 个或更多舵机 | H1 对比完成，关节分配和 `ActuatorProfile` 经 Gate Review 固定 |
| 一整套第二条腿机械件 | H2 单腿 30 分钟测试通过，无干涉且峰值电流已知 |
| Pi Zero 2 W | H2 通过并开始 H3 全身 Stand 集成；H1 先使用现有 PC |
| 2S 电池、BMS 和充电系统 | H3 外部电源站立稳定，拿到真实整机峰值/持续电流后选型 |
| Camera、RGB-D、Jetson、LiDAR、头部舵机 | H6 以前不是 locomotion 的关键路径 |

Bus Servo Adapter (A) 用于通讯，不能把它当成 10DOF 整机配电板。官方 FAQ 给出的最大电流为 5 A；H1 负载测试一次只接一颗舵机，整机阶段另做有保险和物理断电的独立电源母线。来源：[Waveshare Bus Servo Adapter (A) FAQ](https://docs.waveshare.com/Bus_Servo_Adapter_A/FAQ)。

## C044 和 C046 怎么分配

当前只建立**待验证假设**，不提前把 SKU 写死到关节：

| 关节类型 | 初始候选 | 原因 | 最终依据 |
|---|---|---|---|
| hip pitch、knee | C044 优先 | 更高额定负载，适合主要承重关节 | 仿真 p95 扭矩/速度 + H1/H2 实测 |
| hip yaw、hip roll、ankle | C046 优先 | 空载速度更高 | 跟踪误差、速度余量、温升和冲击 |

每个关节先从自有 10DOF 仿真导出 p95 扭矩和 p95 速度，再与实测的 loaded speed、连续负载、温升、延迟和电流比较。初始工程门槛采用速度至少保留 25% 余量、连续扭矩至少保留 50% 余量；这是项目的保守设计目标，不是厂商保证值。任一指标不满足就改 SKU、连杆尺寸、质量分配或步态，不靠提高电流硬顶。

## 到货后按这个顺序做

1. 拍照归档包装、铭牌和完整 SKU；检查线序、短路、端子和外壳损伤。
2. 只接 Adapter、限流电源和一颗舵机；不要安装到腿上，先读取 ID、位置、电压、电流和温度。
3. 为 C044、C046 分别执行 10°/30°/60° step ×20、速度、延迟、抖动、丢包和断连恢复。
4. 在可控载荷与物理断电可触达的条件下执行 30 分钟热测试，记录 50 Hz 原始 CSV 和汇总 JSON。
5. 接入 BNO085，验证 I2C/UART 方案、输出频率、单调时间戳、calibration 和 stale/NaN 故障处理。接线与库用法可参考 [Adafruit BNO085 指南](https://learn.adafruit.com/adafruit-9-dof-orientation-imu-fusion-breakout-bno085/python-circuitpython)。
6. 将结果回写 `ActuatorProfile`、`HardwareManifest` 与 MuJoCo actuator 参数，完成 H1 Gate Review。
7. H1 通过后才补齐一条 5DOF 腿；H2 通过后才采购第二条腿和 H3 计算硬件。

舵机规格书的运行温度范围上限为 60 ℃、过热保护为高于 70 ℃关闭扭矩。本项目 H1 首轮采用 **55 ℃软件停止测试**，为环境误差、热惯性和批次差异留余量；这是一条项目安全边界，不代表厂商额定值。

## 软件到什么程度才可以上硬件

| 准入项 | 当前状态 | 是否阻塞采购 |
|---|---|---|
| 关节顺序、SKU、单位和未知字段显式化 | 已完成 | 否 |
| mock qualification 与日志格式 | 已完成 | 否 |
| timeout、deadline、NaN、断连、soft-limit 基础 | 已完成 | 否 |
| mock 不能冒充 HIL/REAL | 已完成 | 否 |
| 真实 STS3215 backend | 待实物联调 | 不阻塞第一批，阻塞 H1 PASS |
| BNO085 真实总线与标定 | 待实物联调 | 不阻塞第一批，阻塞 H1 PASS |
| 自有 10DOF MJCF / policy | 待实测参数 | 不阻塞 H1，阻塞 H3 |
| 物理急停、保险、限流电源 | 随第一批准备 | 阻塞任何通电测试 |

换句话说：**第一批硬件现在可以买；整机硬件要等数据，不要靠猜。**

## 分阶段采购触发器

```text
当前软件准备完成
  → 买 H1 两颗舵机 + Adapter + BNO085 + 安全供电
  → H1 资格测试 PASS
  → 补齐 5DOF 单腿
  → H2 单腿 30 min PASS
  → 补齐 10DOF 全身 + Pi Zero 2 W
  → H3 外部电源 Stand PASS
  → 按实测峰值电流采购电池/BMS
  → H4 无绳 Walk
```

Pi Zero 2 W 的正式定位是 H3 低层 runtime，而非 H1 测试必需品；产品规格见 [Raspberry Pi 官方页面](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/)。
