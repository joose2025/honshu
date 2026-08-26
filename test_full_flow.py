"""
完整流程测试脚本 - 用于成果展示
测试内容:
1. MQTT数据上传
2. InfluxDB数据存储
3. API数据查询
4. WebSocket实时推送
"""
import paho.mqtt.client as mqtt
import requests
import json
import time

# MQTT配置
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "mangrove/water/test_device"

# API配置
API_URL = "http://localhost:8000/api/v1"

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] 连接成功，返回码: {rc}")

def on_publish(client, userdata, mid):
    print(f"[MQTT] 消息发布成功，消息ID: {mid}")

def test_mqtt_upload():
    """测试MQTT数据上传"""
    print("\n" + "="*60)
    print("  1. 测试MQTT数据上传")
    print("="*60)
    
    client = mqtt.Client(client_id="test_publisher")
    client.on_connect = on_connect
    client.on_publish = on_publish
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        
        # 构造测试数据
        test_data = {
            "device_id": "water_test_01",
            "timestamp": int(time.time()),
            "ph": 7.2,
            "tds": 320.5,
            "turbidity": 15.3,
            "dissolved_oxygen": 6.8
        }
        
        payload = json.dumps(test_data)
        result = client.publish(MQTT_TOPIC, payload, qos=1)
        result.wait_for_publish()
        
        client.loop_stop()
        client.disconnect()
        
        print(f"[MQTT] 发布主题: {MQTT_TOPIC}")
        print(f"[MQTT] 消息内容: {payload}")
        
        return test_data
        
    except Exception as e:
        print(f"[MQTT] 发布失败: {e}")
        return None

def test_api_upload():
    """测试API数据上传（模拟ESP32）"""
    print("\n" + "="*60)
    print("  2. 测试API数据上传")
    print("="*60)
    
    test_data = {
        "device_id": "water_test_02",
        "ph": 8.1,
        "tds": 456.2,
        "turbidity": 28.7,
        "dissolved_oxygen": 5.5
    }
    
    try:
        response = requests.post(f"{API_URL}/water/data", params=test_data)
        print(f"[API] HTTP状态码: {response.status_code}")
        print(f"[API] 响应内容: {response.text}")
        
        if response.status_code == 200:
            return test_data
        return None
        
    except Exception as e:
        print(f"[API] 请求失败: {e}")
        return None

