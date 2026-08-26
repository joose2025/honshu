# 红树林垃圾识别监测系统 - 后端数据存储模块

> 作者：大二某不知名计算机学生（joose）
> 技术栈：FastAPI + MySQL + InfluxDB + MQTT + WebSocket

---

## 一、项目简介

本模块是红树林垃圾识别监测系统的后端数据存储服务，负责接收和存储传感器数据、垃圾识别结果，并向前端提供实时数据推送。

### 系统五层架构

```
┌─────────────────────────────────────────────────────────────┐
│  5. 前端Vue展示层                                           │
│     (实时展示、趋势图表、告警弹窗)                            │
├─────────────────────────────────────────────────────────────┤
│  4. 后端存储服务层 (本模块)                                  │
│     FastAPI + MySQL + InfluxDB + WebSocket                  │
├─────────────────────────────────────────────────────────────┤
│  3. 边缘计算层                                               │
│     YOLOv8垃圾识别算法                                       │
├─────────────────────────────────────────────────────────────┤
│  2. 传输层                                                  │
│     MQTT协议 + MediaMTX流媒体                               │
├─────────────────────────────────────────────────────────────┤
│  1. 终端感知层                                               │
│     ESP32单片机(水质传感器) + 网络摄像头                      │
└─────────────────────────────────────────────────────────────┘
```

### 数据流向

```
水质链路: ESP32传感器 → MQTT Broker → 本后端 → InfluxDB + WebSocket前端
垃圾识别链路: 摄像头RTSP流 → YOLO算法HTTP上报 → 本后端 → MySQL + 本地存图 + WebSocket前端
```

---

## 二、技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| 后端框架 | Python FastAPI | 高性能API服务 |
| 关系型数据库 | MySQL | 存储垃圾识别结构化记录 |
| 时序数据库 | InfluxDB | 存储水质传感器时序数据 |
| MQTT协议 | paho-mqtt | 接收ESP32传感器数据 |
| WebSocket | FastAPI WebSocket | 向前端实时推送数据 |
| 图片存储 | 本地文件系统 | 存储抓拍垃圾图片 |

---

## 三、项目文件结构

