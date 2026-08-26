"""获取 cpolar 在线隧道域名"""
import requests
import json
import time

# 等待 cpolar 启动
time.sleep(2)

# 尝试不同的 API 端点
endpoints = [
    "http://localhost:9200/api/http_tunnels",
    "http://localhost:9200/api/tunnel/list", 
    "http://localhost:9200/api/proxy",
    "http://localhost:9200/status",
]

for ep in endpoints:
    try:
        r = requests.get(ep, timeout=5)
        print(f"=== {ep} ===")
        print(f"Status: {r.status_code}")
        print(f"Content: {r.text[:500]}")
        print()
    except Exception as e:
        print(f"{ep}: {e}")
