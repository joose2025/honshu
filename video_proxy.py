"""
视频流代理模块
负责处理摄像头RTSP流的接入和代理转发

支持功能:
1. 视频流代理 - 将RTSP流转换为HTTP可访问的格式
2. 视频快照 - 获取当前视频帧作为截图
3. 多摄像头管理 - 支持多个摄像头同时接入
"""
import os
import json
import subprocess
import threading
import time
from datetime import datetime
from typing import Optional

# 摄像头配置存储
CAMERAS_CONFIG_FILE = "./config/cameras.json"

# 内存中的摄像头状态
_camera_status = {}
_stream_threads = {}


def load_cameras_config():
    """
    加载摄像头配置文件
    """
    if os.path.exists(CAMERAS_CONFIG_FILE):
        try:
            with open(CAMERAS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Video] 加载摄像头配置失败: {e}")
    
    # 默认返回空配置
    return {"cameras": []}


def save_cameras_config(config):
    """
    保存摄像头配置文件
    """
    os.makedirs(os.path.dirname(CAMERAS_CONFIG_FILE), exist_ok=True)
    
    try:
        with open(CAMERAS_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"[Video] 摄像头配置已保存")
        return True
    except Exception as e:
        print(f"[Video] 保存摄像头配置失败: {e}")
        return False


def get_all_cameras():
    """
    获取所有摄像头列表
    """
    config = load_cameras_config()
    
    # 为每个摄像头添加实时状态
    cameras = config.get("cameras", [])
    for cam in cameras:
        cam_id = cam.get("id", "")
        if cam_id in _camera_status:
            cam["status"] = _camera_status[cam_id]
        else:
            cam["status"] = {
                "online": False,
                "last_heartbeat": None
            }
    
    return cameras


def get_camera_by_id(camera_id):
    """
    根据ID获取单个摄像头信息
    """
    config = load_cameras_config()
    cameras = config.get("cameras", [])
    
    for cam in cameras:
        if cam.get("id") == camera_id:
            if camera_id in _camera_status:
                cam["status"] = _camera_status[camera_id]
            else:
                cam["status"] = {
                    "online": False,
                    "last_heartbeat": None
                }
            return cam
    
    return None


def add_camera(camera_data):
    """
    添加新摄像头
    """
    config = load_cameras_config()
    cameras = config.get("cameras", [])
    
    # 检查ID是否已存在
    camera_id = camera_data.get("id", "")
    for cam in cameras:
        if cam.get("id") == camera_id:
            return False, "摄像头ID已存在"
    
    # 添加新摄像头
    new_camera = {
        "id": camera_id,
        "name": camera_data.get("name", camera_id),
        "rtsp_url": camera_data.get("rtsp_url", ""),
        "location": camera_data.get("location", ""),
        "type": camera_data.get("type", "water_quality"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    cameras.append(new_camera)
    config["cameras"] = cameras
    
    success = save_cameras_config(config)
    return success, new_camera if success else "保存失败"


def update_camera(camera_id, camera_data):
    """
    更新摄像头信息
    """
    config = load_cameras_config()
    cameras = config.get("cameras", [])
    
    for i, cam in enumerate(cameras):
        if cam.get("id") == camera_id:
            # 更新字段
            for key in ["name", "rtsp_url", "location", "type"]:
                if key in camera_data:
                    cameras[i][key] = camera_data[key]
            
            config["cameras"] = cameras
            success = save_cameras_config(config)
            return success, cameras[i] if success else "保存失败"
    
    return False, "摄像头不存在"


def delete_camera(camera_id):
    """
    删除摄像头
    """
    config = load_cameras_config()
    cameras = config.get("cameras", [])
    
    for i, cam in enumerate(cameras):
        if cam.get("id") == camera_id:
            cameras.pop(i)
            config["cameras"] = cameras
            success = save_cameras_config(config)
            return success
    
    return False


def update_camera_status(camera_id, online=True):
    """
    更新摄像头状态
    """
    _camera_status[camera_id] = {
        "online": online,
        "last_heartbeat": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def get_video_stream_url(camera_id, format="hls"):
    """
    获取视频流访问URL
    
    参数:
        camera_id: 摄像头ID
        format: 输出格式 (hls, webrtc, mjpeg)
    
    返回:
        视频流访问URL
    """
    return f"/api/v1/video/stream/{camera_id}?format={format}"


def capture_snapshot(camera_id, rtsp_url=None):
    """
    获取摄像头当前画面快照
    
    使用ffmpeg从RTSP流截取一帧保存为图片
    
    参数:
        camera_id: 摄像头ID
        rtsp_url: RTSP地址（可选，如果不传则从配置读取）
    
    返回:
        截图文件路径
    """
    try:
        # 获取RTSP地址
        if not rtsp_url:
            cam = get_camera_by_id(camera_id)
            if cam:
                rtsp_url = cam.get("rtsp_url", "")
        
        if not rtsp_url:
            return None, "未配置RTSP地址"
        
        # 创建截图保存目录
        snapshot_dir = "./uploads/snapshots"
        os.makedirs(snapshot_dir, exist_ok=True)
        
        # 生成截图文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = os.path.join(snapshot_dir, f"{camera_id}_{timestamp}.jpg")
        
        # 使用ffmpeg获取一帧
        cmd = [
            "ffmpeg",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-frames:v", "1",
            "-q:v", "2",
            "-y",
            snapshot_path
        ]
        
        # 设置超时
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and os.path.exists(snapshot_path):
                return snapshot_path, None
            else:
                return None, f"截图失败: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return None, "截图超时"
            
    except FileNotFoundError:
        return None, "ffmpeg未安装或不在PATH中"
    except Exception as e:
        return None, f"截图异常: {e}"


def check_camera_online(rtsp_url, timeout=5):
    """
    检测摄像头是否在线
    
    参数:
        rtsp_url: RTSP地址
        timeout: 超时时间（秒）
    
    返回:
        是否在线
    """
    try:
        cmd = [
            "ffmpeg",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-t", "1",
            "-f", "null",
            "-"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout
        )
        
        return result.returncode == 0
        
    except:
        return False


def initialize_video_module():
    """
    初始化视频模块
    """
    print("[Video] 视频模块初始化完成")
    
    # 检查ffmpeg是否可用
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=3)
        print("[Video] ffmpeg可用")
    except:
        print("[Video] 警告: ffmpeg未安装，视频功能将受限")
    
    # 检查摄像头配置
    config = load_cameras_config()
    camera_count = len(config.get("cameras", []))
    print(f"[Video] 已配置摄像头数量: {camera_count}")
