#!/bin/bash
# ============================================================
# 红树林垃圾识别监测系统 - 服务器端一键部署脚本
# 使用方式：bash deploy.sh
# ============================================================

set -e

echo "=========================================="
echo "  红树林监测系统 - 后端部署"
echo "=========================================="

# 项目目录
APP_DIR="/www/wwwroot/mangrove-backend"

# ==================== 1. 创建项目目录 ====================
echo "[1/7] 创建项目目录..."
mkdir -p $APP_DIR
cd $APP_DIR

# ==================== 2. 创建 Python 虚拟环境 ====================
echo "[2/7] 创建 Python 虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# ==================== 3. 安装 Python 依赖 ====================
echo "[3/7] 安装 Python 依赖..."
pip install --upgrade pip
pip install fastapi==0.110.0 uvicorn==0.28.0 pydantic==2.6.0
pip install mysql-connector-python==8.3.0 influxdb-client==1.36.0
pip install paho-mqtt==1.6.1 python-dotenv==1.0.0 python-dateutil==2.9.0

# ==================== 4. 配置环境变量 ====================
echo "[4/7] 配置环境变量..."
if [ ! -f .env ]; then
    cat > .env << 'ENVEOF'
# MySQL配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=这里填你的MySQL密码
MYSQL_DATABASE=mangrove_db

# InfluxDB配置
INFLUXDB_URL=http://localhost:8181
INFLUXDB_TOKEN=apiv3_4P_Y9L9KFBDo9kkc-X5BzjepwUklQeCSVS6varYKwPlnPTH7VrvVVQh1M7-a7fLSbfvvmDls6F7zsg1uhLA81w
INFLUXDB_ORG=mangrove_org
INFLUXDB_BUCKET=water_quality
INFLUXDB_CLI_PATH=influxdb3

# MQTT配置
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_TOPIC=mangrove/water/+
MQTT_CLIENT_ID=mangrove_backend_server_01

# API配置
API_HOST=0.0.0.0
API_PORT=8000

# 图片存储
IMAGE_STORE_PATH=./uploads/images
ENVEOF
    echo "  -> 已生成 .env 文件，请编辑修改 MySQL 密码"
    echo "  -> 命令: nano $APP_DIR/.env"
else
    echo "  -> .env 已存在，跳过"
fi

# ==================== 5. 初始化 MySQL 数据库 ====================
echo "[5/7] 初始化 MySQL 数据库..."
echo "  -> 请手动在宝塔面板的 phpMyAdmin 中导入 database_init.sql"

# ==================== 6. 配置防火墙 ====================
echo "[6/7] 提醒：在宝塔面板开放 8000 端口"
echo "  -> 宝塔面板 -> 安全 -> 放行端口 -> 添加 8000"

# ==================== 7. 启动服务 ====================
echo "[7/7] 启动后端服务..."
echo ""
echo "=========================================="
echo "  部署文件已准备完成！"
echo "=========================================="
echo ""
echo "接下来你需要做："
echo ""
echo "1. 编辑 .env 文件，填入正确的 MySQL 密码："
echo "   nano $APP_DIR/.env"
echo ""
echo "2. 在宝塔面板 phpMyAdmin 中导入 database_init.sql"
echo ""
echo "3. 在宝塔面板安全中放行 8000 端口"
echo ""
echo "4. 启动后端服务："
echo "   cd $APP_DIR"
echo "   source venv/bin/activate"
echo "   nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 &"
echo ""
echo "5. 验证服务是否启动："
echo "   curl http://localhost:8000/api/v1/stats/dashboard"
echo ""
echo "6. 外部访问测试："
echo "   http://81.71.69.247:8000/api/v1/stats/dashboard"
echo ""