```
honshu/                                    # 后端主目录
├── main.py                                  # 应用入口，启动FastAPI服务
├── config.py                                # 配置文件，加载环境变量
├── requirements.txt                         # Python依赖清单
├── .env                                     # 环境配置文件(数据库密码等)
├── database_init.sql                        # MySQL建表脚本
├── influxdb_init.txt                        # InfluxDB初始化指南
├── README.md                                # 本说明文档
│
├── mysql_op.py                              # MySQL操作模块
│   ├── init_mysql()                         # 初始化连接和建表
│   ├── save_garbage_record()                # 保存垃圾识别记录
│   ├── query_garbage_records()              # 分页查询记录
│   └── get_today_stats()                    # 获取当日统计
│
├── influxdb_op.py                           # InfluxDB操作模块
│   ├── init_influxdb()                      # 初始化连接
│   ├── write_water_quality()                # 写入水质时序数据
│   ├── query_water_quality()                # 查询历史数据
│   └── get_latest_water_quality()           # 获取最新数据
│
├── mqtt_sub.py                              # MQTT订阅模块
│   ├── init_mqtt()                          # 初始化MQTT客户端
│   ├── on_connect()                         # 连接成功回调
│   ├── on_message()                         # 消息接收回调
│   └── start_mqtt_loop()                    # 启动消息循环
│
├── ws_manager.py                            # WebSocket连接管理器
│   ├── connect()                            # 新客户端连接
│   ├── disconnect()                         # 客户端断开
│   ├── broadcast()                          # 广播消息给所有客户端
│   ├── broadcast_water_quality()            # 广播水质数据
│   └── broadcast_garbage_detection()        # 广播垃圾识别通知
│
├── device_manager.py                        # 设备管理模块
│   ├── register_device()                   # 设备注册
│   ├── device_heartbeat()                  # 设备心跳上报
│   ├── get_all_devices()                   # 获取所有设备列表
│   ├── get_device_by_id()                 # 获取单个设备
│   ├── update_device()                     # 更新设备信息
│   ├── delete_device()                     # 删除设备
│   ├── get_device_statistics()             # 设备统计(在线/离线)
│   └── check_all_devices_online()          # 批量检查设备在线状态
│
├── video_proxy.py                           # 视频流代理模块
│   ├── get_all_cameras()                   # 获取所有摄像头
│   ├── get_camera_by_id()                  # 获取单个摄像头
│   ├── add_camera()                        # 添加摄像头
│   ├── update_camera()                     # 更新摄像头
│   ├── delete_camera()                     # 删除摄像头
│   ├── capture_snapshot()                  # 获取视频快照(ffmpeg)
│   ├── check_camera_online()               # 检测摄像头在线状态
│   └── initialize_video_module()           # 初始化视频模块
│
├── stats_op.py                              # 数据统计模块
│   ├── get_water_quality_stats()           # 水质统计(min/max/avg)
│   ├── get_water_quality_trend()           # 水质趋势(按时间聚合)
│   ├── get_water_quality_anomalies()       # 水质异常检测
│   ├── get_dashboard_summary()             # 仪表盘汇总(大屏展示)
│   └── get_water_quality_comparison()      # 水质同比对比
│
├── config/
│   ├── devices.json                        # 设备配置文件
│   └── cameras.json                        # 摄像头配置文件
│
└── api_routes.py                            # API路由模块
    ├── /water/history                       # 查询历史水质数据
    ├── /water/latest                        # 获取最新水质数据
    ├── /water/data                           # 写入水质数据(测试用)
    ├── /garbage/detect                      # 接收垃圾识别结果(YOLO调用)
    ├── /garbage/records                     # 分页查询垃圾记录
    ├── /garbage/stats/today                 # 获取当日统计
    ├── /garbage/cameras                     # 获取摄像头列表
    ├── /garbage/types                       # 获取垃圾类型列表
    ├── /devices/register                    # 设备注册
    ├── /devices/{id}/heartbeat              # 设备心跳
    ├── /devices                              # 设备列表
    ├── /devices/stats                       # 设备统计
    ├── /devices/{id}                        # 设备详情/更新/删除
    ├── /video/cameras                       # 摄像头增删改查
    ├── /video/cameras/{id}/snapshot         # 视频快照
    ├── /video/stream/{id}                   # 视频流WebSocket
    ├── /stats/water/quality                 # 水质统计
    ├── /stats/water/trend                  # 水质趋势
    ├── /stats/water/anomalies              # 水质异常
    ├── /stats/dashboard                    # 仪表盘汇总
    ├── /stats/water/comparison             # 同比对比
    ├── /ws                                  # WebSocket实时推送
    └── /health                              # 健康检查
```

---

## 四、安装部署步骤

### 4.1 安装Python依赖

```bash
cd honshu
pip install -r requirements.txt
```

### 4.2 安装MySQL数据库

#### Windows安装
1. 下载MySQL Installer: https://dev.mysql.com/downloads/installer/
2. 安装时选择"Developer Default"或"Server Only"
3. 设置root密码为 `123456`（或修改.env文件中的密码）

#### 初始化数据库

```bash
mysql -u root -p < database_init.sql
```

### 4.3 安装InfluxDB时序数据库

#### Windows安装
1. 下载InfluxDB: https://portal.influxdata.com/downloads/
2. 双击安装，选择默认路径
3. 启动服务: `services.msc` 找到 InfluxDB 服务并启动

#### 创建Bucket和Token

1. 访问InfluxDB Web UI: http://localhost:8086
2. 登录后创建组织(Org): `mangrove_org`
3. 创建存储桶(Bucket): `water_quality`，保留时间7天
4. 创建Token: 点击左侧"Data" -> "Tokens" -> "Generate Token"
5. 复制Token，替换.env文件中的 `INFLUXDB_TOKEN`

### 4.4 安装MQTT Broker(Mosquitto)

#### Windows安装
1. 下载Mosquitto: https://mosquitto.org/download/
2. 安装完成后启动服务

### 4.5 修改配置文件

编辑 `.env` 文件，根据实际情况修改：

```env
# MySQL配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=123456
MYSQL_DATABASE=mangrove_db

# InfluxDB配置
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_token_here
INFLUXDB_ORG=mangrove_org
INFLUXDB_BUCKET=water_quality

# MQTT配置
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_TOPIC=mangrove/water/+

# API配置
API_HOST=0.0.0.0
API_PORT=8000
```

---

## 五、启动运行

### 5.1 启动后端服务

```bash
cd honshu
python main.py
```

### 5.2 启动成功日志

