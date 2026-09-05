# 红树林垃圾识别监测系统 — 后端PDR文档

> **项目名称**：红树林垃圾识别监测系统  
> **文档类型**：PDR（Preliminary Design Review，初步设计评审文档）  
> **负责模块**：后端存储服务层  
> **版本**：V1.0  
> **日期**：2026-09-03

---

## 一、项目概述

### 1.1 项目背景

本项目为大学生科技创新竞赛作品，旨在构建一套基于物联网的红树林生态监测平台。系统通过水质传感器和摄像头实时采集红树林水域的环境数据，利用YOLOv8算法识别水面垃圾，实现生态监测的数字化和智能化。

### 1.2 系统五层架构

| 层级 | 名称 | 技术方案 | 说明 |
|------|------|----------|------|
| 第1层 | 终端感知层 | ESP32 + 网络摄像头 | 采集水质参数（pH、TDS、浊度、溶解氧）和视频流 |
| 第2层 | 传输层 | MQTT + RTSP | 传感器数据通过MQTT上报，视频通过RTSP协议传输 |
| 第3层 | 边缘计算层 | YOLOv8 | 对摄像头画面进行垃圾目标检测和分类 |
| 第4层 | 后端存储服务层 | **本模块（FastAPI）** | 数据存储、API服务、实时推送 |
| 第5层 | 前端展示层 | Vue3 + TypeScript | 数据可视化大屏展示 |

### 1.3 后端职责

- 接收MQTT上报的水质传感器数据，写入InfluxDB时序数据库
- 接收YOLO算法上报的垃圾识别结果，写入MySQL关系型数据库
- 提供RESTful API供前端查询和管理
- 通过WebSocket向前端实时推送水质数据和垃圾识别通知
- 管理设备注册、心跳检测、在线状态追踪
- 管理摄像头配置和视频流代理

---

## 二、技术选型

### 2.1 技术栈总览

| 类别 | 技术选型 | 版本 | 选型理由 |
|------|----------|------|----------|
| Web框架 | FastAPI | 0.110.0 | 异步高性能、自动生成Swagger文档、类型校验 |
| ASGI服务器 | Uvicorn | 0.28.0 | 原生异步支持、生产级稳定 |
| 关系型数据库 | MySQL | 5.7 | 存储结构化垃圾识别记录，成熟稳定 |
| 时序数据库 | InfluxDB 3 | 3.x | 存储高频传感器数据，按时间聚合查询高效 |
| MQTT客户端 | Paho-MQTT | 1.6.1 | Python生态最成熟的MQTT客户端库 |
| WebSocket | FastAPI原生 | - | 与HTTP同端口，无需额外组件 |
| 配置管理 | python-dotenv | 1.0.0 | 环境变量隔离，便于部署 |

### 2.2 依赖清单

```
fastapi==0.110.0
uvicorn==0.28.0
pydantic==2.6.0
mysql-connector-python==8.3.0
influxdb-client==1.36.0
paho-mqtt==1.6.1
python-dotenv==1.0.0
python-dateutil==2.9.0
python-multipart
```

---

## 三、系统架构设计

### 3.1 模块架构图

