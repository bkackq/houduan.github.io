# 反诈举报系统后端

这是一个为反诈网站在线举报模块提供后端服务的Python Flask应用。

## 功能特性

1. 举报信息提交接口
2. 文件上传处理（支持多文件）
3. 数据存储和管理
4. 请求频率限制
5. 跨域支持
6. 日志记录
7. 诈骗类型API

## 技术栈

- Python 3.7+
- Flask
- Flask-CORS
- Flask-Limiter

## 安装和运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行应用

```bash
python app.py
```

应用将在 `http://localhost:5000` 上运行。

## API 接口

### 1. 提交举报
- **URL**: `/api/report`
- **方法**: POST
- **参数**:
  - reporterName (可选): 举报人姓名
  - contactInfo (必需): 联系方式
  - fraudType (必需): 诈骗类型
  - fraudTime (必需): 诈骗时间
  - fraudAmount (可选): 涉及金额
  - fraudDescription (必需): 详细描述
  - emergencyContact (可选): 紧急联系人
  - emergencyPhone (可选): 紧急联系人电话
  - evidence (可选): 证据文件（支持多文件）
  - agreeTerms (必需): 同意条款

### 2. 获取举报列表
- **URL**: `/api/reports`
- **方法**: GET

### 3. 获取举报详情
- **URL**: `/api/report/<report_id>`
- **方法**: GET

### 4. 获取诈骗类型选项
- **URL**: `/api/fraud-types`
- **方法**: GET

### 5. 健康检查
- **URL**: `/health`
- **方法**: GET

## 目录结构

- `app.py`: 主应用文件
- `requirements.txt`: 依赖包列表
- `reports/`: 举报数据存储目录
- `fraud_reports.log`: 日志文件

## 安全特性

1. 请求频率限制（每分钟最多10次提交）
2. 文件上传安全检查
   - 文件数量限制（最多5个）
   - 文件大小限制（单个文件不超过10MB）
   - 文件类型限制（仅允许JPG, PNG, PDF, DOC, DOCX）
3. 跨域资源共享(CORS)支持
4. 敏感信息过滤
5. 日志记录

## 注意事项

1. 在生产环境中，请使用适当的WSGI服务器（如Gunicorn）部署应用
2. 修改日志配置以适应生产环境需求
3. 考虑添加身份验证和授权机制以保护API
4. 定期备份reports目录中的数据
5. 根据实际需求调整文件上传限制