"""测试云服务器端口是否开放"""
import socket

HOST = "81.71.69.247"
PORTS = {
    "InfluxDB": 8181,
    "MQTT": 1883,
    "MySQL": 3306,
    "Backend": 8000,
}

print(f"测试服务器 {HOST} 端口连通性...\n")
for name, port in PORTS.items():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    result = s.connect_ex((HOST, port))
    status = "OPEN ✅" if result == 0 else "CLOSED ❌"
    print(f"  {name:12s} (端口 {port:5d}): {status}")
    s.close()
