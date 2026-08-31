# 硬件、工具与完整预算

更新时间：2026-08-31

这份清单覆盖从 H1 执行器资格测试到 10DOF 实体样机的配套硬件、工具、预算和采购触发器。它不是要求一次性买齐的购物车；所有型号都必须经过前一 Gate 的实测数据确认。

## 预算总览

| 范围 | 预计投入 | 说明 |
|---|---:|---|
| H1 核心电子件 | ¥582–860 | 两颗候选舵机、Adapter、BNO085、Pico |
| H1 可安全测试 | ¥712–1,140 | 核心件 + 保险/线材/断电 + 测试支架 |
| H1 从零配齐 | ¥1,187–1,740 | 再加 5 A 限流电源和可靠万用表 |
| H1 完整工具间 | ¥1,557–2,560 | 再加测温、拉力、压接、焊接和测量工具 |
| 10DOF 可站立/行走样机 | ¥4,500–6,500 | 含 10 颗舵机、结构、主控、配电、电池和基础工具；以 H1/H2 实测为准 |

最合理的第一笔预算是 **约 ¥1,500**。已有电源和万用表时，第一笔可以压缩到 **约 ¥800**。不要把未来整机预算提前变成一箱可能选错的零件。

## H1：现在购买

| 物料 | 数量 | 参考价 | 必须核对 | 用途 |
|---|---:|---:|---|---|
| FEETECH `ST-3215-C044` | 1 | ¥150–220 | 7.4 V、1:191、完整 `C044` 后缀 | 负载型候选 |
| FEETECH `ST-3215-C046` | 1 | ¥150–220 | 7.4 V、1:147、完整 `C046` 后缀 | 速度型候选 |
| Waveshare Bus Servo Adapter (A) | 1 | ¥35–60 | SKU 25514、USB/UART、A 版 | 单舵机通讯 |
| Adafruit 4754 / BNO085 | 1 | ¥217–300 | BNO085 原版 breakout | 主姿态传感器 |
| Raspberry Pi Pico / Pico 2 | 1 | ¥30–60 | 3.3 V IO、USB 数据线 | BNO085 到 PC 的桥接与记录 |
| 兆信 KXN-305D | 1 | ¥255–300 | 0–30 V / 0–5 A、可调限流 | 单舵机 H1；已有则不买 |
| 优利德 UT139C | 1 | ¥220–300 | 真有效值、直流电流、温度 | 接线、压降和温度；已有则不买 |
| 保险、线材、断电和端子 | 1 套 | ¥100–180 | 5 A 保险、16/18 AWG、XT30、绝缘与应力释放 | 安全通电 |
| 舵机测试架、摆臂 | 1 套 | ¥30–100 | 舵机牢固固定、摆臂有防脱 | 空载与可控负载测试 |

购买入口：