```
============================================================
  红树林垃圾识别监测系统 - 后端服务启动中...
============================================================

[启动] 初始化MySQL数据库...
[MySQL] 连接成功，表结构已就绪
[启动] 初始化InfluxDB时序数据库...
[InfluxDB] 连接成功
[启动] 初始化MQTT订阅服务...
[MQTT] 客户端初始化完成，准备连接: localhost:1883
[MQTT] 连接成功，返回码: 0
[MQTT] 已订阅主题: mangrove/water/+
[启动] MQTT订阅服务已在后台线程启动

============================================================
  后端服务启动完成！
  API地址: http://0.0.0.0:8000
  文档地址: http://0.0.0.0:8000/docs
  WebSocket: ws://0.0.0.0:8000/api/v1/ws
============================================================
```

### 5.3 访问地址

| 服务 | 地址 |
|------|------|
| API主页 | http://localhost:8000 |
| Swagger文档 | http://localhost:8000/docs |
| WebSocket | ws://localhost:8000/api/v1/ws |

---

## 六、API接口说明

### 6.1 水质数据接口

| 方法 | 路径 | 描述 | 参数 |
|------|------|------|------|
| GET | `/api/v1/water/history` | 查询历史水质数据 | device_id, start_time, end_time |
| GET | `/api/v1/water/latest` | 获取最新水质数据 | device_id(可选) |

**查询历史数据示例:**

```bash
curl "http://localhost:8000/api/v1/water/history?start_time=-24h"
curl "http://localhost:8000/api/v1/water/history?device_id=water_01&start_time=-1h"
```

### 6.2 垃圾识别接口

| 方法 | 路径 | 描述 | 参数 |
|------|------|------|------|
| POST | `/api/v1/garbage/detect` | 接收识别结果(YOLO调用) | camera_id, garbage_type, count, confidence, image_file |
| GET | `/api/v1/garbage/records` | 分页查询记录 | page, page_size, camera_id, garbage_type |
| GET | `/api/v1/garbage/stats/today` | 获取当日统计 | garbage_type(可选) |
| GET | `/api/v1/garbage/cameras` | 获取摄像头列表 | 无 |
| GET | `/api/v1/garbage/types` | 获取垃圾类型列表 | 无 |

**接收垃圾识别结果示例(YOLO算法调用):**

```bash
# 不携带图片
curl -X POST "http://localhost:8000/api/v1/garbage/detect" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "camera_id=camera_01&garbage_type=塑料袋&count=2&confidence=92.5"

# 携带图片
curl -X POST "http://localhost:8000/api/v1/garbage/detect" \
  -F "camera_id=camera_01" \
  -F "garbage_type=塑料瓶" \
  -F "count=1" \
  -F "confidence=88.3" \
  -F "image_file=@test.jpg"
```

### 6.3 设备管理接口

设备数据存储在 `config/devices.json` 文件中，支持设备注册、心跳检测、在线状态管理。

**设计思路：** 设备数量少，直接用 JSON 文件存配置，增删改查本质就是"读文件→改字典→写回去"。心跳检测在内存中记录每个设备最后上报时间，超过60秒未上报标记为离线。

| 方法 | 路径 | 描述 | 参数 |
|------|------|------|------|
| POST | `/api/v1/devices/register` | 设备注册 | device_id(必填), name, device_type, model, location, mqtt_topic |
| POST | `/api/v1/devices/{device_id}/heartbeat` | 设备心跳上报 | device_id, status, ph, tds, turbidity, dissolved_oxygen |
| GET | `/api/v1/devices` | 获取设备列表 | include_status, device_type(过滤) |
| GET | `/api/v1/devices/stats` | 设备统计(总数/在线/离线) | 无 |
| GET | `/api/v1/devices/{device_id}` | 获取单个设备详情 | device_id |
| PUT | `/api/v1/devices/{device_id}` | 更新设备信息 | device_id, name, location, model, mqtt_topic |
| DELETE | `/api/v1/devices/{device_id}` | 删除设备 | device_id |

**设备注册示例:**

```bash
curl -X POST "http://localhost:8000/api/v1/devices/register?device_id=esp32_01&name=水质传感器1号&device_type=water_sensor&location=红树林A区"
```

**设备心跳上报示例:**

```bash
curl -X POST "http://localhost:8000/api/v1/devices/esp32_01/heartbeat?status=online&ph=7.2&tds=320&turbidity=15&dissolved_oxygen=6.8"
```

**设备统计返回示例:**

```json
{
    "code": 200,
    "data": {
        "total": 3,
        "online": 2,
        "offline": 1,
        "by_type": {"water_sensor": 2, "camera": 1}
    }
}
```

