"""
生成API接口文档Word文件
"""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

doc = Document()

# ==================== 设置全局字体 ====================
style = doc.styles['Normal']
font = style.font
font.name = 'Microsoft YaHei'
font.size = Pt(11)

# ==================== 标题 ====================
title = doc.add_heading('红树林垃圾识别监测系统 - 后端API接口文档', level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER

doc.add_paragraph('')
p = doc.add_paragraph('作者：大二计算机学生科创比赛项目')
p = doc.add_paragraph('技术栈：FastAPI + MySQL + InfluxDB + MQTT + WebSocket')
p = doc.add_paragraph('')

# ==================== 第一部分：服务地址 ====================
doc.add_heading('一、后端服务地址', level=1)

table = doc.add_table(rows=3, cols=2, style='Table Grid')
table.alignment = WD_TABLE_ALIGNMENT.CENTER
table.cell(0, 0).text = '服务名称'
table.cell(0, 1).text = '地址'
table.cell(1, 0).text = 'API主页'
table.cell(1, 1).text = 'http://localhost:8000'
table.cell(2, 0).text = 'Swagger在线文档'
table.cell(2, 1).text = 'http://localhost:8000/docs'

doc.add_paragraph('')

# ==================== 第二部分：接口总览 ====================
doc.add_heading('二、接口总览', level=1)

interfaces = [
    # (序号, 请求方式, 路径, 描述, JSON样例)
    (1, 'GET', '/api/v1/water/history', '查询历史水质数据',
     '{"code": 200, "message": "查询成功", "data": [{"time": "2026-08-14T10:00:00Z", "device_id": "water_01", "ph": 7.2, "tds": 320, "turbidity": 15, "dissolved_oxygen": 6.8}]}'),

    (2, 'GET', '/api/v1/water/latest', '获取最新水质数据',
     '{"code": 200, "message": "查询成功", "data": {"device_id": "water_01", "ph": 7.2, "tds": 320, "turbidity": 15, "dissolved_oxygen": 6.8, "time": "2026-08-14T10:00:00Z"}}'),

    (3, 'POST', '/api/v1/water/data', '写入水质数据(测试用)',
     '{"code": 200, "message": "数据写入成功", "data": {"device_id": "water_01", "ph": 7.2, "tds": 320, "turbidity": 15, "dissolved_oxygen": 6.8, "timestamp": 1723593600}}'),

    (4, 'POST', '/api/v1/garbage/detect', '接收垃圾识别结果(YOLO调用)',
     '{"code": 200, "message": "识别结果已保存", "record_id": 1, "data": {"camera_id": "camera_01", "garbage_type": "塑料瓶", "count": 2, "confidence": 92.5, "detect_time": "2026-08-14 10:00:00", "image_path": ""}}'),

    (5, 'GET', '/api/v1/garbage/records', '分页查询垃圾记录',
     '{"code": 200, "message": "查询成功", "data": {"total": 50, "page": 1, "page_size": 20, "records": [{"id": 1, "camera_id": "camera_01", "detect_time": "2026-08-14 10:00:00", "garbage_type": "塑料瓶", "count": 2, "confidence": 92.5, "image_path": ""}]}}'),

    (6, 'GET', '/api/v1/garbage/stats/today', '获取当日垃圾统计',
     '{"code": 200, "message": "查询成功", "data": [{"garbage_type": "塑料瓶", "total_count": 15, "detect_times": 8}, {"garbage_type": "塑料袋", "total_count": 6, "detect_times": 3}]}'),

    (7, 'GET', '/api/v1/garbage/cameras', '获取摄像头列表',
     '{"code": 200, "message": "查询成功", "data": ["camera_01", "camera_02"]}'),

    (8, 'GET', '/api/v1/garbage/types', '获取垃圾类型列表',
     '{"code": 200, "message": "查询成功", "data": ["塑料瓶", "塑料袋", "易拉罐"]}'),

    (9, 'POST', '/api/v1/devices/register', '设备注册',
     '{"code": 200, "message": "设备注册成功", "data": {"id": "esp32_01", "name": "水质传感器1号", "type": "water_sensor", "model": "ESP32", "location": "红树林A区", "created_at": "2026-08-14 10:00:00"}}'),

    (10, 'POST', '/api/v1/devices/{device_id}/heartbeat', '设备心跳上报',
     '{"code": 200, "message": "心跳已接收", "data": {"id": "esp32_01", "status": "online", "last_heartbeat": "2026-08-14 10:00:00"}}'),

    (11, 'GET', '/api/v1/devices', '获取设备列表',
     '{"code": 200, "message": "查询成功", "data": [{"id": "esp32_01", "name": "水质传感器1号", "type": "water_sensor", "location": "红树林A区", "online_status": {"status": "online", "last_heartbeat": 1723593600}}]}'),

    (12, 'GET', '/api/v1/devices/stats', '设备统计(总数/在线/离线)',
     '{"code": 200, "message": "查询成功", "data": {"total": 3, "online": 2, "offline": 1, "offline_unknown": 0, "by_type": {"water_sensor": 2, "camera": 1}}}'),

    (13, 'GET', '/api/v1/devices/{device_id}', '获取单个设备详情',
     '{"code": 200, "message": "查询成功", "data": {"id": "esp32_01", "name": "水质传感器1号", "type": "water_sensor", "location": "红树林A区", "online_status": {"status": "online", "last_heartbeat": 1723593600}}}'),

    (14, 'PUT', '/api/v1/devices/{device_id}', '更新设备信息',
     '{"code": 200, "message": "更新成功", "data": {"id": "esp32_01", "name": "新名称", "location": "新位置"}}'),

    (15, 'DELETE', '/api/v1/devices/{device_id}', '删除设备',
     '{"code": 200, "message": "删除成功"}'),

    (16, 'GET', '/api/v1/video/cameras', '获取所有摄像头列表',
     '{"code": 200, "message": "查询成功", "data": [{"id": "cam_01", "name": "红树林监控1号", "rtsp_url": "rtsp://192.168.1.100:554/stream", "location": "入海口A区", "status": {"online": false, "last_heartbeat": null}}]}'),

    (17, 'GET', '/api/v1/video/cameras/{camera_id}', '获取单个摄像头信息',
     '{"code": 200, "message": "查询成功", "data": {"id": "cam_01", "name": "红树林监控1号", "rtsp_url": "rtsp://...", "location": "入海口A区", "status": {"online": false, "last_heartbeat": null}}}'),

    (18, 'POST', '/api/v1/video/cameras', '添加摄像头',
     '{"code": 200, "message": "添加成功", "data": {"id": "cam_01", "name": "红树林监控1号", "rtsp_url": "rtsp://...", "location": "入海口A区", "created_at": "2026-08-14 10:00:00"}}'),

    (19, 'PUT', '/api/v1/video/cameras/{camera_id}', '更新摄像头配置',
     '{"code": 200, "message": "更新成功", "data": {"id": "cam_01", "name": "新名称", "rtsp_url": "rtsp://..."}}'),

    (20, 'DELETE', '/api/v1/video/cameras/{camera_id}', '删除摄像头',
     '{"code": 200, "message": "删除成功"}'),

    (21, 'POST', '/api/v1/video/cameras/{camera_id}/snapshot', '获取视频快照',
     '{"code": 200, "message": "快照获取成功", "data": {"camera_id": "cam_01", "snapshot_path": "./uploads/snapshots/cam_01_20260814_100000.jpg", "timestamp": "2026-08-14 10:00:00"}}'),

    (22, 'WebSocket', '/api/v1/video/stream/{camera_id}', '视频流WebSocket代理',
     '{"camera_id": "cam_01", "timestamp": "2026-08-14T10:00:00", "status": "streaming"}'),

    (23, 'GET', '/api/v1/stats/water/quality', '水质统计(min/max/avg)',
     '{"code": 200, "message": "查询成功", "data": [{"device_id": "water_01", "time_range": "-24h", "data_count": 1440, "ph": {"min": 6.8, "max": 7.5, "avg": 7.15}, "tds": {"min": 280, "max": 350, "avg": 315}, "turbidity": {"min": 10, "max": 25, "avg": 15}, "dissolved_oxygen": {"min": 5.5, "max": 7.2, "avg": 6.4}}]}'),

    (24, 'GET', '/api/v1/stats/water/trend', '水质趋势(按时间聚合)',
     '{"code": 200, "message": "查询成功", "data": [{"time": "2026-08-14T09:00:00Z", "device_id": "water_01", "ph": 7.1, "tds": 310, "turbidity": 14, "dissolved_oxygen": 6.5, "data_count": 60}]}'),

    (25, 'GET', '/api/v1/stats/water/anomalies', '水质异常检测',
     '{"code": 200, "message": "查询成功", "data": {"total_anomalies": 3, "records": [{"time": "2026-08-14T08:00:00Z", "device_id": "water_01", "anomalies": ["pH值异常: 8.5"]}]}}'),

    (26, 'GET', '/api/v1/stats/dashboard', '仪表盘汇总(大屏展示)',
     '{"code": 200, "message": "查询成功", "data": {"update_time": "2026-08-14 10:00:00", "water_quality": {"devices_with_data": 2, "latest_readings": []}, "garbage_today": [{"garbage_type": "塑料瓶", "total_count": 15, "detect_times": 8}], "system_status": {"influxdb": "online", "mysql": "online", "mqtt": "online"}}}'),

    (27, 'GET', '/api/v1/stats/water/comparison', '水质同比对比(周/月/年)',
     '{"code": 200, "message": "查询成功", "data": {"compare_period": "week", "comparisons": [{"device_id": "water_01", "current_period": {"ph": {"avg": 7.15}}, "previous_period": {"ph_avg": 7.0}, "changes": {"ph_change": 0.15, "tds_change": 5, "turbidity_change": -2, "do_change": 0.3}}]}}'),

    (28, 'WebSocket', '/api/v1/ws', '实时数据推送(水质+垃圾)',
     '{"type": "water_quality", "data": {"device_id": "water_01", "ph": 7.2, "tds": 320}}\n{"type": "garbage_detection", "data": {"camera_id": "camera_01", "garbage_type": "塑料瓶", "count": 2}}'),

    (29, 'GET', '/api/v1/health', '健康检查',
     '{"code": 200, "status": "healthy", "timestamp": "2026-08-14 10:00:00"}'),
]

# 总览表格
table = doc.add_table(rows=len(interfaces) + 1, cols=4, style='Table Grid')
table.alignment = WD_TABLE_ALIGNMENT.CENTER

# 表头
headers = ['序号', '请求方式', '路径', '描述']
for i, h in enumerate(headers):
    cell = table.cell(0, i)
    cell.text = h
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.bold = True

# 数据行
for row_idx, (num, method, path, desc, _) in enumerate(interfaces, 1):
    table.cell(row_idx, 0).text = str(num)
    table.cell(row_idx, 1).text = method
    table.cell(row_idx, 2).text = path
    table.cell(row_idx, 3).text = desc

doc.add_paragraph('')

# ==================== 第三部分：各接口详情 ====================
doc.add_heading('三、各接口返回JSON样例', level=1)

# 按模块分组
groups = [
    ("水质数据接口", [1, 2, 3]),
    ("垃圾识别接口", [4, 5, 6, 7, 8]),
    ("设备管理接口", [9, 10, 11, 12, 13, 14, 15]),
    ("视频流代理接口", [16, 17, 18, 19, 20, 21, 22]),
    ("数据统计接口", [23, 24, 25, 26, 27]),
    ("其他接口", [28, 29]),
]

interface_map = {item[0]: item for item in interfaces}

for group_name, nums in groups:
    doc.add_heading(group_name, level=2)

    for num in nums:
        item = interface_map[num]
        _, method, path, desc, json_example = item

        # 接口标题
        p = doc.add_paragraph()
        run = p.add_run(f'{num}. {method} {path}')
        run.bold = True
        run.font.size = Pt(12)

        # 描述
        p = doc.add_paragraph()
        p.add_run(f'描述：{desc}')

        # JSON样例
        p = doc.add_paragraph()
        run = p.add_run('返回JSON样例：')
        run.bold = True

        # JSON代码块（用等宽字体）
        p = doc.add_paragraph()
        run = p.add_run(json_example)
        run.font.name = 'Consolas'
        run.font.size = Pt(9)

        doc.add_paragraph('')

# ==================== 第四部分：说明 ====================
doc.add_heading('四、补充说明', level=1)

notes = [
    '所有接口返回统一JSON格式：{"code": 状态码, "message": "描述", "data": 数据}',
    '状态码：200成功，400参数错误，404不存在，500服务器错误',
    'POST/PUT/DELETE接口的参数均为query string形式（拼在URL后面），不是JSON body',
    'POST /api/v1/garbage/detect 的 image_file 参数支持文件上传（multipart/form-data）',
    'WebSocket接口无需发送请求，连接后自动接收服务端推送的数据',
    '当前接口无需Token鉴权，前端直接调用即可',
    'Swagger在线文档地址：http://localhost:8000/docs（可在线查看和测试所有接口）',
]

for i, note in enumerate(notes, 1):
    doc.add_paragraph(f'{i}. {note}')

# ==================== 保存 ====================
output_path = r'c:\Users\joose\OneDrive\Desktop\honshu\后端API接口文档.docx'
doc.save(output_path)
print(f'文档已生成：{output_path}')