- [飞特官网列出的淘宝官方店](https://shop337717059.taobao.com/)；
- [淘宝搜索：STS3215-C044 7.4V](https://s.taobao.com/search?q=飞特%20STS3215-C044%207.4V)；
- [淘宝搜索：STS3215-C046 7.4V](https://s.taobao.com/search?q=飞特%20STS3215-C046%207.4V)；
- [淘宝搜索：Bus Servo Adapter A 25514](https://s.taobao.com/search?q=微雪%20Bus%20Servo%20Adapter%20A%2025514)；
- [淘宝搜索：Adafruit 4754 BNO085](https://s.taobao.com/search?q=Adafruit%204754%20BNO085)；
- [淘宝搜索：Raspberry Pi Pico 2](https://s.taobao.com/search?q=树莓派%20Pico%202)；
- [淘宝搜索：兆信 KXN-305D](https://s.taobao.com/search?q=兆信%20KXN-305D)；
- [淘宝搜索：优利德 UT139C](https://s.taobao.com/search?q=优利德%20UT139C)。

淘宝商品页和隐藏规格会变化，链接只作为入口。下单以包装/外壳完整 SKU、额定电压、固件版本和原厂线序为准，不以标题里的“STS3215”“19 kg”或商品主图为准。

### 发给舵机客服的核对话术

```text
需要 ST-3215-C044 7.4V ×1 和 ST-3215-C046 7.4V ×1。
请确认包装或外壳有完整 C044/C046 后缀，不是 C001、C018。
两颗尽量使用相同固件版本，并配原厂总线连接线、舵机盘/舵机臂和安装螺丝。
请在发货前提供型号标签与固件版本照片。
```

## 一次性实验工具

| 工具 | 必需性 | 参考价 | 作用 |
|---|---|---:|---|
| 5 A 可调限流电源 | H1 必需 | ¥255–300 | 从 0.5 A 限流开始安全 bring-up |
| 数字万用表 | H1 必需 | ¥220–300 | 极性、短路、压降、通断 |
| USB-C 数据线 | H1 必需 | ¥15–40 | Adapter 连接 PC；必须支持数据 |
| 5 A 保险丝与保险座 | H1 必需 | ¥10–30 | 单舵机支路保护 |
| XT30 或明确 DC 额定的断电开关 | H1 必需 | ¥10–40 | 可触达的物理断电 |
| 16/18 AWG 硅胶线 | H1 必需 | ¥20–50 | 舵机供电主线 |
| 端子、热缩管、扎带 | H1 必需 | ¥20–60 | 绝缘、应力释放和走线 |
| 固定台钳/测试底座 | H1 必需 | ¥30–150 | 防止舵机摆臂带着设备移动 |
| 红外测温枪 | 推荐 | ¥60–120 | 交叉验证舵机内部温度 |
| 0–5 kg 拉力计/砝码 | 推荐 | ¥50–150 | 结合已知臂长做受控负载测试 |
| 冷压钳与管形端子 | 推荐 | ¥50–100 | 防止散线、虚接和松脱 |
| 温控电烙铁 | H2 前准备 | ¥150–300 | XT30、配电和最终线束 |
| 数显卡尺 | H2 前准备 | ¥60–150 | CAD、打印公差和孔位核对 |
| 手机支架 | 推荐 | ¥20–80 | 固定机位保存 HIL/REAL 视频证据 |

不要用手抓舵机轴测试扭矩；不要反复堵转；不要让摆臂运动平面朝向脸部或身体。

## H2：H1 PASS 后补一条 5DOF 腿

数量和 SKU 由 H1 的 loaded speed、温升、电流与关节 p95 扭矩/速度决定。下面只用于预算，不用于提前下单。

| 物料 | 暂定数量 | 预计增量 | 采购条件 |
|---|---:|---:|---|
| 入选 STS3215 | 补足至 5 颗，另 1 颗备件可选 | ¥450–880 | H1 Gate Review 固定关节分配 |
| 单腿打印件 | 1 套 | ¥200–500 | 自有 CAD 冻结、打印方向与公差确认 |
| 舵机臂、轴承、M2/M3 螺丝、热熔铜螺母 | 1 套 | ¥100–300 | 以 CAD BOM 为准，不照搬 Open Duck 尺寸 |
| 独立配电母线、支路保险、电流采集 | 1 套 | ¥100–300 | 不让多舵机电流经过 5 A Adapter 铜箔 |
| 单腿固定支架/吊架 | 1 套 | ¥100–300 | 失控时脚不接触人和桌面 |
| 足底接触传感器 | 2 个，可选 | ¥10–80 | observation/telemetry 方案明确后采购 |

如果希望电源一次买到 H2，可将 KXN-305D 换成 0–30 V / 10–20 A 的可靠限流电源；高电流电源必须配独立分路保险和物理断电，不能把 10–20 A 经过最大 5 A 的 Bus Servo Adapter (A)。

## H3/H4：全身、主控和电池

| 物料 | 暂定数量 | 预计增量 | 采购条件 |
|---|---:|---:|---|
| 入选 STS3215 | 补足至 10 颗 + 1 颗备件可选 | ¥750–1,320 | 单腿 30 min 测试通过 |
| 第二条腿与机身打印件 | 1 套 | ¥400–1,000 | H2 无干涉、CAD revision 冻结 |
| 低层主控 | 1 | ¥150–500 | 在 Pi Zero 2 W 与更接近 Microduck 的 Radxa 路线之间完成 Gate Review |
| microSD、线束、安装件 | 1 套 | ¥80–200 | 主控确定 |
| 全身配电、分路保险、急停和总电流采集 | 1 套 | ¥200–500 | H2 峰值/持续电流已知 |
| 2S 高放电电池、BMS、平衡充电与低压保护 | 1 套 | ¥250–600 | H3 外部电源 stand 稳定后按实测电流选型 |
| 足底传感器 | 补足至 4 个，可选 | ¥20–160 | 真机策略是否使用 contact observation 已确定 |

电池阶段不采用“标称 20 A”但没有持续电流、MOSFET 温升和保护曲线资料的无名 BMS；也不通过绕过 BMS 的方式解决过流掉电。逻辑主控 5 V 与舵机 7.4 V 应有独立稳压路径和共同参考地，防止舵机压降拖垮主控。

## H6 以后：感知和表达硬件

以下都不是当前 locomotion 关键路径：Camera、ToF/RGB-D、麦克风、扬声器、LED、头部/嘴部/翅膀舵机、Jetson 和 LiDAR。只有站立、行走和恢复获得 `REAL_PASS`，并且新增任务给出 observation、功耗、重量和接口预算后才采购。

如果后续训练“跳跃时同步展开翅膀”，必须先把翅膀 DOF、质量、惯量、舵机速度、软限位和结构空间加入自有模型与 HardwareManifest。当前 10DOF 腿部硬件不能凭软件奖励产生真实可动翅膀。

## 到货和证据记录

每件机器人专用物料至少记录：

- 厂商、完整型号、硬件 revision、固件版本；
- 店铺、订单日期、单价、数量和替代料；
- 包装/铭牌/线序照片；
- 重量、尺寸、接头和线长；
- 资格测试 artifact 目录与结论；
- 失败、退换货和批次差异。

真实 H1 数据分别写入 `artifacts/h1-c044-real/`、`artifacts/h1-c046-real/` 和 `artifacts/h1-bno085-real/`。当前 qualification CLI 只有 mock backend，实物到货后还需实现 `FeetechServoBus`、Windows COM/WSL USB 连接与 BNO085/Pico backend，才能生成 HIL/REAL 证据。

## 权威资料

- [C044 官方规格书](https://files.seeedstudio.com/products/Feetech/101090141_Feetech_ST-3215-C044_Datasheet.pdf)
- [C046 官方规格书](https://files.seeedstudio.com/products/Feetech/101090142_Feetech_ST-3215-C046_Datasheet.pdf)
- [Bus Servo Adapter (A) 文档](https://docs.waveshare.com/Bus_Servo_Adapter_A)
- [Bus Servo Adapter (A) 最大 5 A 与无稳压说明](https://docs.waveshare.com/Bus_Servo_Adapter_A/FAQ)
- [Adafruit BNO085](https://www.adafruit.com/product/4754)
- [BNO085 UART-RVC](https://learn.adafruit.com/adafruit-9-dof-orientation-imu-fusion-breakout-bno085/uart-rvc-for-python-circuitpython)
- [Raspberry Pi Zero 2 W](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/)