### 6.4 视频流代理接口

摄像头配置存储在 `config/cameras.json` 文件中，视频快照通过调用 **ffmpeg** 命令行工具从 RTSP 流截取一帧图片。视频流代理通过 WebSocket 向前端推送实时帧。

**设计思路：** 摄像头增删改查用 JSON 文件存储（同设备管理）。快照功能调用 `ffmpeg -rtsp_transport tcp -i {rtsp_url} -frames:v 1 {output.jpg}` 命令截取一帧。视频流 WebSocket 目前是模拟推送，后续可改为从 ffmpeg 管道读取真实帧数据。

| 方法 | 路径 | 描述 | 参数 |
|------|------|------|------|
| GET | `/api/v1/video/cameras` | 获取所有摄像头列表 | 无 |
| GET | `/api/v1/video/cameras/{camera_id}` | 获取单个摄像头信息 | camera_id |
| POST | `/api/v1/video/cameras` | 添加摄像头 | camera_id, name, rtsp_url, location, camera_type |
| PUT | `/api/v1/video/cameras/{camera_id}` | 更新摄像头配置 | camera_id, name, rtsp_url, location |
| DELETE | `/api/v1/video/cameras/{camera_id}` | 删除摄像头 | camera_id |
| POST | `/api/v1/video/cameras/{camera_id}/snapshot` | 获取视频快照 | camera_id |
| WebSocket | `/api/v1/video/stream/{camera_id}` | 视频流WebSocket代理 | camera_id |

**添加摄像头示例:**

```bash
curl -X POST "http://localhost:8000/api/v1/video/cameras?camera_id=cam_01&name=红树林监控1号&rtsp_url=rtsp://192.168.1.100:554/stream&location=入海口A区"
```

**获取视频快照示例:**

```bash
curl -X POST "http://localhost:8000/api/v1/video/cameras/cam_01/snapshot"
```

> 注意：快照功能需要系统安装 ffmpeg 并配置到 PATH 环境变量中。

### 6.5 数据统计接口

通过 InfluxDB 的类 SQL 语法执行聚合查询（MIN/MAX/AVG/GROUP BY），用 Python 子进程调用 InfluxDB 命令行工具获取 JSON 结果后重新格式化返回。

**设计思路：** InfluxDB 支持标准 SQL，直接写聚合查询语句，通过 `subprocess.run()` 调用 `influxdb3 query` 命令获取 JSON 结果。异常检测是先查出所有数据，再用 Python 循环对比 `config.py` 中定义的阈值范围，超出阈值的记录标记为异常。

| 方法 | 路径 | 描述 | 参数 |
|------|------|------|------|
| GET | `/api/v1/stats/water/quality` | 水质统计(min/max/avg) | device_id, time_range(-1h/-24h/-7d) |
| GET | `/api/v1/stats/water/trend` | 水质趋势(按时间聚合) | device_id, time_range, interval(1h/30m/1d) |
| GET | `/api/v1/stats/water/anomalies` | 水质异常检测 | device_id, time_range |
| GET | `/api/v1/stats/dashboard` | 仪表盘汇总(大屏展示) | 无 |
| GET | `/api/v1/stats/water/comparison` | 同比对比(周/月/年) | device_id, compare_period(week/month/year) |

**水质统计示例:**

```bash
curl "http://localhost:8000/api/v1/stats/water/quality?time_range=-24h"
```

**水质趋势示例:**

```bash
curl "http://localhost:8000/api/v1/stats/water/trend?device_id=water_01&time_range=-24h&interval=1h"
```

**仪表盘汇总示例:**

```bash
curl "http://localhost:8000/api/v1/stats/dashboard"
```

**水质统计返回示例:**

```json
{
    "code": 200,
    "data": [
        {
            "device_id": "water_01",
            "time_range": "-24h",
            "data_count": 1440,
            "ph": {"min": 6.8, "max": 7.5, "avg": 7.15},
            "tds": {"min": 280, "max": 350, "avg": 315},
            "turbidity": {"min": 10, "max": 25, "avg": 15},
            "dissolved_oxygen": {"min": 5.5, "max": 7.2, "avg": 6.4}
        }
    ]
}
```

### 6.6 WebSocket接口

