"""临时脚本：获取当前cpolar在线隧道的公网域名"""
import requests
import json

try:
    r = requests.get("http://localhost:9200/api/online_tunnels", timeout=5)
    data = r.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"请求失败: {e}")

# 同时尝试另一个API
try:
    r2 = requests.get("http://localhost:9200/status", timeout=5)
    print("\n--- Status ---")
    print(r2.text[:1000])
except Exception as e:
    print(f"Status请求失败: {e}")
