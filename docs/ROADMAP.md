# V0.4 Hardware-First Roadmap

Gate 同时控制预算、软件范围和完成口径。物理能力只有 `REAL_PASS` 可以标记 DONE。

| Gate | 目标 | 累计预算 | 通过条件 |
|---|---|---:|---|
| H0 | 上游仿真基线 | ¥0 | 固定 commit、viewer/policy、GPU 训练和量化评估可复现 |
| H1 | 执行器与 IMU 资格测试 | ¥1,187–1,740（从零配工具） | C044/C046 50 Hz、step、速度、温升、延迟、断连数据归档；完成选型 |
| H2 | 一条 5DOF 实体腿 | ¥2,200–3,500 | 支架上 30 min 轨迹、无机械干涉、峰值电流已知 |
| H3 | 10DOF 全身 Stand | ¥4,000–6,000 | 外部限流供电；10 次上电至少 8 次安全 stand；brownout=0 |
| H4 | 无绳 2 m 行走 | ¥4,500–6,500 | 2 m ×10，至少 7 次成功 |
| H5 | 跌倒恢复 | 同阶段核价 | 标准跌倒 10 次至少 7 次恢复且无需重启 |
| H6 | 找人并靠近 | 同阶段核价 | Camera 3 + 真实 Hero Demo `REAL_PASS` |
| H7 | 地毯/轻坡/小高差 | 按实验核价 | terrain-aware locomotion 真实成功率报告 |
| H8 | 陌生房间定位与数据面 | 按传感器核价 | RGB/IMU/Pose 可标定、重放和追溯 |
| H9 | 真实房间 3D 重建 | 独立核价 | raw data 可重建浏览的 3D artifact |
| H10 | Spatial Memory | 软件为主 | 空间实体带 pose、版本和证据可查询 |
| H11 | Agent + Skills | 软件为主 | 探索/找目标/失败重规划通过真实场景 |
| H11.5 | Claude/Codex 受控真机调用 | 软件为主 | 白名单 Skill、lease、approval、audit 完整 |
| H12–H13 | VLA / World Action Model | 按算力核价 | 对照实验相对传统 Skill/Policy 有量化增益 |
| H14 | 跨本体复用 | 另行设计 | 第二种本体复用高层 contract |

## H0：已通过

- [x] WSL2 Ubuntu、Python、uv、Git、NVIDIA GPU 可识别；
- [x] Microduck RL、Open Duck Playground 和 MuJoCo commit 已固定；
- [x] 官方 tests、task registry、viewer/policy 和 64 env smoke 通过；
- [x] 4,096 env GPU 长训练完成，`model_1000.pt` 通过固定直行评估；
- [x] 命令、日志、GPU、checkpoint、ONNX、视频与失败证据已归档。

H0 的官方模型是 14DOF 参考，不是 V0.4 10DOF 真机策略。

## 当前 Gate：H1

- [x] V0.4 `HardwareManifest` 与完整 C044/C046 SKU 已建立；
- [x] H1 qualification plan、CSV/JSON logger 和 mock backend 已实现；
- [x] BNO085-first `ImuBackend` 与 BNO055 compatibility adapter 已实现；
- [x] 50 Hz mock runtime 的 timeout、deadline、NaN、soft-limit 与断连安全基础已实现；
- [x] SIM/HIL/REAL evidence contract 和 10DOF policy bundle gate 已实现；
- [x] 第一批采购清单、候选分配假设、到货测试顺序与扩批触发器已成文；
- [ ] 下单并核验 C044×1、C046×1、Bus Servo Adapter (A)×1、BNO085×1；
- [ ] 真实执行 step/速度/30 min/断连测试；
- [ ] 根据数据完成 `ActuatorProfile` 与 H1 Gate Review；
- [ ] H1 PASS 后才补齐一条腿的舵机和打印件。

## 止损规则

- 两个候选执行器都不满足速度、温升或延迟要求时，停止补货并更换执行器体系；
- 单腿机械/功率路线不成立时，不打印第二条腿；
- H3 stand 不稳定时，先修 hardware/model，不用更复杂 AI 掩盖；
- H6 Hero Demo 通过前，不采购 Jetson、RGB-D、LiDAR 或头部多自由度。
