"""
WebSocket实时推送测试
"""
import asyncio
import websockets
import json
import requests
import threading
import time

async def test_websocket():
    """测试WebSocket实时推送"""
    print("[WebSocket] 连接到服务器...")
    try:
        async with websockets.connect("ws://localhost:8000/api/v1/ws") as websocket:
            print("[WebSocket] 连接成功！")
            
            # 同时发送一条测试数据触发推送
            def send_data():
                time.sleep(2)
                requests.post("http://localhost:8000/api/v1/water/data", params={
                    "device_id": "ws_test_device",
                    "ph": 7.5,
                    "tds": 380.0,
                    "turbidity": 22.5,
                    "dissolved_oxygen": 6.2
                })
                print("[WebSocket] 已发送测试数据")
            
            threading.Thread(target=send_data, daemon=True).start()
            
            # 接收消息
            print("[WebSocket] 等待接收实时数据...")
            count = 0
            while count < 3:
                message = await websocket.recv()
                print(f"[WebSocket] 收到消息: {message}")
                count += 1
            
            print("[WebSocket] 测试完成")
            
    except Exception as e:
        print(f"[WebSocket] 连接失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
