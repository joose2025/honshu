-- ==============================================
-- 红树林垃圾识别监测系统 - MySQL数据库初始化脚本
-- 执行方式: mysql -u root -p < database_init.sql
-- ==============================================

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS mangrove_db 
DEFAULT CHARACTER SET utf8mb4 
DEFAULT COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE mangrove_db;

-- 创建垃圾识别记录表
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

-- 创建索引
CREATE INDEX idx_camera_id ON garbage_detect_record(camera_id);
CREATE INDEX idx_detect_time ON garbage_detect_record(detect_time);
CREATE INDEX idx_garbage_type ON garbage_detect_record(garbage_type);

-- 插入测试数据
INSERT INTO garbage_detect_record (camera_id, detect_time, garbage_type, count, confidence, image_path) VALUES
('camera_01', '2024-01-15 08:30:00', '塑料袋', 2, 92.5, './uploads/images/test_01.jpg'),
('camera_01', '2024-01-15 09:15:00', '塑料瓶', 1, 88.3, './uploads/images/test_02.jpg'),
('camera_02', '2024-01-15 10:00:00', '渔网', 1, 95.0, './uploads/images/test_03.jpg'),
('camera_01', '2024-01-15 11:30:00', '易拉罐', 3, 90.1, './uploads/images/test_04.jpg'),
('camera_02', '2024-01-15 14:00:00', '塑料袋', 1, 87.8, './uploads/images/test_05.jpg');

-- 查询验证
SELECT * FROM garbage_detect_record;

-- ==============================================
-- 初始化完成！
-- ==============================================
