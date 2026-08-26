"""
简单的MQTT Broker实现（基于paho-mqtt）
用于测试目的，不支持完整的MQTT协议
"""
import socket
import threading
import json

class SimpleMQTTBroker:
    def __init__(self, host='127.0.0.1', port=1883):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {}
        self.topics = {}
        self.running = False
        
    def start(self):
        """启动MQTT Broker"""
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        self.running = True
        print(f"[MQTT Broker] 启动成功，监听 {self.host}:{self.port}")
        
        while self.running:
            try:
                client_socket, addr = self.socket.accept()
                print(f"[MQTT Broker] 新客户端连接: {addr}")
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, addr))
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                if self.running:
                    print(f"[MQTT Broker] 错误: {e}")
    
    def handle_client(self, client_socket, addr):
        """处理客户端连接"""
        client_id = f"client_{addr[0]}_{addr[1]}"
        self.clients[client_id] = client_socket
        
        try:
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    break
                    
                try:
                    # 简单处理MQTT协议
                    # 实际MQTT协议是二进制的，这里简化处理
                    payload = data.decode('utf-8')
                    print(f"[MQTT Broker] 收到消息: {payload}")
                    
                    # 尝试解析JSON消息
                    try:
                        msg = json.loads(payload)
                        if 'topic' in msg and 'message' in msg:
                            self.publish(msg['topic'], msg['message'])
                    except:
                        pass
                except:
                    pass
        except Exception as e:
            print(f"[MQTT Broker] 客户端处理错误: {e}")
        finally:
            del self.clients[client_id]
            client_socket.close()
            print(f"[MQTT Broker] 客户端断开: {addr}")
    
    def publish(self, topic, message):
        """发布消息到主题"""
        print(f"[MQTT Broker] 发布消息到主题 {topic}")
        # 广播给所有客户端
        for client_id, sock in self.clients.items():
            try:
                response = json.dumps({'topic': topic, 'message': message}) + '\n'
                sock.send(response.encode('utf-8'))
            except:
                pass
    
    def stop(self):
        """停止MQTT Broker"""
        self.running = False
        self.socket.close()
        print("[MQTT Broker] 已停止")

if __name__ == "__main__":
    broker = SimpleMQTTBroker()
    try:
        broker.start()
    except KeyboardInterrupt:
        broker.stop()