```
                    ┌─────────────────────────────────┐
                    │         前端 Vue3 页面           │
                    │  (Dashboard / 水质 / 垃圾 / 设备) │
                    └──────┬──────────────┬───────────┘
                           │ HTTP REST    │ WebSocket
                           ▼              ▼
                    ┌─────────────────────────────────┐
                    │       FastAPI 后端服务           │
                    │        (main.py 入口)            │
                    ├─────────────────────────────────┤
                    │  ┌──────────┐  ┌──────────────┐  │
                    │  │api_routes│  │  ws_manager  │  │
                    │  │  (路由)   │  │ (WebSocket)  │  │
                    │  └────┬─────┘  └──────┬───────┘  │
                    │       │               │          │
                    │  ┌────▼─────┐  ┌─────▼────────┐ │
                    │  │mysql_op  │  │ influxdb_op  │ │
                    │  │(MySQL操作)│  │(InfluxDB操作) │ │
                    │  └────┬─────┘  └─────┬────────┘ │
                    │       │               │          │
                    │  ┌────▼─────┐  ┌─────▼────────┐ │
                    │  │stats_op  │  │  mqtt_sub    │ │
                    │  │(数据统计) │  │ (MQTT订阅)   │ │
                    │  └──────────┘  └──────────────┘ │
                    │  ┌──────────┐  ┌──────────────┐  │
                    │  │device_mgr│  │ video_proxy  │  │
                    │  │(设备管理) │  │ (视频流代理) │  │
                    │  └──────────┘  └──────────────┘  │
                    └─────────────────────────────────┘
                           │               │
                           ▼               ▼
                    ┌──────────┐    ┌──────────────┐
                    │  MySQL   │    │   InfluxDB   │
                    │ (垃圾记录) │    │  (水质时序)  │
                    └──────────┘    └──────────────┘
```

### 3.2 数据流向

**水质数据链路：**
```
ESP32传感器 → MQTT Broker → mqtt_sub.py → influxdb_op.py → InfluxDB
                                         → ws_manager.py → WebSocket → 前端实时图表
```

**垃圾识别链路：**
```
摄像头RTSP流 → YOLOv8算法 → HTTP POST /api/v1/garbage/detect → mysql_op.py → MySQL
                                                              → ws_manager.py → WebSocket → 前端弹窗通知
```

**前端查询链路：**
```
前端Vue → axios GET /api/v1/... → api_routes.py → mysql_op / influxdb_op / stats_op → 返回JSON
```

### 3.3 启动流程

```
main.py 启动
  ├── 1. 初始化MySQL连接 + 自动建表
  ├── 2. 初始化InfluxDB连接（失败不阻断启动）
  ├── 3. 初始化MQTT客户端 → 连接Broker → 后台线程启动订阅循环
  └── 4. Uvicorn启动HTTP服务，监听8000端口
```

### 3.4 模块文件清单

