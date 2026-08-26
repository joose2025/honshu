"""
测试新添加的API接口
"""
import requests
import json

base_url = 'http://localhost:8000/api/v1'

def test_device_heartbeat():
    """测试设备心跳"""
    print('1. 测试设备心跳')
    r = requests.post(f'{base_url}/devices/esp32_sensor_01/heartbeat', params={
        'status': 'online',
        'ph': 7.2,
        'tds': 320
    })
    print(f'   状态码: {r.status_code}')
    print(f'   响应: {json.dumps(r.json(), ensure_ascii=False)}')
    return r.status_code == 200

def test_device_list():
    """测试设备列表"""
    print('\n2. 测试设备列表')
    r = requests.get(f'{base_url}/devices')
    print(f'   状态码: {r.status_code}')
    data = r.json()
    count = len(data.get("data", []))
    print(f'   设备数: {count}')
    return r.status_code == 200

def test_device_stats():
    """测试设备统计"""
    print('\n3. 测试设备统计')
    r = requests.get(f'{base_url}/devices/stats')
    print(f'   状态码: {r.status_code}')
    print(f'   响应: {json.dumps(r.json(), ensure_ascii=False)}')
    return r.status_code == 200

def test_water_quality_stats():
    """测试水质统计"""
    print('\n4. 测试水质统计')
    r = requests.get(f'{base_url}/stats/water/quality', params={'time_range': '-24h'})
    print(f'   状态码: {r.status_code}')
    data = r.json()
    records = data.get("data", [])
    print(f'   统计设备数: {len(records)}')
    return r.status_code == 200

def test_dashboard():
    """测试仪表盘"""
    print('\n5. 测试仪表盘汇总')
    r = requests.get(f'{base_url}/stats/dashboard')
    print(f'   状态码: {r.status_code}')
    if r.status_code == 200:
        data = r.json().get('data', {})
        print(f'   更新时间: {data.get("update_time")}')
        print(f'   系统状态: {data.get("system_status")}')
    return r.status_code == 200

def test_water_trend():
    """测试水质趋势"""
    print('\n6. 测试水质趋势')
    r = requests.get(f'{base_url}/stats/water/trend', params={'time_range': '-24h', 'interval': '1h'})
    print(f'   状态码: {r.status_code}')
    data = r.json()
    records = data.get("data", [])
    print(f'   趋势点数: {len(records)}')
    return r.status_code == 200

def test_camera_list():
    """测试摄像头列表"""
    print('\n7. 测试摄像头列表')
    r = requests.get(f'{base_url}/video/cameras')
    print(f'   状态码: {r.status_code}')
    data = r.json()
    cameras = data.get("data", [])
    print(f'   摄像头数: {len(cameras)}')
    return r.status_code == 200

def main():
    print('=' * 60)
    print('  测试新添加的API接口')
    print('=' * 60)
    
    tests = [
        test_device_heartbeat,
        test_device_list,
        test_device_stats,
        test_water_quality_stats,
        test_dashboard,
        test_water_trend,
        test_camera_list
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f'   测试异常: {e}')
            results.append(False)
    
    print('\n' + '=' * 60)
    passed = sum(results)
    total = len(results)
    print(f'测试完成: {passed}/{total} 通过')
    print('=' * 60)

if __name__ == '__main__':
    main()
