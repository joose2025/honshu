"""
MQTT订阅服务模块
负责订阅ESP32单片机上传的水质传感器数据
订阅主题: mangrove/water/+
数据格式: {"device_id": "water_01", "timestamp": 1720000000, "ph": 7.2, "tds": 320, "turbidity": 15, "dissolved_oxygen": 6.8}

数据流程:
ESP32传感器 → MQTT Broker → 本模块接收 → InfluxDB存储 + WebSocket实时推送
"""
import paho.mqtt.client as mqtt
import json
import time
from config import MQTT_CONFIG
from influxdb_op import write_water_quality
from ws_manager import ws_manager

# 全局MQTT客户端实例
_mqtt_client = None


def on_connect(client, userdata, flags, rc):
    """
    MQTT连接成功回调函数
    """
    if rc == 0:
        print(f"[MQTT] 连接成功，返回码: {rc}")
        client.subscribe(MQTT_CONFIG['topic'], qos=1)
        print(f"[MQTT] 已订阅主题: {MQTT_CONFIG['topic']}")
    else:
        print(f"[MQTT] 连接失败，返回码: {rc}")


def on_disconnect(client, userdata, rc):
    """
    MQTT断开连接回调函数
    """
    print(f"[MQTT] 断开连接，返回码: {rc}")
    
    if rc != 0:
        print("[MQTT] 异常断开，5秒后尝试重新连接...")
        time.sleep(5)
        try:
            client.reconnect()
        except Exception as e:
            print(f"[MQTT] 重新连接失败: {e}")


def on_message(client, userdata, msg):
    """
    MQTT消息接收回调函数
    """
    try:
        topic = msg.topic
        print(f"\n[MQTT] 收到消息 - 主题: {topic}")
        
        payload = json.loads(msg.payload.decode('utf-8'))
        print(f"[MQTT] 消息内容: {payload}")
        
        # 从主题中提取设备ID
        parts = topic.split('/')
        if len(parts) >= 3:
            device_id = parts[2]
            payload['device_id'] = device_id
        
        # 数据校验
        required_fields = ['ph', 'tds', 'turbidity', 'dissolved_oxygen']
        missing_fields = [f for f in required_fields if f not in payload]
        
        if missing_fields:
            print(f"[MQTT] 数据字段缺失，跳过: {missing_fields}")
            return
        
        # 写入InfluxDB
        write_success = write_water_quality(payload)
        
        if write_success:
            # WebSocket推送
            import asyncio
            asyncio.run(ws_manager.broadcast_water_quality(payload))
        else:
            print("[MQTT] 数据写入InfluxDB失败")
        
    except json.JSONDecodeError as e:
        print(f"[MQTT] JSON解析失败: {e}")
    except Exception as e:
        print(f"[MQTT] 消息处理失败: {e}")


def init_mqtt():
    """
    初始化MQTT客户端
    """
    global _mqtt_client
    
    try:
        _mqtt_client = mqtt.Client(
            client_id=MQTT_CONFIG['client_id'],
            clean_session=True
        )
        
        _mqtt_client.on_connect = on_connect
        _mqtt_client.on_disconnect = on_disconnect
        _mqtt_client.on_message = on_message
        
        _mqtt_client.keepalive = 60
        
        print(f"[MQTT] 客户端初始化完成，准备连接: {MQTT_CONFIG['broker']}:{MQTT_CONFIG['port']}")
        return True
        
    except Exception as e:
        print(f"[MQTT] 客户端初始化失败: {e}")
        return False


def connect_mqtt():
    """
    连接MQTT Broker
    """
    global _mqtt_client
    
    if not _mqtt_client:
        print("[MQTT] 客户端未初始化")
        return False
    
    try:
        _mqtt_client.connect(
            host=MQTT_CONFIG['broker'],
            port=MQTT_CONFIG['port'],
            keepalive=60
        )
        
        return True
        
    except Exception as e:
        print(f"[MQTT] 连接失败: {e}")
        return False


def start_mqtt_loop():
    """
    启动MQTT消息循环（阻塞式）
    """
    global _mqtt_client
    
    if not _mqtt_client:
        print("[MQTT] 客户端未初始化")
        return
    
    try:
        print("[MQTT] 启动消息循环...")
        _mqtt_client.loop_forever()
        
    except KeyboardInterrupt:
        print("[MQTT] 用户中断，停止消息循环")
    except Exception as e:
        print(f"[MQTT] 消息循环异常: {e}")


def stop_mqtt():
    """
    停止MQTT客户端
    """
    global _mqtt_client
    
    if _mqtt_client:
        _mqtt_client.disconnect()
        print("[MQTT] 客户端已断开连接")
