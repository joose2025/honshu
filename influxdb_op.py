"""
InfluxDB操作模块
专门负责水质时序数据的存储和查询
时序数据库适合存储传感器连续采集的数据，便于按时间范围查询和绘制趋势图
适配InfluxDB 3.x版本（写入使用influxdb_client，查询使用命令行工具）
"""
import subprocess
import json
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime
from config import INFLUXDB_CONFIG, WATER_QUALITY_RULES

# 全局InfluxDB客户端实例
_influxdb_client = None
_write_api = None


def init_influxdb():
    """
    初始化InfluxDB连接
    在应用启动时调用一次即可
    """
    global _influxdb_client, _write_api
    
    try:
        # 创建InfluxDB客户端（用于写入数据）
        _influxdb_client = InfluxDBClient(
            url=INFLUXDB_CONFIG['url'],
            token=INFLUXDB_CONFIG['token'],
            org=INFLUXDB_CONFIG['org']
        )
        
        # 创建写入API（同步模式）
        _write_api = _influxdb_client.write_api(write_options=SYNCHRONOUS)
        
        print("[InfluxDB] 连接成功")
        return True
    except Exception as e:
        print(f"[InfluxDB] 连接失败: {e}")
        return False


def write_water_quality(data):
    """
    写入水质时序数据到InfluxDB
    
    参数:
        data: 字典，包含以下字段:
            - device_id: 设备ID
            - timestamp: Unix时间戳（秒）
            - ph: pH值
            - tds: TDS值
            - turbidity: 浊度
            - dissolved_oxygen: 溶解氧
    
    返回:
        bool: 写入成功返回True，失败返回False
    """
    if not _write_api:
        print("[InfluxDB] 客户端未初始化")
        return False
    
    try:
        # 数据校验和异常值过滤
        ph = data.get('ph')
        if ph is None or ph < WATER_QUALITY_RULES['ph']['min'] or ph > WATER_QUALITY_RULES['ph']['max']:
            print(f"[InfluxDB] pH值异常，跳过: {ph}")
            ph = WATER_QUALITY_RULES['ph']['default']
        
        tds = data.get('tds')
        if tds is None or tds < WATER_QUALITY_RULES['tds']['min'] or tds > WATER_QUALITY_RULES['tds']['max']:
            print(f"[InfluxDB] TDS值异常，跳过: {tds}")
            tds = WATER_QUALITY_RULES['tds']['default']
        
        turbidity = data.get('turbidity')
        if turbidity is None or turbidity < WATER_QUALITY_RULES['turbidity']['min'] or turbidity > WATER_QUALITY_RULES['turbidity']['max']:
            print(f"[InfluxDB] 浊度值异常，跳过: {turbidity}")
            turbidity = WATER_QUALITY_RULES['turbidity']['default']
        
        dissolved_oxygen = data.get('dissolved_oxygen')
        if dissolved_oxygen is None or dissolved_oxygen < WATER_QUALITY_RULES['dissolved_oxygen']['min'] or dissolved_oxygen > WATER_QUALITY_RULES['dissolved_oxygen']['max']:
            print(f"[InfluxDB] 溶解氧值异常，跳过: {dissolved_oxygen}")
            dissolved_oxygen = WATER_QUALITY_RULES['dissolved_oxygen']['default']
        
        # 处理时间戳
        timestamp = data.get('timestamp')
        if timestamp:
            time_dt = datetime.fromtimestamp(timestamp)
        else:
            time_dt = datetime.now()
        
        # 构建InfluxDB数据点（Point）
        point = (
            Point("water_quality")  # 测量名称（相当于表名）
            .tag("device_id", data.get('device_id', 'unknown'))  # 设备ID作为标签
            .field("ph", float(ph))  # pH值
            .field("tds", float(tds))  # TDS值
            .field("turbidity", float(turbidity))  # 浊度
            .field("dissolved_oxygen", float(dissolved_oxygen))  # 溶解氧
            .time(time_dt)  # 时间戳
        )
        
        # 写入数据（InfluxDB 3使用bucket作为数据库名）
        _write_api.write(bucket=INFLUXDB_CONFIG['bucket'], org=INFLUXDB_CONFIG['org'], record=point)
        
        print(f"[InfluxDB] 水质数据写入成功: device_id={data.get('device_id')}, time={time_dt}")
        return True
        
    except Exception as e:
        print(f"[InfluxDB] 写入失败: {e}")
        return False


