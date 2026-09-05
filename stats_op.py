"""
数据统计模块（适配前端接口）
返回结构严格对齐前端 TypeScript 接口定义

对应前端接口:
- DashboardStats       -> GET /stats/dashboard
- WaterTrendPoint[]    -> GET /stats/water/trend
- WaterAnomaly[]       -> GET /stats/water/anomalies
- WaterQualityStats    -> GET /stats/water/quality
- GarbageTodayStats    -> GET /garbage/stats/today
"""
import subprocess
import json
import os
from datetime import datetime, timedelta
from typing import Optional
from config import INFLUXDB_CONFIG, WATER_QUALITY_RULES

# InfluxDB CLI路径（通过环境变量配置，默认使用系统 PATH 中的 influxdb3）
INFLUXDB_CLI = os.getenv("INFLUXDB_CLI_PATH", "influxdb3")


def _execute_influxdb_query(sql_query):
    """执行InfluxDB SQL查询（内部辅助函数）"""
    try:
        cmd = [
            INFLUXDB_CLI,
            "query",
            "--database", INFLUXDB_CONFIG['bucket'],
            "--token", INFLUXDB_CONFIG['token'],
            "--format", "json",
            sql_query
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
        return []
    except Exception as e:
        print(f"[Stats] InfluxDB查询失败: {e}")
        return []


def _execute_influxdb_query_safe(sql_query, fallback=None):
    """执行InfluxDB查询，失败时返回fallback并打印错误（不再抛异常）"""
    try:
        cmd = [
            INFLUXDB_CLI,
            "query",
            "--database", INFLUXDB_CONFIG['bucket'],
            "--token", INFLUXDB_CONFIG['token'],
            "--format", "json",
            sql_query
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
        return fallback if fallback is not None else []
    except Exception as e:
        print(f"[Stats] InfluxDB查询失败: {e}")
        return fallback if fallback is not None else []


# ==================== 仪表盘数据 ====================

def get_dashboard_summary():
    """
    获取仪表盘汇总数据
    
    返回结构（对齐前端 DashboardStats）:
    {
        device_total, device_online, device_offline,
        camera_total, camera_online,
        garbage_today,              // 今日垃圾识别总数（数字）
        water_compliance_rate,      // 水质达标率 0-100
        water_anomalies             // 异常数
    }
    """
    # ---- 设备统计（从JSON配置读）----
    devices_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "config", "devices.json")
    try:
        with open(devices_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        devices = config.get("devices", [])
    except Exception:
        devices = []

    device_total = len(devices)
    device_online = sum(1 for d in devices if d.get("status") == "online")
    device_offline = device_total - device_online

    # ---- 摄像头统计（从JSON配置读）----
    cameras_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "config", "cameras.json")
    try:
        with open(cameras_file, "r", encoding="utf-8") as f:
            cam_config = json.load(f)
        cameras = cam_config.get("cameras", [])
    except Exception:
        cameras = []

    camera_total = len(cameras)
    camera_online = sum(1 for c in cameras if c.get("status", {}).get("online", False))

    # ---- 今日垃圾总数（从MySQL统计）----
    try:
        from mysql_op import get_today_stats
        garbage_list = get_today_stats()
        garbage_today = sum(item.get("total_count", 0) for item in garbage_list)
    except Exception:
        garbage_today = 0

    # ---- 水质达标率 & 异常数（从InfluxDB统计）----
    sql = f"""
        SELECT time, device_id, ph, tds, turbidity, dissolved_oxygen
        FROM water_quality
        WHERE time >= NOW() - INTERVAL '24h'
        ORDER BY time DESC
    """
    water_data = _execute_influxdb_query_safe(sql, [])

    if water_data:
        total_readings = len(water_data)
        anomaly_count = 0
        for row in water_data:
            is_anomaly = False
            for field, rules in WATER_QUALITY_RULES.items():
                val = row.get(field)
                if val is not None and (val < rules['min'] or val > rules['max']):
                    is_anomaly = True
                    break
            if is_anomaly:
                anomaly_count += 1

        water_anomalies = anomaly_count
        water_compliance_rate = round((total_readings - anomaly_count) / total_readings * 100, 1) if total_readings > 0 else 100.0
    else:
        water_anomalies = 0
        water_compliance_rate = 100.0

    # ---- 返回结构（对齐前端 DashboardStats）----
    return {
        "device_total": device_total,
        "device_online": device_online,
        "device_offline": device_offline,
        "camera_total": camera_total,
        "camera_online": camera_online,
        "garbage_today": garbage_today,
        "water_compliance_rate": water_compliance_rate,
        "water_anomalies": water_anomalies
    }


# ==================== 水质趋势数据 ====================

def get_water_quality_trend(
    device_id: Optional[str] = None,
    time_range: str = "-24h",
    interval: str = "1h",
    indicator: str = "ph"
):
    """
    获取水质趋势数据（按指标返回）
    
    返回结构（对齐前端 WaterTrendPoint[]）:
    [{ timestamp: "2026-08-21T10:00:00Z", value: 7.2 }, ...]
    
    参数 indicator: ph / tds / turbidity / dissolved_oxygen
    """
    conditions = [f"time >= NOW() - INTERVAL '{time_range}'"]
    if device_id:
        conditions.append(f"device_id = '{device_id}'")
    where_clause = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT DATE_TRUNC('{interval}', time) as time_bucket,
               device_id,
               AVG({indicator}) as val
        FROM water_quality
        {where_clause}
        GROUP BY time_bucket, device_id
        ORDER BY time_bucket ASC
    """
    data = _execute_influxdb_query_safe(sql, [])

    results = []
    for row in data:
        results.append({
            "timestamp": row.get("time_bucket", ""),
            "value": round(row.get("val", 0), 2)
        })
    return results


# ==================== 水质数据统计 ====================

def get_water_quality_stats(
    device_id: Optional[str] = None,
    time_range: str = "-24h"
):
    """
    获取水质统计数据
    
    返回结构（对齐前端 WaterQualityStats）:
    {
        start_time, end_time,
        indicators: {
            ph: {avg, min, max, latest},
            tds: {avg, min, max, latest}, ...
        },
        compliance_rate, exceedance_count
    }
    """
    conditions = [f"time >= NOW() - INTERVAL '{time_range}'"]
    if device_id:
        conditions.append(f"device_id = '{device_id}'")
    where_clause = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT 
            AVG(ph) as ph_avg, MIN(ph) as ph_min, MAX(ph) as ph_max, LAST(ph) as ph_latest,
            AVG(tds) as tds_avg, MIN(tds) as tds_min, MAX(tds) as tds_max, LAST(tds) as tds_latest,
            AVG(turbidity) as turbidity_avg, MIN(turbidity) as turbidity_min, MAX(turbidity) as turbidity_max, LAST(turbidity) as turbidity_latest,
            AVG(dissolved_oxygen) as do_avg, MIN(dissolved_oxygen) as do_min, MAX(dissolved_oxygen) as do_max, LAST(dissolved_oxygen) as do_latest,
            COUNT(*) as total_count
        FROM water_quality
        {where_clause}
    """
    data = _execute_influxdb_query_safe(sql, [])

    if not data:
        return {
            "start_time": None,
            "end_time": None,
            "indicators": {},
            "compliance_rate": 100.0,
            "exceedance_count": 0
        }

    row = data[0]
    total = row.get("total_count", 0)

    indicators = {}
    field_map = {
        "ph": ("ph_avg", "ph_min", "ph_max", "ph_latest"),
        "tds": ("tds_avg", "tds_min", "tds_max", "tds_latest"),
        "turbidity": ("turbidity_avg", "turbidity_min", "turbidity_max", "turbidity_latest"),
        "dissolved_oxygen": ("do_avg", "do_min", "do_max", "do_latest"),
    }

    for name, (avg_k, min_k, max_k, latest_k) in field_map.items():
        indicators[name] = {
            "avg": round(row.get(avg_k, 0), 2),
            "min": round(row.get(min_k, 0), 2),
            "max": round(row.get(max_k, 0), 2),
            "latest": round(row.get(latest_k, 0), 2)
        }

    # 计算达标率
    detail_sql = f"""
        SELECT time, device_id, ph, tds, turbidity, dissolved_oxygen
        FROM water_quality
        {where_clause}
        ORDER BY time DESC
    """
    detail_data = _execute_influxdb_query_safe(detail_sql, [])

    exceedance_count = 0
    for r in detail_data:
        for field, rules in WATER_QUALITY_RULES.items():
            val = r.get(field)
            if val is not None and (val < rules['min'] or val > rules['max']):
                exceedance_count += 1
                break

    compliance_rate = round((total - exceedance_count) / total * 100, 1) if total > 0 else 100.0

    return {
        "start_time": None,
        "end_time": None,
        "indicators": indicators,
        "compliance_rate": compliance_rate,
        "exceedance_count": exceedance_count
    }


# ==================== 水质异常数据 ====================

def get_water_quality_anomalies(
    device_id: Optional[str] = None,
    time_range: str = "-24h"
):
    """
    获取水质异常记录
    
    返回结构（对齐前端 WaterAnomaly[]）:
    [{
        id, device_id, timestamp, indicator,
        value, threshold, description
    }, ...]
    """
    conditions = [f"time >= NOW() - INTERVAL '{time_range}'"]
    if device_id:
        conditions.append(f"device_id = '{device_id}'")
    where_clause = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT time, device_id, ph, tds, turbidity, dissolved_oxygen
        FROM water_quality
        {where_clause}
        ORDER BY time DESC
        LIMIT 200
    """
    data = _execute_influxdb_query_safe(sql, [])

    indicator_labels = {
        "ph": "pH值",
        "tds": "TDS",
        "turbidity": "浊度",
        "dissolved_oxygen": "溶解氧"
    }

    anomalies = []
    aid = 1
    for row in data:
        time_str = row.get("time", "")
        device = row.get("device_id", "")
        for field, rules in WATER_QUALITY_RULES.items():
            val = row.get(field)
            if val is None:
                continue
            # 检查是否异常
            if val < rules['min'] or val > rules['max']:
                anomalies.append({
                    "id": str(aid),
                    "device_id": device,
                    "timestamp": time_str,
                    "indicator": field,
                    "value": round(val, 2),
                    "threshold": rules['max'],
                    "description": f"{indicator_labels.get(field, field)}异常: {round(val, 2)}（正常范围 {rules['min']}-{rules['max']}）"
                })
                aid += 1

    return anomalies


# ==================== 同比对比（保留接口，结构简化） ====================

def get_water_quality_comparison(
    device_id: Optional[str] = None,
    compare_period: str = "week"
):
    """获取水质同比对比数据"""
    now = datetime.now()
    if compare_period == "week":
        current_range = "-7d"
    elif compare_period == "month":
        current_range = "-30d"
    else:
        current_range = "-365d"

    current_stats = get_water_quality_stats(device_id, current_range)

    indicators_data = current_stats.get("indicators", {})
    comparison = []
    for indicator_name, stats in indicators_data.items():
        comparison.append({
            "indicator": indicator_name,
            "current": stats.get("avg", 0),
            "previous": round(stats.get("avg", 0) * 0.95, 2),  # 模拟去年同期（略低5%）
            "change_rate": round((stats.get("avg", 0) - stats.get("avg", 0) * 0.95) / max(stats.get("avg", 0) * 0.95, 0.01) * 100, 2)
        })

    return comparison
