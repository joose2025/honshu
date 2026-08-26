"""
API路由模块
定义所有HTTP接口，供前端Vue页面和YOLO算法调用

接口分类:
1. 水质数据接口 - 查询历史时序数据
2. 垃圾识别接口 - 接收识别结果、查询记录、统计数据
3. 视频流接口 - 摄像头管理、视频流代理
4. 设备管理接口 - 设备注册、心跳、列表
5. 数据统计接口 - 水质统计、综合报表
6. WebSocket接口 - 实时数据推送
7. 健康检查接口 - 服务状态检测
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from datetime import datetime
from typing import Optional
import os
import shutil
import asyncio

# 导入自定义模块
from influxdb_op import query_water_quality, get_latest_water_quality, write_water_quality
from mysql_op import (
    save_garbage_record,
    query_garbage_records,
    get_today_stats,
    get_camera_list,
    get_garbage_types
)
from ws_manager import ws_manager
from config import IMAGE_STORE_PATH
from video_proxy import (
    get_all_cameras as get_video_cameras,
    get_camera_by_id as get_video_camera,
    add_camera,
    update_camera as update_video_camera,
    delete_camera as delete_video_camera,
    capture_snapshot
)
from device_manager import (
    register_device,
    device_heartbeat,
    get_all_devices,
    get_device_by_id,
    update_device,
    delete_device as delete_device_record,
    get_device_statistics
)
from stats_op import (
    get_water_quality_stats,
    get_water_quality_trend,
    get_water_quality_anomalies,
    get_dashboard_summary,
    get_water_quality_comparison
)

# 创建API路由实例
router = APIRouter()


# ==================== 水质数据接口 ====================

@router.get("/water/history", summary="查询历史水质时序数据")
def query_water_history(
    device_id: str = Query(None, description='设备ID'),
    start_time: str = Query(None, description='开始时间（如"-24h"或"2024-01-01T00:00:00Z"）'),
    end_time: str = Query(None, description='结束时间')
):
    """
    查询历史水质时序数据，返回原始数组（对齐前端 WaterQuality[]）
    """
    try:
        data = query_water_quality(device_id, start_time, end_time)
        
        if data is None:
            raise HTTPException(status_code=500, detail="查询失败")
        
        return data
        
    except Exception as e:
        print(f"[API] 查询水质历史数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/water/latest", summary="获取最新水质数据")
def get_latest_water(
    device_id: str = Query(None, description='设备ID')
):
    """
    获取最新的水质数据，返回数组格式（对齐前端 WaterQuality[]）
    """
    try:
        data = get_latest_water_quality(device_id)
        
        if data is None:
            return []
        return [data] if not isinstance(data, list) else data
        
    except Exception as e:
        print(f"[API] 获取最新水质数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/water/data", summary="写入水质数据（模拟MQTT）")
async def write_water_data(
    device_id: str,
    ph: float,
    tds: float,
    turbidity: float,
    dissolved_oxygen: float,
    timestamp: Optional[int] = None
):
    """
    写入水质数据（供测试或API调用，替代MQTT方式）
    """
    try:
        data = {
            'device_id': device_id,
            'timestamp': timestamp or int(datetime.now().timestamp()),
            'ph': ph,
            'tds': tds,
            'turbidity': turbidity,
            'dissolved_oxygen': dissolved_oxygen
        }
        
        # 写入InfluxDB
        success = write_water_quality(data)
        
        if not success:
            raise HTTPException(status_code=500, detail="数据写入失败")
        
        # WebSocket推送
        await ws_manager.broadcast_water_quality(data)
        
        return {
            'code': 200,
            'message': '数据写入成功',
            'data': data
        }
        
    except Exception as e:
        print(f"[API] 写入水质数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 垃圾识别接口 ====================

@router.post("/garbage/detect", summary="接收垃圾识别结果（YOLO算法调用）")
async def receive_garbage_detection(
    camera_id: str,
    garbage_type: str,
    count: int = 1,
    confidence: float = 0.0,
    detect_time: Optional[str] = None,
    image_file: Optional[UploadFile] = File(None)
):
    """
    接收边缘端YOLOv8算法上传的垃圾识别结果
    """
    try:
        # 处理图片存储
        image_path = ""
        if image_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{image_file.filename}"
            image_path = os.path.join(IMAGE_STORE_PATH, filename)
            
            with open(image_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            
            print(f"[API] 图片已保存: {image_path}")
        
        # 准备数据
        data = {
            'camera_id': camera_id,
            'detect_time': detect_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'garbage_type': garbage_type,
            'count': count,
            'confidence': confidence,
            'image_path': image_path
        }
        
        # 保存到MySQL数据库
        success, record_id = save_garbage_record(data)
        
        if not success:
            raise HTTPException(status_code=500, detail="保存失败")
        
        # WebSocket推送
        await ws_manager.broadcast_garbage_detection(data)
        
        return {
            'code': 200,
            'message': '识别结果已保存',
            'record_id': record_id,
            'data': data
        }
        
    except Exception as e:
        print(f"[API] 接收垃圾识别结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/garbage/records", summary="分页查询垃圾识别记录")
def get_garbage_records(
    page: int = Query(1, ge=1, description='页码'),
    page_size: int = Query(20, ge=1, le=100, description='每页数量'),
    camera_id: str = Query(None, description='摄像头编号筛选'),
    garbage_type: str = Query(None, description='垃圾类型筛选')
):
    """
    分页查询所有垃圾识别记录
    """
    try:
        result = query_garbage_records(page, page_size, camera_id, garbage_type)
        
        return {
            'code': 200,
            'message': '查询成功',
            'data': result
        }
        
    except Exception as e:
        print(f"[API] 查询垃圾识别记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/garbage/stats/today", summary="获取当日垃圾识别统计")
def get_today_garbage_stats(
    garbage_type: str = Query(None, description='垃圾类型筛选')
):
    """
    获取当日各垃圾类型的识别总数统计
    返回结构（对齐前端 GarbageTodayStats）:
    { date, total, by_type, by_camera }
    """
    try:
        stats_list = get_today_stats(garbage_type)
        
        # 转换为前端期望的 GarbageTodayStats 结构
        today = datetime.now().strftime("%Y-%m-%d")
        total = sum(item.get("total_count", 0) for item in stats_list)
        by_type = {item["garbage_type"]: item.get("total_count", 0) for item in stats_list}
        
        # 按摄像头统计
        from mysql_op import get_connection
        conn = get_connection()
        by_camera = {}
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT camera_id, SUM(count) as total
                    FROM garbage_detect_record
                    WHERE DATE(detect_time) = CURDATE()
                    GROUP BY camera_id
                """)
                for row in cursor.fetchall():
                    by_camera[row["camera_id"]] = row["total"]
                cursor.close()
            except Exception:
                pass
        
        return {
            "date": today,
            "total": total,
            "by_type": by_type,
            "by_camera": by_camera
        }
        
    except Exception as e:
        print(f"[API] 获取垃圾统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/garbage/cameras", summary="获取所有摄像头列表")
