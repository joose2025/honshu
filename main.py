"""
红树林垃圾识别监测系统 - 后端主应用入口

系统五层架构:
1. 终端感知层(ESP32+网络摄像头)
2. 传输层(MQTT+MediaMTX流媒体)
3. 边缘计算层(YOLOv8垃圾识别)
4. 后端存储服务层(本模块)
5. 前端Vue展示层

数据流向:
1. 水质链路: ESP32传感器 → MQTT → InfluxDB + WebSocket前端
2. 垃圾识别链路: 摄像头RTSP流 → YOLO算法HTTP上报 → MySQL + 本地存图 + WebSocket前端

启动方式:
    python main.py

访问地址:
    API: http://localhost:8000
    文档: http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading

# 导入自定义模块
from api_routes import router
from config import API_CONFIG
from mysql_op import init_mysql, close_mysql
from influxdb_op import init_influxdb, close_influxdb
from mqtt_sub import init_mqtt, connect_mqtt, start_mqtt_loop, stop_mqtt

# 创建FastAPI应用实例
app = FastAPI(
    title="红树林垃圾识别监测系统",
    description="红树林垃圾识别监测系统后端API - 数据存储模块",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(router, prefix="/api/v1")


# ==================== 启动时初始化 ====================

@app.on_event("startup")
async def startup_event():
    """
    应用启动时执行的初始化操作
    按顺序初始化: MySQL → InfluxDB → MQTT
    """
    print("\n" + "="*60)
    print("  红树林垃圾识别监测系统 - 后端服务启动中...")
    print("="*60 + "\n")
    
    # 1. 初始化MySQL数据库
    print("[启动] 初始化MySQL数据库...")
    mysql_ok = init_mysql()
    
    # 2. 初始化InfluxDB时序数据库
    print("[启动] 初始化InfluxDB时序数据库...")
    influxdb_ok = init_influxdb()
    
    # 3. 初始化MQTT客户端（在后台线程中运行）
    print("[启动] 初始化MQTT订阅服务...")
    if init_mqtt() and connect_mqtt():
        mqtt_thread = threading.Thread(
            target=start_mqtt_loop,
            daemon=True,
            name="MQTT-Loop"
        )
        mqtt_thread.start()
        print("[启动] MQTT订阅服务已在后台线程启动")
    else:
        print("[启动] MQTT订阅服务初始化失败，请检查配置")
    
    # 打印启动完成信息
    print("\n" + "="*60)
    print("  后端服务启动完成！")
    print(f"  API地址: http://{API_CONFIG['host']}:{API_CONFIG['port']}")
    print(f"  文档地址: http://{API_CONFIG['host']}:{API_CONFIG['port']}/docs")
    print(f"  WebSocket: ws://{API_CONFIG['host']}:{API_CONFIG['port']}/api/v1/ws")
    print("="*60 + "\n")


# ==================== 关闭时清理 ====================

@app.on_event("shutdown")
async def shutdown_event():
    """
    应用关闭时执行的清理操作
    """
    print("\n" + "="*60)
    print("  后端服务正在关闭...")
    print("="*60 + "\n")
    
    stop_mqtt()
    close_influxdb()
    close_mysql()
    
    print("\n" + "="*60)
    print("  后端服务已关闭！")
    print("="*60 + "\n")


# ==================== 根路径 ====================

@app.get("/")
def root():
    """
    根路径接口
    """
    return {
        'message': '红树林垃圾识别监测系统后端API',
        'version': '1.0.0',
        'docs': f'http://{API_CONFIG["host"]}:{API_CONFIG["port"]}/docs',
        'api_prefix': '/api/v1'
    }


# ==================== 主函数 ====================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=API_CONFIG['host'],
        port=API_CONFIG['port'],
        reload=True
    )