def _cli_query(sql_query):
    """
    使用influxdb3命令行工具执行SQL查询（内部辅助函数）
    
    参数:
        sql_query: SQL查询语句
    
    返回:
        list: 查询结果列表
    """
    try:
        # 构建命令
        cmd = [
            "c:\\Users\\joose\\OneDrive\\Desktop\\AzurLaneAutoScript\\influxdb3-core-3.10.5-windows_amd64\\influxdb3.exe",
            "query",
            "--database", INFLUXDB_CONFIG['bucket'],
            "--token", INFLUXDB_CONFIG['token'],
            "--format", "json",
            sql_query
        ]
        
        # 执行命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
        else:
            print(f"[InfluxDB] CLI查询失败: {result.stderr}")
            return []
    except Exception as e:
        print(f"[InfluxDB] CLI查询异常: {e}")
        return []


def query_water_quality(device_id=None, start_time=None, end_time=None):
    """
    查询历史水质时序数据（使用命令行工具，适配InfluxDB 3）
    
    参数:
        device_id: 设备ID（可选，不传则查询所有设备）
        start_time: 开始时间（字符串，如"2024-01-01T00:00:00Z"或相对时间如"-1h"）
        end_time: 结束时间（字符串，格式同start_time）
    
    返回:
        list: 查询结果列表，每个元素是包含时间和水质指标的字典
    """
    try:
        # 构建条件
        conditions = []
        
        # 处理时间范围
        if start_time:
            if start_time.startswith("-"):
                duration = start_time[1:]
                conditions.append(f"time >= NOW() - INTERVAL '{duration}'")
            else:
                conditions.append(f"time >= '{start_time}'")
        
        if end_time:
            if end_time.startswith("-"):
                duration = end_time[1:]
                conditions.append(f"time <= NOW() - INTERVAL '{duration}'")
            else:
                conditions.append(f"time <= '{end_time}'")
        
        # 处理设备ID过滤
        if device_id:
            conditions.append(f"device_id = '{device_id}'")
        
        # 构建WHERE子句
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # SQL查询
        sql_query = f"""
            SELECT 
                time, device_id, ph, tds, turbidity, dissolved_oxygen
            FROM water_quality
            {where_clause}
            ORDER BY time ASC
        """
        
        # 执行查询
        result = _cli_query(sql_query)
        
        print(f"[InfluxDB] 查询完成，共 {len(result)} 条数据")
        return result
        
    except Exception as e:
        print(f"[InfluxDB] 查询失败: {e}")
        return []


def get_latest_water_quality(device_id=None):
    """
    获取最新的水质数据（使用命令行工具，适配InfluxDB 3）
    
    参数:
        device_id: 设备ID（可选）
    
    返回:
        dict: 最新的水质数据
    """
    try:
        # 构建SQL查询
        where_clause = ""
        if device_id:
            where_clause = f"WHERE device_id = '{device_id}'"
        
        sql_query = f"""
            SELECT 
                time, device_id, ph, tds, turbidity, dissolved_oxygen
            FROM water_quality
            {where_clause}
            ORDER BY time DESC
            LIMIT 1
        """
        
        # 执行查询
        result = _cli_query(sql_query)
        
        if result:
            return result[0]
        
        return None
        
    except Exception as e:
        print(f"[InfluxDB] 获取最新数据失败: {e}")
        return None


def close_influxdb():
    """
    关闭InfluxDB连接
    在应用退出时调用
    """
    global _influxdb_client
    
    if _influxdb_client:
        _influxdb_client.close()
        print("[InfluxDB] 连接已关闭")