| 文件名 | 职责 | 代码行数 |
|--------|------|----------|
| [main.py](file:///c:/Users/joose/OneDrive/Desktop/honshu/main.py) | 应用入口，启动初始化 | ~140行 |
| [config.py](file:///c:/Users/joose/OneDrive/Desktop/honshu/config.py) | 全局配置，加载环境变量 | ~63行 |
| [api_routes.py](file:///c:/Users/joose/OneDrive/Desktop/honshu/api_routes.py) | 全部HTTP/WebSocket路由定义 | ~792行 |
| [mysql_op.py](file:///c:/Users/joose/OneDrive/Desktop/honshu/mysql_op.py) | MySQL操作（垃圾记录CRUD） | ~344行 |
| [influxdb_op.py](file:///c:/Users/joose/OneDrive/Desktop/honshu/influxdb_op.py) | InfluxDB操作（水质数据读写） | ~262行 |
| [stats_op.py](file:///c:/Users/joose/OneDrive/Desktop/honshu/stats_op.py) | 数据统计（仪表盘/趋势/异常） | ~375行 |
| [mqtt_sub.py](file:///c:/Users/joose/OneDrive/Desktop/honshu/mqtt_sub.py) | MQTT订阅服务（传感器数据接收） | ~167行 |
| [ws_manager.py](file:///c:/Users/joose/OneDrive/Desktop/honshu/ws_manager.py) | WebSocket连接管理和广播 | ~79行 |
| [device_manager.py](file:///c:/Users/joose/OneDrive/Desktop/honshu/device_manager.py) | 设备注册/心跳/状态管理 | ~315行 |
| [video_proxy.py](file:///c:/Users/joose/OneDrive/Desktop/honshu/video_proxy.py) | 摄像头配置管理/视频流代理 | ~305行 |
| [seed_data.py](file:///c:/Users/joose/OneDrive/Desktop/honshu/seed_data.py) | 种子数据生成（测试用） | ~182行 |

---

## 四、数据库设计

### 4.1 MySQL — 关系型数据

**数据库**：`mangrove_db`（字符集 utf8mb4）

**表1：垃圾识别记录表 `garbage_detect_record`**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT AUTO_INCREMENT | 自增主键 |
| camera_id | VARCHAR(50) NOT NULL | 摄像头设备号 |
| detect_time | DATETIME NOT NULL | 识别时间 |
| garbage_type | VARCHAR(50) NOT NULL | 垃圾种类（塑料袋/塑料瓶/渔网/易拉罐等） |
| count | INT DEFAULT 1 | 单次识别垃圾总数 |
| confidence | FLOAT DEFAULT 0 | 平均置信度 |
| image_path | VARCHAR(500) | 抓拍图片本地路径 |
| created_at | DATETIME DEFAULT CURRENT_TIMESTAMP | 记录创建时间 |

**索引：**
- `idx_camera_id` — 摄像头编号索引（按设备筛选加速）
- `idx_detect_time` — 识别时间索引（按时间范围查询加速）
- `idx_garbage_type` — 垃圾类型索引（按类型统计加速）

### 4.2 InfluxDB — 时序数据

**Bucket（数据库）**：`water_quality`

**Measurement（测量）**：`water_quality`

| 字段名 | 类型 | 说明 |
|--------|------|------|
| time | timestamp | 时间戳（自动生成） |
| device_id | tag | 设备ID（标签，用于过滤） |
| ph | field (float) | pH值 |
| tds | field (float) | TDS值（ppm） |
| turbidity | field (float) | 浊度（NTU） |
| dissolved_oxygen | field (float) | 溶解氧（mg/L） |

### 4.3 JSON配置文件

**设备配置 `config/devices.json`**：存储设备注册信息（ID、名称、类型、位置、MQTT主题等）

**摄像头配置 `config/cameras.json`：**存储摄像头配置（ID、名称、RTSP地址、位置、在线状态等）

### 4.4 水质数据校验规则

```python
WATER_QUALITY_RULES = {
    'ph':                {'min': 6.0, 'max': 8.5,  'default': 7.0},
    'tds':               {'min': 100, 'max': 500,  'default': 300},
    'turbidity':         {'min': 0,   'max': 50,   'default': 15},
    'dissolved_oxygen':  {'min': 4.0, 'max': 9.0,  'default': 7.0}
}
```

写入InfluxDB时自动校验，超出范围的值替换为默认值，确保数据质量。

---

## 五、API接口设计

### 5.1 接口总览

所有接口前缀：`/api/v1`

| 分类 | 接口 | 方法 | 说明 |
|------|------|------|------|
| **水质数据** | /water/history | GET | 查询历史水质时序数据 |
| | /water/latest | GET | 获取最新水质数据 |
| | /water/data | POST | 写入水质数据（模拟MQTT） |
| **垃圾识别** | /garbage/detect | POST | 接收YOLO识别结果（含图片上传） |
| | /garbage/records | GET | 分页查询垃圾记录 |
| | /garbage/stats/today | GET | 当日垃圾统计 |
| | /garbage/cameras | GET | 摄像头列表 |
| | /garbage/types | GET | 垃圾类型列表 |
| **视频流** | /video/cameras | GET/POST | 摄像头CRUD |
| | /video/cameras/{id} | GET/PUT/DELETE | 单个摄像头操作 |
| | /video/cameras/{id}/snapshot | POST | 获取摄像头快照 |
| | /video/stream/{id} | WebSocket | 视频流WebSocket代理 |
| **设备管理** | /devices/register | POST | 设备注册 |
| | /devices/{id}/heartbeat | POST | 设备心跳上报 |
| | /devices | GET | 设备列表 |
| | /devices/stats | GET | 设备统计 |
| | /devices/{id} | GET/PUT/DELETE | 单个设备操作 |
| **数据统计** | /stats/dashboard | GET | 仪表盘汇总数据 |
| | /stats/water/quality | GET | 水质统计（均值/极值） |
| | /stats/water/trend | GET | 水质趋势（按时间聚合） |
| | /stats/water/anomalies | GET | 水质异常记录 |
| | /stats/water/comparison | GET | 水质同比对比 |
| **实时推送** | /ws | WebSocket | 实时数据推送 |
| **健康检查** | /health | GET | 服务状态检测 |

### 5.2 核心接口详情

#### 5.2.1 仪表盘汇总 — GET /api/v1/stats/dashboard

**用途**：前端大屏首页展示，一次请求获取全部核心指标

**返回结构**（对齐前端 `DashboardStats` 类型）：
```json
{
  "device_total": 1,
  "device_online": 1,
  "device_offline": 0,
  "camera_total": 3,
  "camera_online": 2,
  "garbage_today": 111,
  "water_compliance_rate": 99.5,
  "water_anomalies": 2
}
```

**数据来源**：
- 设备统计 ← `config/devices.json`
- 摄像头统计 ← `config/cameras.json`
- 今日垃圾数 ← MySQL `garbage_detect_record` 表
- 水质达标率 & 异常数 ← InfluxDB `water_quality` measurement

#### 5.2.2 垃圾识别结果上报 — POST /api/v1/garbage/detect

**调用方**：边缘端YOLOv8算法

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| camera_id | string | 是 | 摄像头编号 |
| garbage_type | string | 是 | 垃圾种类 |
| count | int | 否 | 数量，默认1 |
| confidence | float | 否 | 置信度 |
| detect_time | string | 否 | 识别时间 |
| image_file | file | 否 | 抓拍图片 |

**流程**：保存图片到本地 → 写入MySQL → WebSocket推送前端

#### 5.2.3 水质趋势 — GET /api/v1/stats/water/trend

**返回结构**（对齐前端 `WaterTrendPoint[]`）：
```json
[
  { "timestamp": "2026-09-03T10:00:00Z", "value": 7.2 },
  { "timestamp": "2026-09-03T11:00:00Z", "value": 7.5 }
]
```

**查询逻辑**：InfluxDB SQL `DATE_TRUNC` 按时间间隔聚合，支持ph/tds/turbidity/dissolved_oxygen四个指标

#### 5.2.4 WebSocket实时推送 — ws://host:8000/api/v1/ws

**消息格式**：
```json
{
  "type": "water_quality",
  "data": { "device_id": "esp32_01", "ph": 7.2, "tds": 320, ... }
}
```

```json
{
  "type": "garbage_detection",
  "data": { "camera_id": "camera_01", "garbage_type": "塑料袋", ... }
}
```

---

## 六、核心模块设计

### 6.1 MySQL操作模块 (mysql_op.py)

**设计要点**：
- 全局单例连接 + 自动重连机制（`is_connected()` 检测，断开自动重连）
- 垃圾记录CRUD：`save_garbage_record` / `query_garbage_records` / `get_today_stats`
- 分页查询支持：`page` + `page_size`，通过 `LIMIT/OFFSET` 实现
- 支持按摄像头ID和垃圾类型筛选
- 自动建表（启动时 `CREATE TABLE IF NOT EXISTS`）

### 6.2 InfluxDB操作模块 (influxdb_op.py)

**设计要点**：
- 写入使用 `influxdb_client` Python SDK（Point + WriteApi同步模式）
- 查询使用 `influxdb3` 命令行工具（subprocess调用，适配InfluxDB 3.x）
- CLI路径通过环境变量 `INFLUXDB_CLI_PATH` 配置，跨平台支持
- 写入时自动数据校验：pH/TDS/浊度/溶解氧 超范围替换为默认值
- **容错设计**：InfluxDB连接失败不阻断启动，查询失败返回空列表

### 6.3 MQTT订阅模块 (mqtt_sub.py)

**设计要点**：
- 订阅主题：`mangrove/water/+`（通配符匹配所有设备）
- 从主题提取设备ID：`mangrove/water/{device_id}` → 自动填充payload
- 数据校验：必填字段（ph/tds/turbidity/dissolved_oxygen）缺失则跳过
- 异常断开自动重连（5秒延迟）
- 后台守护线程运行（`loop_forever`），不影响主进程

### 6.4 WebSocket管理器 (ws_manager.py)

**设计要点**：
- `ConnectionManager` 单例管理所有活跃连接
- `broadcast()` 广播给所有连接的前端客户端
- 两种推送类型：`water_quality`（水质数据）和 `garbage_detection`（垃圾识别）
- 连接断开自动移除，广播失败自动清理

### 6.5 数据统计模块 (stats_op.py)

**设计要点**：
- 返回结构严格对齐前端TypeScript接口定义
- `_execute_influxdb_query_safe()` 安全查询，失败返回fallback
- 仪表盘数据聚合多个数据源（JSON配置 + MySQL + InfluxDB）
- 水质异常检测：逐条检查是否超出 `WATER_QUALITY_RULES` 范围

### 6.6 设备管理模块 (device_manager.py)

**设计要点**：
- 设备配置持久化到 `config/devices.json`
- 内存缓存心跳状态（`_device_status` 字典）
- 心跳超时阈值60秒，超时自动标记离线
- 设备未注册时自动注册（心跳触发）

### 6.7 视频流代理模块 (video_proxy.py)

**设计要点**：
- 摄像头配置持久化到 `config/cameras.json`
- RTSP流快照：调用 `ffmpeg` 截取单帧保存为图片
- 摄像头在线检测：通过ffmpeg尝试连接RTSP流
- WebSocket视频流代理：模拟帧推送（可扩展为真实ffmpeg管道）

---

## 七、配置管理

### 7.1 环境变量 (.env)

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| MYSQL_HOST | localhost | MySQL主机 |
| MYSQL_PORT | 3306 | MySQL端口 |
| MYSQL_USER | root | MySQL用户名 |
| MYSQL_PASSWORD | 123456 | MySQL密码 |
| MYSQL_DATABASE | mangrove_db | 数据库名 |
| INFLUXDB_URL | http://localhost:8086 | InfluxDB地址 |
| INFLUXDB_TOKEN | my_secret_token | InfluxDB认证Token |
| INFLUXDB_ORG | mangrove_org | InfluxDB组织名 |
| INFLUXDB_BUCKET | water_quality | InfluxDB Bucket名 |
| INFLUXDB_CLI_PATH | influxdb3 | InfluxDB CLI路径 |
| MQTT_BROKER | localhost | MQTT Broker地址 |
| MQTT_PORT | 1883 | MQTT端口 |
| MQTT_TOPIC | mangrove/water/+ | MQTT订阅主题 |
| MQTT_CLIENT_ID | mangrove_backend | MQTT客户端ID |
| API_HOST | 0.0.0.0 | API监听地址 |
| API_PORT | 8000 | API监听端口 |
| IMAGE_STORE_PATH | ./uploads/images | 图片存储路径 |

### 7.2 CORS配置

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # 允许所有来源（部署阶段）
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 八、部署方案

### 8.1 部署环境

| 项目 | 配置 |
|------|------|
| 云服务器 | 腾讯云 CVM |
| 操作系统 | OpenCloudOS（RHEL系） |
| Python | 3.11.6 |
| MySQL | 5.7.44 |
| Mosquitto | 2.0.18 |
| 管理面板 | 宝塔面板 |
| 服务器IP | 81.71.69.247 |
| 后端端口 | 8000 |

### 8.2 部署步骤

1. **创建项目目录**：`/www/wwwroot/mangrove-backend/`
2. **创建Python虚拟环境**：`python3 -m venv venv`
3. **安装依赖**：`pip install -r requirements.txt`
4. **上传代码文件**：通过宝塔面板文件管理上传
5. **配置环境变量**：创建 `.env` 文件
6. **重置MySQL密码**：通过宝塔面板数据库管理
7. **初始化数据库**：`python3 seed_data.py`
8. **启动后端**：`nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 &`
9. **放行端口**：腾讯云安全组 + 服务器防火墙放行8000端口

### 8.3 本地开发环境

| 项目 | 配置 |
|------|------|
| 操作系统 | Windows |
| Python | 3.x |
| 启动命令 | `python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload` |
| API地址 | http://localhost:8000 |
| Swagger文档 | http://localhost:8000/docs |
| WebSocket | ws://localhost:8000/api/v1/ws |

---

## 九、数据安全与容错

### 9.1 容错机制

| 场景 | 处理方式 |
|------|----------|
| InfluxDB连接失败 | 不阻断启动，查询返回空列表，前端显示"暂无数据" |
| MQTT连接失败 | 打印警告日志，不影响HTTP服务正常运行 |
| MySQL连接断开 | 自动重连（`is_connected()` 检测 + 重连逻辑） |
| 水质数据异常值 | 自动替换为默认值，确保数据质量 |
| WebSocket广播失败 | 自动移除断开的连接，不影响其他客户端 |
| ffmpeg未安装 | 视频快照功能降级，返回提示信息 |

### 9.2 数据校验

- 水质数据：pH 6.0-8.5、TDS 100-500ppm、浊度 0-50 NTU、溶解氧 4.0-9.0 mg/L
- 垃圾识别：必填字段校验（camera_id、garbage_type、detect_time）
- 分页查询：page >= 1，page_size 1-100

---

## 十、已知问题与后续计划

### 10.1 已知问题

| 问题 | 状态 | 影响 |
|------|------|------|
| InfluxDB 3 在云服务器安装失败 | 未解决 | 水质数据仅本地可用，云服务器显示默认值 |
| 后端进程未做守护 | 待解决 | 服务器重启后需手动启动后端 |
| MQTT Broker未配置认证 | 待优化 | 安全风险（竞赛演示环境可接受） |

### 10.2 后续计划

1. **InfluxDB安装**：尝试Docker方式部署InfluxDB 2.x
2. **进程守护**：使用 systemd 或 supervisor 管理后端进程
3. **鸟类识别功能**：新增鸟类图像识别接口，复用垃圾分类的上报流程
4. **接口文档完善**：补充Swagger注释和参数说明
5. **日志系统**：引入Python logging模块，替代print输出
6. **性能优化**：MySQL连接池、InfluxDB批量写入、WebSocket心跳保活
7. **安全加固**：MQTT添加用户名密码认证、API接口限流

---

## 十一、附录

### 11.1 项目文件结构

```
honshu/
├── main.py                 # 应用入口
├── config.py               # 全局配置
├── api_routes.py           # API路由定义
├── mysql_op.py             # MySQL操作
├── influxdb_op.py          # InfluxDB操作
├── stats_op.py             # 数据统计
├── mqtt_sub.py             # MQTT订阅
├── ws_manager.py           # WebSocket管理
├── device_manager.py       # 设备管理
├── video_proxy.py          # 视频流代理
├── seed_data.py            # 种子数据生成
├── database_init.sql       # MySQL建表脚本
├── requirements.txt        # Python依赖
├── .env                    # 环境变量配置
├── config/
│   ├── devices.json        # 设备配置
│   └── cameras.json        # 摄像头配置
└── uploads/
    └── images/             # 垃圾识别抓拍图片
```

### 11.2 术语表

| 术语 | 说明 |
|------|------|
| ESP32 | 乐鑫科技物联网开发板，用于连接水质传感器 |
| YOLOv8 | 目标检测算法，用于识别水面垃圾 |
| MQTT | 轻量级消息协议，适合物联网设备通信 |
| InfluxDB | 时序数据库，适合存储传感器连续采集的数据 |
| Measurement | InfluxDB中的概念，相当于关系型数据库的表 |
| Point | InfluxDB中的数据点，包含tag(索引)、field(值)、time(时间戳) |
| RTSP | 实时流传输协议，用于摄像头视频流传输 |
| ASGI | 异步服务器网关接口，Python异步Web标准 |
| CORS | 跨域资源共享，允许浏览器跨域请求 |

---

> 文档作者：后端开发人员  
> 最后更新：2026-09-03
