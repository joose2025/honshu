"""
MQTT数据测试脚本
模拟ESP32传感器发送水质数据到后端
可以直接调用后端API写入数据，无需MQTT Broker
"""
import requests
import json
import time
import random

# 后端API地址
API_BASE = "http://localhost:8000/api/v1"

# 模拟设备ID
DEVICE_IDS = ["water_01", "water_02", "water_03"]

# 水质数据范围
PH_RANGE = (6.5, 8.5)
TDS_RANGE = (200, 500)
TURBIDITY_RANGE = (5, 50)
DO_RANGE = (5.0, 8.5)


def send_water_quality(device_id):
    """发送模拟水质数据（使用查询参数）"""
    ph = round(random.uniform(*PH_RANGE), 1)
    tds = round(random.uniform(*TDS_RANGE), 0)
    turbidity = round(random.uniform(*TURBIDITY_RANGE), 1)
    dissolved_oxygen = round(random.uniform(*DO_RANGE), 1)
    
    data = {
        "device_id": device_id,
        "timestamp": int(time.time()),
        "ph": ph,
        "tds": tds,
        "turbidity": turbidity,
        "dissolved_oxygen": dissolved_oxygen
    }
    
    print(f"\n发送数据: {json.dumps(data, indent=2)}")
    
    try:
        # 使用查询参数发送
        response = requests.post(f"{API_BASE}/water/data", params=data)
        
        if response.status_code == 200:
            print(f"✅ 数据写入成功")
            return True
        else:
            print(f"❌ 数据写入失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return False


def query_latest_data(device_id=None):
    """查询最新数据"""
    url = f"{API_BASE}/water/latest"
    params = {}
    if device_id:
        params['device_id'] = device_id
    
    try:
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n最新数据查询结果:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return result
        else:
            print(f"❌ 查询失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return None


def query_history_data(device_id=None, hours=24):
    """查询历史数据"""
    url = f"{API_BASE}/water/history"
    params = {
        'start_time': f"-{hours}h"
    }
    if device_id:
        params['device_id'] = device_id
    
    try:
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            result = response.json()
            data_count = len(result.get('data', []))
            print(f"\n历史数据查询结果（最近{hours}小时）:")
            print(f"  总记录数: {data_count}")
            if data_count > 0:
                print(f"  第一条数据: {json.dumps(result['data'][0], ensure_ascii=False)}")
                print(f"  最后一条数据: {json.dumps(result['data'][-1], ensure_ascii=False)}")
            return result
        else:
            print(f"❌ 查询失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return None


def main():
    print("=" * 60)
    print("MQTT数据测试脚本")
    print("模拟ESP32传感器发送水质数据")
    print("=" * 60)
    
    # 发送测试数据
    print("\n1. 发送测试数据...")
    for device_id in DEVICE_IDS:
        send_water_quality(device_id)
        time.sleep(0.5)
    
    # 查询最新数据
    print("\n2. 查询最新数据...")
    query_latest_data()
    
    # 查询历史数据
    print("\n3. 查询历史数据...")
    query_history_data()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
