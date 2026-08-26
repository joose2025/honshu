"""
种子数据脚本
往MySQL和InfluxDB里灌mock数据，让前端页面能显示真实数据

运行方式: python seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mysql.connector
import time
import json
from datetime import datetime, timedelta
from config import MYSQL_CONFIG, INFLUXDB_CONFIG, WATER_QUALITY_RULES

# ==================== 配置 ====================
# 垃圾类型
GARBAGE_TYPES = ["塑料瓶", "塑料袋", "易拉罐", "渔网", "玻璃瓶", "纸张"]
CAMERA_IDS = ["camera_01", "camera_02", "camera_03"]

# 水质设备
WATER_DEVICES = ["esp32_sensor_01", "esp32_sensor_02"]

# 24小时内的mock数据点数量
HOURS = 24
POINTS_PER_HOUR = 4  # 每15分钟一个点


def seed_mysql():
    """往MySQL里灌今日垃圾识别记录"""
    print("[Seed] 正在往MySQL灌垃圾数据...")

    conn = mysql.connector.connect(
        host=MYSQL_CONFIG['host'],
        port=MYSQL_CONFIG['port'],
        user=MYSQL_CONFIG['user'],
        password=MYSQL_CONFIG['password'],
        database=MYSQL_CONFIG['database'],
        charset=MYSQL_CONFIG['charset']
    )
    cursor = conn.cursor()

    # 先清空旧数据
    cursor.execute("DELETE FROM garbage_detect_record")
    conn.commit()
    print("[Seed] 旧数据已清空")

    # 灌今日数据：生成40条记录
    now = datetime.now()
    records = []
    for i in range(40):
        detect_time = now - timedelta(minutes=30 * i)
        camera = CAMERA_IDS[i % len(CAMERA_IDS)]
        gtype = GARBAGE_TYPES[i % len(GARBAGE_TYPES)]
        count = (i % 5) + 1
        confidence = round(0.70 + (i * 0.005), 2)

        records.append((camera, detect_time, gtype, count, confidence, ""))

    insert_sql = """
        INSERT INTO garbage_detect_record
        (camera_id, detect_time, garbage_type, count, confidence, image_path)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cursor.executemany(insert_sql, records)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM garbage_detect_record")
    total = cursor.fetchone()[0]
    print(f"[Seed] MySQL灌完，共 {total} 条垃圾记录")

    cursor.close()
    conn.close()


def seed_influxdb():
    """往InfluxDB里灌24小时水质数据"""
    print("[Seed] 正在往InfluxDB灌水质数据...")

    try:
        from influxdb_client import InfluxDBClient, Point
        from influxdb_client.client.write_api import SYNCHRONOUS

        client = InfluxDBClient(
            url=INFLUXDB_CONFIG['url'],
            token=INFLUXDB_CONFIG['token'],
            org=INFLUXDB_CONFIG['org']
        )
        # 测试连接
        client.health()
        write_api = client.write_api(write_options=SYNCHRONOUS)
    except Exception as e:
        print(f"[Seed] InfluxDB连接失败: {e}")
        print("[Seed] 跳过InfluxDB种子数据，请先启动InfluxDB后再运行seed_data.py")
        return

    # 先清空旧数据（删除water_quality measurement）
    try:
        delete_cmd = [
            "c:\\Users\\joose\\OneDrive\\Desktop\\influxdb3-core-3.10.5-windows_amd64\\influxdb3.exe",
            "delete",
            "--database", INFLUXDB_CONFIG['bucket'],
            "--token", INFLUXDB_CONFIG['token'],
            "--measurement", "water_quality",
            "--start", "-30d",
            "--stop", "+1d"
        ]
        import subprocess
        result = subprocess.run(delete_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("[Seed] InfluxDB旧数据已清空")
    except Exception as e:
        print(f"[Seed] 清空InfluxDB旧数据跳过: {e}")

    # 灌数据：2个设备 × 24小时 × 4个点/小时 = 192条
    now = datetime.now()
    count = 0
    for device_id in WATER_DEVICES:
        for h in range(HOURS):
            for p in range(POINTS_PER_HOUR):
                time_dt = now - timedelta(hours=h, minutes=15 * p)

                # 生成合理范围的水质数据
                # 偶尔生成异常值，方便异常检测功能演示
                is_anomaly = (h == 5 and p == 0 and device_id == "esp32_sensor_01")

                if is_anomaly:
                    ph = 9.5  # 异常：pH偏高
                    tds = 600  # 异常：TDS偏高
                    turbidity = 50  # 异常：浊度偏高
                    dissolved_oxygen = 3.0  # 异常：溶解氧偏低
                else:
                    ph = round(6.8 + 0.4 * (p / POINTS_PER_HOUR) + 0.1 * (h % 3), 2)
                    tds = round(280 + 30 * (p / POINTS_PER_HOUR) + 20 * (h % 4), 1)
                    turbidity = round(12 + 4 * (p / POINTS_PER_HOUR) + 2 * (h % 5), 1)
                    dissolved_oxygen = round(6.5 + 0.5 * (p / POINTS_PER_HOUR) - 0.3 * (h % 4), 2)

                point = (
                    Point("water_quality")
                    .tag("device_id", device_id)
                    .field("ph", float(ph))
                    .field("tds", float(tds))
                    .field("turbidity", float(turbidity))
                    .field("dissolved_oxygen", float(dissolved_oxygen))
                    .time(time_dt)
                )
                write_api.write(
                    bucket=INFLUXDB_CONFIG['bucket'],
                    org=INFLUXDB_CONFIG['org'],
                    record=point
                )
                count += 1

    print(f"[Seed] InfluxDB灌完，共 {count} 条水质记录")
    client.close()


def main():
    print("=" * 50)
    print("  红树林监测系统 - 种子数据脚本")
    print("=" * 50)
    print()

    try:
        seed_mysql()
        print()
        seed_influxdb()
        print()
        print("=" * 50)
        print("  ✅ 种子数据灌完了！")
        print("  重启后端服务，前端刷新页面就能看到数据了")
        print("=" * 50)
    except Exception as e:
        print(f"[Seed] 出错了: {e}")
        import traceback
        traceback.print_exc()
    print("[Seed] 完成（MySQL已灌，InfluxDB跳过或已灌）")


if __name__ == "__main__":
    main()