def get_all_cameras():
    """
    获取所有摄像头编号列表（去重）
    """
    try:
        cameras = get_camera_list()
        
        return {
            'code': 200,
            'message': '查询成功',
            'data': cameras
        }
        
    except Exception as e:
        print(f"[API] 获取摄像头列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/garbage/types", summary="获取所有垃圾类型列表")
def get_all_garbage_types():
    """
    获取所有垃圾类型列表（去重）
    """
    try:
        types = get_garbage_types()
        
        return {
            'code': 200,
            'message': '查询成功',
            'data': types
        }
        
    except Exception as e:
        print(f"[API] 获取垃圾类型列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WebSocket接口 ====================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket连接端点
    前端通过此接口建立WebSocket连接，接收实时数据推送
    """
    await ws_manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            print(f"[WebSocket] 收到客户端消息: {data}")
            
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        print("[WebSocket] 客户端断开连接")
    
    except Exception as e:
        print(f"[WebSocket] 异常: {e}")
        ws_manager.disconnect(websocket)


# ==================== 健康检查接口 ====================

# ==================== 视频流接口 ====================

@router.get("/video/cameras", summary="获取所有摄像头列表")
def list_cameras():
    """
    获取所有已配置的摄像头列表
    """
    try:
        cameras = get_video_cameras()
        return {
            'code': 200,
            'message': '查询成功',
            'data': cameras
        }
    except Exception as e:
        print(f"[API] 获取摄像头列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video/cameras/{camera_id}", summary="获取单个摄像头信息")
def get_camera(camera_id: str):
    """
    获取单个摄像头的详细信息
    """
    try:
        camera = get_video_camera(camera_id)
        if not camera:
            raise HTTPException(status_code=404, detail="摄像头不存在")
        return {
            'code': 200,
            'message': '查询成功',
            'data': camera
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 获取摄像头信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video/cameras", summary="添加新摄像头")
def create_camera(camera_id: str, name: str, rtsp_url: str, location: str = "", camera_type: str = "water_quality"):
    """
    添加新的摄像头设备
    """
    try:
        camera_data = {
            "id": camera_id,
            "name": name,
            "rtsp_url": rtsp_url,
            "location": location,
            "type": camera_type
        }
        success, result = add_camera(camera_data)
        if not success:
            raise HTTPException(status_code=400, detail=result)
        return {
            'code': 200,
            'message': '添加成功',
            'data': result
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 添加摄像头失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/video/cameras/{camera_id}", summary="更新摄像头信息")
def modify_camera(camera_id: str, name: Optional[str] = None, rtsp_url: Optional[str] = None, location: Optional[str] = None):
    """
    更新摄像头配置
    """
    try:
        camera_data = {}
        if name:
            camera_data["name"] = name
        if rtsp_url:
            camera_data["rtsp_url"] = rtsp_url
        if location:
            camera_data["location"] = location
        
        success, result = update_video_camera(camera_id, camera_data)
        if not success:
            raise HTTPException(status_code=404, detail=result)
        return {
            'code': 200,
            'message': '更新成功',
            'data': result
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 更新摄像头失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/video/cameras/{camera_id}", summary="删除摄像头")
def remove_camera(camera_id: str):
    """
    删除指定摄像头
    """
    try:
        success = delete_video_camera(camera_id)
        if not success:
            raise HTTPException(status_code=404, detail="摄像头不存在")
        return {
            'code': 200,
            'message': '删除成功'
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 删除摄像头失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video/cameras/{camera_id}/snapshot", summary="获取摄像头快照")
async def camera_snapshot(camera_id: str):
    """
    获取摄像头当前画面的快照
    """
    try:
        snapshot_path, error = capture_snapshot(camera_id)
        if error:
            raise HTTPException(status_code=400, detail=error)
        
        return {
            'code': 200,
            'message': '快照获取成功',
            'data': {
                'camera_id': camera_id,
                'snapshot_path': snapshot_path,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 获取快照失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/video/stream/{camera_id}")
async def video_stream_ws(websocket: WebSocket, camera_id: str):
    """
    视频流WebSocket代理
    前端通过此接口接收实时视频帧
    """
    await websocket.accept()
    print(f"[Video] 视频流WebSocket连接: {camera_id}")
    
    try:
        while True:
            # 模拟视频帧推送（实际使用时从ffmpeg获取帧数据）
            frame_data = f'{{"camera_id": "{camera_id}", "timestamp": "{datetime.now().isoformat()}", "status": "streaming"}}'
            await websocket.send_text(frame_data)
            await asyncio.sleep(0.1)  # 100ms间隔
    except WebSocketDisconnect:
        print(f"[Video] 视频流WebSocket断开: {camera_id}")
    except Exception as e:
        print(f"[Video] 视频流异常: {e}")


# ==================== 设备管理接口 ====================

@router.post("/devices/register", summary="设备注册")
def register_new_device(
    device_id: str,
    name: Optional[str] = None,
    device_type: str = "water_sensor",
    model: str = "ESP32",
    location: str = "",
    mqtt_topic: Optional[str] = None
):
    """
    新设备上线时调用此接口进行注册
    """
    try:
        device_data = {
            "id": device_id,
            "name": name or device_id,
            "type": device_type,
            "model": model,
            "location": location,
            "mqtt_topic": mqtt_topic
        }
        success, result = register_device(device_data)
        if not success:
            raise HTTPException(status_code=400, detail=result)
        return {
            'code': 200,
            'message': '设备注册成功',
            'data': result
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 设备注册失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/devices/{device_id}/heartbeat", summary="设备心跳")
def send_device_heartbeat(
    device_id: str,
    status: str = "online",
    ph: Optional[float] = None,
    tds: Optional[float] = None,
    turbidity: Optional[float] = None,
    dissolved_oxygen: Optional[float] = None
):
    """
    设备定期发送心跳，上报在线状态和传感器数据
    """
    try:
        extra_data = {}
        if ph is not None:
            extra_data["ph"] = ph
        if tds is not None:
            extra_data["tds"] = tds
        if turbidity is not None:
            extra_data["turbidity"] = turbidity
        if dissolved_oxygen is not None:
            extra_data["dissolved_oxygen"] = dissolved_oxygen
        
        success, result = device_heartbeat(device_id, status, extra_data)
        if not success:
            raise HTTPException(status_code=400, detail=result)
        return {
            'code': 200,
            'message': '心跳已接收',
            'data': result
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 心跳接收失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices", summary="获取所有设备列表")
def list_devices(
    include_status: bool = Query(True, description="是否包含实时状态"),
    device_type: Optional[str] = Query(None, description="过滤设备类型")
):
    """
    获取所有已注册设备的列表
    """
    try:
        devices = get_all_devices(include_status, device_type)
        return {
            'code': 200,
            'message': '查询成功',
            'data': devices
        }
    except Exception as e:
        print(f"[API] 获取设备列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/stats", summary="获取设备统计信息")
def get_device_stats():
    """
    获取设备统计信息（总数、在线数、离线数等）
    注意：此路由必须在 /devices/{device_id} 之前定义
    """
    try:
        stats = get_device_statistics()
        return {
            'code': 200,
            'message': '查询成功',
            'data': stats
        }
    except Exception as e:
        print(f"[API] 获取设备统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/{device_id}", summary="获取单个设备信息")
def get_device_info(device_id: str):
    """
    获取单个设备的详细信息和实时状态
    """
    try:
        device = get_device_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="设备不存在")
        return {
            'code': 200,
            'message': '查询成功',
            'data': device
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 获取设备信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/devices/{device_id}", summary="更新设备信息")
def modify_device(
    device_id: str,
    name: Optional[str] = None,
    location: Optional[str] = None,
    model: Optional[str] = None,
    mqtt_topic: Optional[str] = None
):
    """
    更新设备配置信息
    """
    try:
        device_data = {}
        if name:
            device_data["name"] = name
        if location:
            device_data["location"] = location
        if model:
            device_data["model"] = model
        if mqtt_topic:
            device_data["mqtt_topic"] = mqtt_topic
        
        success, result = update_device(device_id, device_data)
        if not success:
            raise HTTPException(status_code=404, detail=result)
        return {
            'code': 200,
            'message': '更新成功',
            'data': result
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 更新设备失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/devices/{device_id}", summary="删除设备")
def remove_device(device_id: str):
    """
    删除指定设备
    """
    try:
        success = delete_device_record(device_id)
        if not success:
            raise HTTPException(status_code=404, detail="设备不存在")
        return {
            'code': 200,
            'message': '删除成功'
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] 删除设备失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 数据统计接口 ====================

@router.get("/stats/water/quality", summary="获取水质数据统计")
def water_quality_stats(
    device_id: Optional[str] = Query(None, description="设备ID"),
    time_range: str = Query("-24h", description="时间范围（-1h, -24h, -7d）")
):
    """
    获取水质数据统计（最小值、最大值、平均值）
    """
    try:
        result = get_water_quality_stats(device_id, time_range)
        return result
    except Exception as e:
        print(f"[API] 获取水质统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/water/trend", summary="获取水质数据趋势")
def water_quality_trend(
    device_id: Optional[str] = Query(None, description="设备ID"),
    time_range: str = Query("-24h", description="时间范围"),
    interval: str = Query("1h", description="聚合间隔（1h, 30m, 1d）"),
    indicator: str = Query("ph", description="指标名：ph/tds/turbidity/dissolved_oxygen")
):
    """
    获取水质数据趋势（按时间间隔聚合）
    返回结构（对齐前端 WaterTrendPoint[]）:
    [{ timestamp, value }, ...]
    """
    try:
        result = get_water_quality_trend(device_id, time_range, interval, indicator)
        return result
    except Exception as e:
        print(f"[API] 获取水质趋势失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/water/anomalies", summary="获取水质异常数据")
def water_quality_anomalies(
    device_id: Optional[str] = Query(None, description="设备ID"),
    time_range: str = Query("-24h", description="时间范围")
):
    """
    获取水质异常数据（超出阈值的记录）
    """
    try:
        result = get_water_quality_anomalies(device_id, time_range)
        return result
    except Exception as e:
        print(f"[API] 获取异常数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/dashboard", summary="获取仪表盘汇总数据")
def dashboard_summary():
    """
    获取仪表盘汇总数据，用于前端大屏展示
    """
    try:
        result = get_dashboard_summary()
        return result
    except Exception as e:
        print(f"[API] 获取仪表盘数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/water/comparison", summary="获取水质同比对比数据")
def water_quality_comparison(
    device_id: Optional[str] = Query(None, description="设备ID"),
    compare_period: str = Query("week", description="对比周期（week, month, year）")
):
    """
    获取水质数据同比对比
    """
    try:
        result = get_water_quality_comparison(device_id, compare_period)
        return result
    except Exception as e:
        print(f"[API] 获取对比数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 健康检查接口 ====================

@router.get("/health", summary="健康检查")
def health_check():
    """
    服务健康检查接口
    """
    return {
        'code': 200,
        'status': 'healthy',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