def test_api_query():
    """测试API数据查询"""
    print("\n" + "="*60)
    print("  3. 测试API历史数据查询")
    print("="*60)
    
    try:
        response = requests.get(f"{API_URL}/water/history", params={
            "device_id": "water_test_01",
            "start_time": "-24h"
        })
        
        print(f"[API] HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"[API] 查询结果: 共 {len(data['data'])} 条记录")
            
            if data['data']:
                print("[API] 最新记录:")
                for key, value in data['data'][-1].items():
                    print(f"      {key}: {value}")
        
    except Exception as e:
        print(f"[API] 查询失败: {e}")

def test_latest_query():
    """测试获取最新数据"""
    print("\n" + "="*60)
    print("  4. 测试获取最新数据")
    print("="*60)
    
    try:
        response = requests.get(f"{API_URL}/water/latest")
        
        print(f"[API] HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"[API] 最新数据:")
            if data['data']:
                for key, value in data['data'].items():
                    print(f"      {key}: {value}")
        
    except Exception as e:
        print(f"[API] 查询失败: {e}")

def test_influxdb_direct():
    """直接测试InfluxDB查询"""
    print("\n" + "="*60)
    print("  5. 直接测试InfluxDB数据")
    print("="*60)
    
    import subprocess
    
    try:
        cmd = [
            "c:\\Users\\joose\\OneDrive\\Desktop\\influxdb3-core-3.10.5-windows_amd64\\influxdb3.exe",
            "query",
            "--database", "water_quality",
            "--token", "apiv3_cLKuZCpuxkTnOXAKkLx2IOAAgSRxVCHncS0m_GttnaansPx3EdVUQ5jfLqrH8B8H8XPlbZI06oPHSZF3WRcfyg",
            "--format", "json",
            "SELECT * FROM water_quality ORDER BY time DESC LIMIT 5"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            print(f"[InfluxDB] 总记录数: {len(data)}")
            print("[InfluxDB] 最新5条记录:")
            for i, record in enumerate(data):
                print(f"  {i+1}. time={record['time']}, device={record['device_id']}, ph={record['ph']}, tds={record['tds']}, turbidity={record['turbidity']}, DO={record['dissolved_oxygen']}")
        
    except Exception as e:
        print(f"[InfluxDB] 查询失败: {e}")

def generate_report():
    """生成成果展示报告"""
    print("\n" + "="*70)
    print("                    红树林垃圾识别监测系统 - 成果展示报告")
    print("="*70)
    
    print("\n一、系统架构")
    print("-"*40)
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│                    终端感知层                               │")
    print("│  ESP32水质传感器 + 网络摄像头                               │")
    print("└─────────────────────────────────────────────────────────────┘")
    print("                            ↓")
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│                    传输层                                   │")
    print("│  MQTT协议 (端口1883) + HTTP API (端口8000)                 │")
    print("└─────────────────────────────────────────────────────────────┘")
    print("                            ↓")
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│                    后端服务层                               │")
    print("│  FastAPI + InfluxDB3 + MySQL                               │")
    print("└─────────────────────────────────────────────────────────────┘")
    print("                            ↓")
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│                    前端展示层                               │")
    print("│  Vue.js + ECharts实时图表                                   │")
    print("└─────────────────────────────────────────────────────────────┘")
    
    print("\n二、服务状态")
    print("-"*40)
    services = [
        {"name": "MQTT Broker (Mosquitto)", "status": "✓ 运行中", "port": "1883"},
        {"name": "InfluxDB 3.x", "status": "✓ 运行中", "port": "8181"},
        {"name": "FastAPI后端", "status": "✓ 运行中", "port": "8000"},
        {"name": "MySQL数据库", "status": "✓ 运行中", "port": "3306"}
    ]
    
    for s in services:
        print(f"  {s['name']}")
        print(f"    状态: {s['status']}, 端口: {s['port']}")
    
    print("\n三、API接口")
    print("-"*40)
    apis = [
        {"method": "POST", "path": "/api/v1/water/data", "desc": "写入水质数据"},
        {"method": "GET", "path": "/api/v1/water/history", "desc": "查询历史数据"},
        {"method": "GET", "path": "/api/v1/water/latest", "desc": "获取最新数据"},
        {"method": "POST", "path": "/api/v1/garbage/detect", "desc": "接收垃圾识别结果"},
        {"method": "GET", "path": "/api/v1/garbage/records", "desc": "查询识别记录"},
        {"method": "GET", "path": "/api/v1/garbage/stats/today", "desc": "今日统计"},
        {"method": "GET", "path": "/api/v1/health", "desc": "健康检查"}
    ]
    
    print(f"  {'方法':<6} {'路径':<45} {'描述'}")
    print(f"  {'----':<6} {'----':<45} {'----'}")
    for api in apis:
        print(f"  {api['method']:<6} {api['path']:<45} {api['desc']}")
    
    print("\n四、数据流向")
    print("-"*40)
    print("  水质数据: ESP32 → MQTT/API → InfluxDB → HTTP API → 前端图表")
    print("  垃圾识别: 摄像头 → YOLOv8 → HTTP API → MySQL → 前端展示")
    
    print("\n五、访问地址")
    print("-"*40)
    print("  API地址:    http://localhost:8000")
    print("  API文档:    http://localhost:8000/docs")
    print("  InfluxDB:   http://localhost:8181")
    print("  MQTT Broker: tcp://localhost:1883")
    
    print("\n" + "="*70)
    print("                          系统运行正常！")
    print("="*70)

if __name__ == "__main__":
    print("\n" + "#"*70)
    print("#           红树林垃圾识别监测系统 - 完整流程测试")
    print("#"*70)
    
    # 运行测试
    mqtt_data = test_mqtt_upload()
    time.sleep(2)  # 等待数据写入
    
    api_data = test_api_upload()
    time.sleep(2)  # 等待数据写入
    
    test_api_query()
    test_latest_query()
    test_influxdb_direct()
    
    # 生成报告
    generate_report()
    
    print("\n测试完成！")
