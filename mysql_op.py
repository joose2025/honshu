"""
MySQL操作模块
专门负责垃圾识别记录的存储和查询
关系型数据库适合存储结构化的识别记录，便于按条件筛选和统计
"""
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from config import MYSQL_CONFIG

# 全局MySQL连接实例
_mysql_connection = None


def init_mysql():
    """
    初始化MySQL连接
    在应用启动时调用一次即可
    """
    global _mysql_connection
    
    try:
        # 创建MySQL连接
        _mysql_connection = mysql.connector.connect(
            host=MYSQL_CONFIG['host'],
            port=MYSQL_CONFIG['port'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password'],
            database=MYSQL_CONFIG['database'],
            charset=MYSQL_CONFIG['charset']
        )
        
        # 创建游标
        cursor = _mysql_connection.cursor()
        
        # 创建垃圾识别记录表（如果不存在）
        # 严格按照用户要求的表结构：garbage_detect_record
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS garbage_detect_record (
                id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
                camera_id VARCHAR(50) NOT NULL COMMENT '摄像头设备号',
                detect_time DATETIME NOT NULL COMMENT '识别时间',
                garbage_type VARCHAR(50) NOT NULL COMMENT '垃圾种类：塑料袋/塑料瓶/渔网/易拉罐等',
                count INT DEFAULT 1 COMMENT '单次识别垃圾总数',
                confidence FLOAT DEFAULT 0 COMMENT '平均置信度',
                image_path VARCHAR(500) COMMENT '抓拍图片本地路径',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='垃圾识别记录表';
        """
        cursor.execute(create_table_sql)
        _mysql_connection.commit()
        cursor.close()
        
        print("[MySQL] 连接成功，表结构已就绪")
        return True
    except Error as e:
        print(f"[MySQL] 连接失败: {e}")
        return False


def get_connection():
    """
    获取MySQL连接（支持自动重连）
    如果连接断开，尝试重新连接
    """
    global _mysql_connection
    
    try:
        # 检查连接是否有效
        if _mysql_connection and _mysql_connection.is_connected():
            return _mysql_connection
        
        # 重新连接
        print("[MySQL] 连接断开，尝试重新连接...")
        _mysql_connection = mysql.connector.connect(
            host=MYSQL_CONFIG['host'],
            port=MYSQL_CONFIG['port'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password'],
            database=MYSQL_CONFIG['database'],
            charset=MYSQL_CONFIG['charset']
        )
        print("[MySQL] 重新连接成功")
        return _mysql_connection
        
    except Error as e:
        print(f"[MySQL] 重新连接失败: {e}")
        return None


def save_garbage_record(data):
    """
    保存垃圾识别记录到MySQL
    
    参数:
        data: 字典，包含以下字段:
            - camera_id: 摄像头编号
            - detect_time: 识别时间（datetime对象或字符串）
            - garbage_type: 垃圾类型
            - count: 垃圾数量
            - confidence: 平均置信度
            - image_path: 抓拍图片本地路径
    
    返回:
        tuple: (成功标志, 记录ID)
    """
    conn = get_connection()
    if not conn:
        print("[MySQL] 无法获取连接")
        return False, 0
    
    try:
        cursor = conn.cursor()
        
        # 处理时间格式
        # 如果是字符串，转换为datetime对象
        detect_time = data.get('detect_time')
        if isinstance(detect_time, str):
            detect_time = datetime.strptime(detect_time, "%Y-%m-%d %H:%M:%S")
        elif not isinstance(detect_time, datetime):
            detect_time = datetime.now()
        
        # SQL插入语句
        # 严格按照用户要求的表名和字段名
        insert_sql = """
            INSERT INTO garbage_detect_record 
            (camera_id, detect_time, garbage_type, count, confidence, image_path)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        # 参数列表
        params = (
            data.get('camera_id', 'unknown'),      # 摄像头编号
            detect_time,                            # 识别时间
            data.get('garbage_type', '未知'),       # 垃圾类型
            data.get('count', 1),                   # 垃圾数量
            data.get('confidence', 0.0),            # 平均置信度
            data.get('image_path', '')              # 图片路径
        )
        
        # 执行插入
        cursor.execute(insert_sql, params)
        conn.commit()
        
        # 获取自增ID
        record_id = cursor.lastrowid
        cursor.close()
        
        print(f"[MySQL] 垃圾识别记录保存成功: id={record_id}, type={data.get('garbage_type')}")
        return True, record_id
        
    except Error as e:
        print(f"[MySQL] 保存失败: {e}")
        conn.rollback()
        return False, 0


def query_garbage_records(page=1, page_size=20, camera_id=None, garbage_type=None):
    """
    分页查询垃圾识别记录
    
    参数:
        page: 页码（从1开始）
        page_size: 每页数量
        camera_id: 摄像头编号（可选，用于筛选）
        garbage_type: 垃圾类型（可选，用于筛选）
    
    返回:
        dict: {'total': 总记录数, 'data': 当前页记录列表}
    """
    conn = get_connection()
    if not conn:
        print("[MySQL] 无法获取连接")
        return {'total': 0, 'data': []}
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 构建查询条件
        where_clause = "WHERE 1=1"
        params = []
        
        if camera_id:
            where_clause += " AND camera_id = %s"
            params.append(camera_id)
        
        if garbage_type:
            where_clause += " AND garbage_type = %s"
            params.append(garbage_type)
        
        # 查询总记录数
        count_sql = f"SELECT COUNT(*) as total FROM garbage_detect_record {where_clause}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']
        
        # 计算分页偏移量
        offset = (page - 1) * page_size
        
        # 查询当前页数据
        query_sql = f"""
            SELECT * FROM garbage_detect_record 
            {where_clause} 
            ORDER BY detect_time DESC 
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])
        
        cursor.execute(query_sql, params)
        records = cursor.fetchall()
        
        cursor.close()
        
        print(f"[MySQL] 查询完成: 共 {total} 条记录，当前页 {page}")
        return {'total': total, 'data': records}
        
    except Error as e:
        print(f"[MySQL] 查询失败: {e}")
        return {'total': 0, 'data': []}


def get_today_stats(garbage_type=None):
    """
    获取当日垃圾识别统计
    
    参数:
        garbage_type: 垃圾类型（可选，不传则统计所有类型）
    
    返回:
        list: 统计结果列表，每个元素包含类型和数量
    """
    conn = get_connection()
    if not conn:
        print("[MySQL] 无法获取连接")
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 获取今日日期范围
        today = datetime.now().strftime("%Y-%m-%d")
        start_time = f"{today} 00:00:00"
        end_time = f"{today} 23:59:59"
        
        # 构建查询
        if garbage_type:
            # 统计指定类型的今日总数
            sql = """
                SELECT garbage_type, SUM(count) as total_count 
                FROM garbage_detect_record 
                WHERE detect_time BETWEEN %s AND %s 
                AND garbage_type = %s
                GROUP BY garbage_type
            """
            params = (start_time, end_time, garbage_type)
        else:
            # 统计所有类型的今日总数
            sql = """
                SELECT garbage_type, SUM(count) as total_count 
                FROM garbage_detect_record 
                WHERE detect_time BETWEEN %s AND %s 
                GROUP BY garbage_type 
                ORDER BY total_count DESC
            """
            params = (start_time, end_time)
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
        cursor.close()
        
        print(f"[MySQL] 今日统计完成: {len(results)} 种垃圾类型")
        return results
        
    except Error as e:
        print(f"[MySQL] 统计失败: {e}")
        return []


def get_camera_list():
    """
    获取所有摄像头列表（去重）
    
    返回:
        list: 摄像头ID列表
    """
    conn = get_connection()
    if not conn:
        print("[MySQL] 无法获取连接")
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        sql = "SELECT DISTINCT camera_id FROM garbage_detect_record ORDER BY camera_id"
        cursor.execute(sql)
        results = cursor.fetchall()
        cursor.close()
        
        # 提取camera_id字段
        camera_ids = [row['camera_id'] for row in results]
        return camera_ids
        
    except Error as e:
        print(f"[MySQL] 获取摄像头列表失败: {e}")
        return []


def get_garbage_types():
    """
    获取所有垃圾类型列表（去重）
    
    返回:
        list: 垃圾类型列表
    """
    conn = get_connection()
    if not conn:
        print("[MySQL] 无法获取连接")
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        sql = "SELECT DISTINCT garbage_type FROM garbage_detect_record ORDER BY garbage_type"
        cursor.execute(sql)
        results = cursor.fetchall()
        cursor.close()
        
        # 提取garbage_type字段
        types = [row['garbage_type'] for row in results]
        return types
        
    except Error as e:
        print(f"[MySQL] 获取垃圾类型列表失败: {e}")
        return []


def close_mysql():
    """
    关闭MySQL连接
    在应用退出时调用
    """
    global _mysql_connection
    
    if _mysql_connection and _mysql_connection.is_connected():
        _mysql_connection.close()
        print("[MySQL] 连接已关闭")