前端通过 WebSocket 连接接收实时数据推送，包括水质数据和垃圾识别通知。

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (data.type === 'water_quality') {
        console.log('水质数据:', data.data);
    } else if (data.type === 'garbage_detection') {
        console.log('垃圾识别:', data.data);
    }
};
```

---

## 七、接口实现说明

### 7.1 整体架构

接口实现采用 **三层分离** 设计：

```
api_routes.py (路由层)     → 接收请求、参数校验、返回统一格式
    ↓ 调用
各业务模块 (逻辑层)          → 处理业务逻辑
    ↓ 读/写
MySQL / InfluxDB / JSON文件 (存储层)  → 数据持久化
```

### 7.2 路由层实现方式

所有接口定义在 `api_routes.py` 中，使用 FastAPI 路由装饰器：

```python
@router.get("/devices")               # 路径
def list_devices(                     # 函数名
    include_status: bool = True,      # 参数直接写在函数签名，框架自动校验
    device_type: str = None
):
    devices = get_all_devices(include_status, device_type)  # 调用业务模块
    return {'code': 200, 'message': '查询成功', 'data': devices}  # 统一返回格式
```

### 7.3 统一返回格式

所有接口返回统一的 JSON 结构：

```json
{
    "code": 200,           // 状态码：200成功，400参数错误，404不存在，500服务器错误
    "message": "操作描述",  // 文字说明
    "data": {}              // 实际数据，可能是对象、列表或null
}
```

### 7.4 各模块存储方式

| 模块 | 存储方式 | 原因 |
|------|----------|------|
| 水质数据 | InfluxDB | 时序数据库适合按时间聚合查询 |
| 垃圾识别记录 | MySQL | 结构化数据，需要分页查询和统计 |
| 设备管理 | JSON文件 | 设备数量少，JSON读写简单，无需建表 |
| 摄像头配置 | JSON文件 | 同上，配置项少 |
| 设备心跳状态 | 内存字典 | 频繁读写，内存速度快，重启后从JSON恢复 |
| 抓拍图片 | 本地文件系统 | 图片文件不适合存数据库 |

### 7.5 心跳检测机制

```
设备上线 → POST /devices/{id}/heartbeat → 更新内存中的最后心跳时间戳
                                              ↓
定时检查(60秒阈值) → 超过60秒未上报 → 标记为 offline
```

心跳时间戳存在内存字典 `_device_status` 中（不写文件），因为心跳频率高，频繁写文件影响性能。重启服务后从 JSON 配置恢复设备信息，状态默认为 unknown，等设备重新上报心跳后恢复 online。

---

## 八、测试示例

### 8.1 模拟MQTT水质数据

```bash
mosquitto_pub -t "mangrove/water/water_01" -m '{
    "timestamp": 1720000000,
    "ph": 7.2,
    "tds": 320,
    "turbidity": 15,
    "dissolved_oxygen": 6.8
}'
```

### 8.2 测试垃圾识别接口

```bash
curl -X POST "http://localhost:8000/api/v1/garbage/detect" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "camera_id=camera_01&garbage_type=塑料袋&count=3&confidence=95.2"
```

---

## 九、数据库表结构

### MySQL表: garbage_detect_record

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 自增主键 |
| camera_id | VARCHAR(50) | 摄像头设备号 |
| detect_time | DATETIME | 识别时间 |
| garbage_type | VARCHAR(50) | 垃圾种类 |
| count | INT | 单次识别垃圾数量 |
| confidence | FLOAT | 平均置信度 |
| image_path | VARCHAR(500) | 抓拍图片路径 |
| created_at | DATETIME | 记录创建时间 |

### InfluxDB Measurement: water_quality

| Tag | 说明 |
|-----|------|
| device_id | 设备ID |

| Field | 类型 | 说明 |
|-------|------|------|
| ph | FLOAT | pH值 |
| tds | FLOAT | TDS值 |
| turbidity | FLOAT | 浊度 |
| dissolved_oxygen | FLOAT | 溶解氧 |

---

## 十、容错处理机制

1. **断连重连**: MySQL和MQTT连接断开后自动尝试重新连接
2. **数据缺失跳过**: MQTT消息缺少必要字段时跳过处理，不崩溃
3. **数值异常过滤**: 水质数据超出合理范围时使用默认值代替
4. **异常捕获**: 所有模块都有try-catch包裹，打印错误但不影响主程序运行

---

## 十一、注意事项

1. 确保MySQL、InfluxDB、Mosquitto服务都已启动
2. 修改.env文件中的数据库密码和InfluxDB Token
3. 首次启动需要等待几秒初始化连接
4. 开发模式下使用`reload=True`，文件修改后自动重启
