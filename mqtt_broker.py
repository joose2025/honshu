"""
MQTT Broker服务（使用gmqtt库）
用于测试ESP32传感器数据上传

启动方式: python mqtt_broker.py
默认端口: 1883
"""
import asyncio
import logging
from gmqtt import Broker

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 订阅的客户端列表
subscribed_clients = {}

async def on_connect(client, flags, rc, properties):
    """客户端连接回调"""
    logger.info(f"客户端连接: {client.client_id}")

async def on_message(client, topic, payload, qos, properties):
    """消息接收回调"""
    try:
        message = payload.decode('utf-8')
        logger.info(f"收到消息 - 主题: {topic}, 内容: {message}")
        
        # 广播给所有订阅了该主题的客户端
        await broker.publish(topic, payload, qos)
        
    except Exception as e:
        logger.error(f"消息处理错误: {e}")

async def on_disconnect(client, packet, exc=None):
    """客户端断开连接回调"""
    logger.info(f"客户端断开: {client.client_id}")

async def main():
    global broker
    
    # 创建MQTT Broker
    broker = Broker("127.0.0.1", 1883)
    
    # 设置回调
    broker.on_connect = on_connect
    broker.on_message = on_message
    broker.on_disconnect = on_disconnect
    
    # 启动Broker
    logger.info("启动MQTT Broker...")
    await broker.start()
    logger.info("MQTT Broker启动成功，监听 127.0.0.1:1883")
    
    # 保持运行
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("正在停止MQTT Broker...")
        await broker.stop()
        logger.info("MQTT Broker已停止")

if __name__ == "__main__":
    asyncio.run(main())
