"""
配置文件模块
负责加载环境变量并提供全局配置参数
"""
from dotenv import load_dotenv
import os

# 加载.env环境配置文件
load_dotenv()

# ==================== MySQL数据库配置 ====================
MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', '123456'),
    'database': os.getenv('MYSQL_DATABASE', 'mangrove_db'),
    'charset': 'utf8mb4'
}

# ==================== InfluxDB时序数据库配置 ====================
INFLUXDB_CONFIG = {
    'url': os.getenv('INFLUXDB_URL', 'http://localhost:8086'),
    'token': os.getenv('INFLUXDB_TOKEN', 'my_secret_token'),
    'org': os.getenv('INFLUXDB_ORG', 'mangrove_org'),
    'bucket': os.getenv('INFLUXDB_BUCKET', 'water_quality')
}

# ==================== MQTT配置 ====================
MQTT_CONFIG = {
    'broker': os.getenv('MQTT_BROKER', 'localhost'),
    'port': int(os.getenv('MQTT_PORT', 1883)),
    'topic': os.getenv('MQTT_TOPIC', 'mangrove/water/+'),
    'client_id': os.getenv('MQTT_CLIENT_ID', 'mangrove_backend')
}

# ==================== API服务配置 ====================
"""API_CONFIG = {
    'host': os.getenv('API_HOST', '0.0.0.0'),
    'port': int(os.getenv('API_PORT', 8000))
}
"""
API_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000
}

# ==================== 图片存储配置 ====================
IMAGE_STORE_PATH = os.getenv('IMAGE_STORE_PATH', './uploads/images')

# 创建图片存储目录（如果不存在）
os.makedirs(IMAGE_STORE_PATH, exist_ok=True)

# ==================== 水质数据校验规则（异常值过滤） ====================
WATER_QUALITY_RULES = {
    'ph': {'min': 6.0, 'max': 8.5, 'default': 7.0},           # pH值范围
    'tds': {'min': 100, 'max': 500, 'default': 300},          # TDS范围：ppm
    'turbidity': {'min': 0, 'max': 50, 'default': 15},        # 浊度范围：NTU
    'dissolved_oxygen': {'min': 4.0, 'max': 9.0, 'default': 7.0} # 溶解氧范围：mg/L
}

# ==================== 项目根目录 ====================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
