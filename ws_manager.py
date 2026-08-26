"""
WebSocket连接管理器
负责管理前端WebSocket连接，实现实时数据推送
当有新的水质数据或垃圾识别结果时，广播给所有连接的前端客户端
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import json

# 存储所有活动的WebSocket连接
class ConnectionManager:
    def __init__(self):
        # 存储所有活跃的WebSocket连接
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """
        新客户端连接时调用
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WebSocket] 新客户端连接，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """
        客户端断开连接时调用
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[WebSocket] 客户端断开连接，当前连接数: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        向单个客户端发送消息
        """
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            print(f"[WebSocket] 发送消息失败: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        """
        向所有连接的客户端广播消息
        """
        connections_copy = self.active_connections.copy()
        
        for connection in connections_copy:
            try:
                await connection.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                print(f"[WebSocket] 广播消息失败，移除连接: {e}")
                self.disconnect(connection)
    
    async def broadcast_water_quality(self, data: dict):
        """
        广播水质实时数据
        """
        message = {
            'type': 'water_quality',
            'data': data
        }
        await self.broadcast(message)
        print(f"[WebSocket] 广播水质数据: device_id={data.get('device_id')}")
    
    async def broadcast_garbage_detection(self, data: dict):
        """
        广播垃圾识别结果（弹窗通知）
        """
        message = {
            'type': 'garbage_detection',
            'data': data
        }
        await self.broadcast(message)
        print(f"[WebSocket] 广播垃圾识别: camera_id={data.get('camera_id')}, type={data.get('garbage_type')}")


# 创建全局WebSocket连接管理器实例
ws_manager = ConnectionManager()
