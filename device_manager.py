"""
设备管理模块
负责管理水质传感器和摄像头设备

支持功能:
1. 设备注册 - 新设备上线时注册
2. 心跳检测 - 定期检测设备在线状态
3. 设备列表 - 查询所有设备及其状态
4. 设备配置 - 更新设备参数
"""
import os
import json
import time
from datetime import datetime
from typing import Optional

# 设备配置存储
DEVICES_CONFIG_FILE = "./config/devices.json"

# 设备在线状态缓存
_device_status = {}
_OFFLINE_THRESHOLD = 60  # 心跳超时阈值（秒），超过此时间未收到心跳视为离线


def load_devices_config():
    """
    加载设备配置文件
    """
    if os.path.exists(DEVICES_CONFIG_FILE):
        try:
            with open(DEVICES_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Device] 加载设备配置失败: {e}")
    
    return {"devices": []}


def save_devices_config(config):
    """
    保存设备配置文件
    """
    os.makedirs(os.path.dirname(DEVICES_CONFIG_FILE), exist_ok=True)
    
    try:
        with open(DEVICES_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[Device] 保存设备配置失败: {e}")
        return False


def register_device(device_data):
    """
    注册新设备
    
    参数:
        device_data: 设备数据字典
            - id: 设备ID（必填）
            - name: 设备名称
            - type: 设备类型（water_sensor, camera）
            - model: 设备型号
            - location: 部署位置
            - mqtt_topic: MQTT主题（传感器设备）
    
    返回:
        成功标志和设备信息
    """
    config = load_devices_config()
    devices = config.get("devices", [])
    device_id = device_data.get("id", "")
    
    # 检查ID是否已存在
    for dev in devices:
        if dev.get("id") == device_id:
            # 已存在，更新注册信息
            dev["last_register"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            dev["register_count"] = dev.get("register_count", 0) + 1
            config["devices"] = devices
            save_devices_config(config)
            _update_device_heartbeat(device_id)
            return True, dev
    
    # 新设备
    new_device = {
        "id": device_id,
        "name": device_data.get("name", device_id),
        "type": device_data.get("type", "water_sensor"),
        "model": device_data.get("model", "ESP32"),
        "location": device_data.get("location", ""),
        "mqtt_topic": device_data.get("mqtt_topic", f"mangrove/water/{device_id}"),
        "last_register": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "register_count": 1,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    devices.append(new_device)
    config["devices"] = devices
    
    success = save_devices_config(config)
    if success:
        _update_device_heartbeat(device_id)
        print(f"[Device] 新设备注册成功: {device_id}")
    
    return success, new_device if success else "保存失败"


def device_heartbeat(device_id, status="online", extra_data=None):
    """
    设备心跳上报
    
    参数:
        device_id: 设备ID
        status: 状态（online, offline, error）
        extra_data: 附加数据（如传感器读数）
    
    返回:
        (success, result) 元组
    """
    _update_device_heartbeat(device_id, status, extra_data)
    
    # 检查设备是否已注册
    config = load_devices_config()
    devices = config.get("devices", [])
    
    for dev in devices:
        if dev.get("id") == device_id:
            # 更新最后心跳时间
            dev["last_heartbeat"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            dev["status"] = status
            config["devices"] = devices
            save_devices_config(config)
            return True, dev
    
    # 未注册的设备，自动注册
    return register_device({"id": device_id, "name": device_id, "type": "unknown"})


def _update_device_heartbeat(device_id, status="online", extra_data=None):
    """
    更新设备心跳状态（内存缓存）
    """
    _device_status[device_id] = {
        "status": status,
        "last_heartbeat": time.time(),
        "last_heartbeat_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "extra_data": extra_data
    }


def get_device_status(device_id):
    """
    获取单个设备的状态
    """
    if device_id in _device_status:
        status = _device_status[device_id].copy()
        # 检查是否超时
        elapsed = time.time() - status["last_heartbeat"]
        if elapsed > _OFFLINE_THRESHOLD:
            status["status"] = "offline"
            status["offline_duration"] = elapsed
        return status
    
    return {
        "status": "unknown",
        "last_heartbeat": None
    }


def get_all_devices(include_status=True, filter_type=None):
    """
    获取所有设备列表
    
    参数:
        include_status: 是否包含实时状态
        filter_type: 过滤类型（water_sensor, camera, None表示全部）
    
    返回:
        设备列表
    """
    config = load_devices_config()
    devices = config.get("devices", [])
    
    # 按类型过滤
    if filter_type:
        devices = [d for d in devices if d.get("type") == filter_type]
    
    # 添加实时状态
    if include_status:
        for dev in devices:
            dev_id = dev.get("id", "")
            dev["online_status"] = get_device_status(dev_id)
    
    return devices


def get_device_by_id(device_id):
    """
    根据ID获取单个设备
    """
    config = load_devices_config()
    devices = config.get("devices", [])
    
    for dev in devices:
        if dev.get("id") == device_id:
            dev["online_status"] = get_device_status(device_id)
            return dev
    
    return None


def update_device(device_id, device_data):
    """
    更新设备信息
    """
    config = load_devices_config()
    devices = config.get("devices", [])
    
    for i, dev in enumerate(devices):
        if dev.get("id") == device_id:
            # 允许更新的字段
            updatable_fields = ["name", "location", "model", "mqtt_topic"]
            for field in updatable_fields:
                if field in device_data:
                    devices[i][field] = device_data[field]
            
            config["devices"] = devices
            success = save_devices_config(config)
            return success, devices[i] if success else "保存失败"
    
    return False, "设备不存在"


def delete_device(device_id):
    """
    删除设备
    """
    config = load_devices_config()
    devices = config.get("devices", [])
    
    for i, dev in enumerate(devices):
        if dev.get("id") == device_id:
            devices.pop(i)
            config["devices"] = devices
            save_devices_config(config)
            
            # 清除内存状态
            if device_id in _device_status:
                del _device_status[device_id]
            
            return True
    
    return False


def get_device_statistics():
    """
    获取设备统计信息
    """
    config = load_devices_config()
    devices = config.get("devices", [])
    
    total = len(devices)
    online_count = 0
    offline_count = 0
    type_count = {}
    
    for dev in devices:
        dev_type = dev.get("type", "unknown")
        type_count[dev_type] = type_count.get(dev_type, 0) + 1
        
        dev_status = get_device_status(dev.get("id", ""))
        if dev_status["status"] == "online":
            online_count += 1
        elif dev_status["status"] == "offline":
            offline_count += 1
    
    return {
        "total": total,
        "online": online_count,
        "offline": offline_count,
        "offline_unknown": total - online_count - offline_count,
        "by_type": type_count
    }


def check_all_devices_online():
    """
    检查所有设备是否在线
    应该定时调用（如每分钟一次），将超时设备标记为离线
    """
    now = time.time()
    offline_devices = []
    
    for device_id, status in _device_status.items():
        elapsed = now - status["last_heartbeat"]
        if elapsed > _OFFLINE_THRESHOLD and status["status"] == "online":
            _device_status[device_id]["status"] = "offline"
            offline_devices.append(device_id)
            print(f"[Device] 设备离线: {device_id}")
    
    return offline_devices


def initialize_device_manager():
    """
    初始化设备管理器
    """
    print("[Device] 设备管理器初始化完成")
    
    config = load_devices_config()
    device_count = len(config.get("devices", []))
    print(f"[Device] 已注册设备数量: {device_count}")
    print(f"[Device] 心跳超时阈值: {_OFFLINE_THRESHOLD}秒")
