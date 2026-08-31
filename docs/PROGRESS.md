# 当前进度

更新时间：2026-08-31

## 当前 Gate

**H1 · Hardware Qualification。H0 上游仿真基线已通过。**

V0.4 已将项目切换为 Hardware-First。官方 Microduck 14DOF 的 103.1M step GPU 训练仍作为可靠的训练/日志/评估参考；自有 10DOF 模型、实体舵机和真机策略尚未完成。

## 已完成

- WSL2 Ubuntu 24.04.3、Python 3.12.3、uv 0.11.7、RTX 5060 Ti 16 GB 训练链路通过；
- 官方 14DOF `model_1000.pt` 在 128 环境固定直行 10 秒时 128/128 不摔、0 NaN；
- V0.4 产品范围、Hardware-First Gate、真实部署链和工程边界已写入仓库；
- `HardwareManifest` 已固定 10DOF joint order、C044/C046 完整 SKU、BNO085-first 与 `TBD_MEASURE` 字段；
- H1 actuator qualification plan、mock bus、CSV/JSON logger 已实现；
- BNO085 backend、BNO055 compatibility adapter 和 mock IMU 已实现；
- 50 Hz mock runtime 已具备 command timeout、deadline、IMU stale/NaN、断连和 soft-limit 基础；
- 10DOF ONNX policy bundle 会校验 joint order、action size、normalizer、control rate、training commit 和 SHA256；
- SIM/HIL/REAL evidence contract 会阻止 mock 冒充真机完成；
- WSL2 训练目录、调参入口和 Pi/真机部署步骤已单独成文。
- H1 第一批采购清单、C044/C046 分配假设、到货顺序和后续扩批触发器已固定；软件已达到采购资格测试样机的条件。

## H1 尚未完成

- C044/C046、Bus Servo Adapter (A)、BNO085 与限流电源尚未接入；
- bus ID、真实零位、软限位、电流、速度、温升、延迟与 backlash 仍为 `TBD_MEASURE`；
- 真实 STS3215 backend、H1 30 min 测试和 H1 Gate Review 尚未完成；
- 自有 10DOF MJCF 和 Policy Contract 需在机械/执行器参数收敛后继续；
- 当前所有新增硬件命令只产生 `SIM_PASS`，不能标成 `HIL_PASS` 或 `REAL_PASS`。

## 下一任务

按 [`HARDWARE_PURCHASE.md`](HARDWARE_PURCHASE.md) 采购第一批 H1 资格测试套件，不批量购买 10 个舵机。到货后先核对外壳/包装完整后缀，再为 qualification CLI 接入真实 STS3215 backend；完成两颗候选舵机的 step、速度、30 min、温升、延迟与断连测试。H1 数据归档和选型通过后，才进入一条 5DOF 实体腿。

## 环境提示

WSL 启动会报告 `/etc/wsl.conf` 的 `user.default` 重复。该提示不阻塞 Ubuntu/GPU；仓库不修改系统级配置。
