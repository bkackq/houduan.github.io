from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import json
import os
import uuid
from datetime import datetime
import logging
from functools import wraps

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('fraud_reports.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 在生产环境中应该使用更安全的密钥
CORS(app, origins=["http://127.0.0.1:*", "http://localhost:*"])  # 允许跨域请求

# 限制请求频率，防止滥用
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
limiter.init_app(app)

# 管理员账户信息（在生产环境中应该存储在数据库中）
ADMIN_CREDENTIALS = {
    'username': 'admin',
    'password': 'admin123'  # 在生产环境中应该使用加密密码
}

# 确保数据目录存在（使用相对于python目录的路径）
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)

# 设置模板目录
app.template_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "templates"))

# 登录检查装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET'])
def login():
    """登录页面"""
    # 如果已经登录，重定向到管理后台
    if 'logged_in' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    """处理登录请求"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        # 验证用户名和密码
        if (username == ADMIN_CREDENTIALS['username'] and 
            password == ADMIN_CREDENTIALS['password']):
            # 登录成功，设置会话
            session['logged_in'] = True
            session['username'] = username
            logger.info(f"管理员 {username} 登录成功")
            
            return jsonify({
                "status": "success",
                "message": "登录成功"
            })
        else:
            # 登录失败
            logger.warning(f"管理员登录失败: 用户名={username}")
            return jsonify({
                "status": "error",
                "message": "用户名或密码错误"
            }), 401
            
    except Exception as e:
        logger.error(f"登录过程中出错: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "服务器内部错误"
        }), 500

@app.route('/logout')
def logout():
    """登出"""
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """管理后台首页"""
    return render_template('admin.html')

@app.route('/health')
def health_check():
    """健康检查端点"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/report', methods=['POST'])
@limiter.limit("10 per minute")
def submit_report():
    """提交诈骗举报"""
    try:
        # 获取表单数据
        data = {
            'reporter_name': request.form.get('reporterName', ''),
            'contact_info': request.form.get('contactInfo', ''),
            'fraud_type': request.form.get('fraudType', ''),
            'fraud_time': request.form.get('fraudTime', ''),
            'fraud_amount': request.form.get('fraudAmount', ''),
            'description': request.form.get('fraudDescription', ''),
            'emergency_contact': request.form.get('emergencyContact', ''),
            'emergency_phone': request.form.get('emergencyPhone', ''),
            'agree_terms': bool(request.form.get('agreeTerms'))
        }
        
        # 验证必填字段
        required_fields = ['contact_info', 'fraud_type', 'fraud_time', 'description']
        for field in required_fields:
            if not data[field]:
                return jsonify({
                    "status": "error",
                    "message": f"缺少必填字段: {field}"
                }), 400
        
        # 验证描述长度
        if len(data['description']) > 1000:
            return jsonify({
                "status": "error",
                "message": "详细描述不能超过1000个字符"
            }), 400
        
        # 验证同意条款
        if not data['agree_terms']:
            return jsonify({
                "status": "error",
                "message": "必须同意提交相关证据用于反诈调查"
            }), 400
        
        # 生成唯一报告ID
        report_id = str(uuid.uuid4())
        data['report_id'] = report_id
        data['timestamp'] = datetime.now().isoformat()
        
        # 处理上传的文件
        files = []
        if 'evidence' in request.files:
            uploaded_files = request.files.getlist('evidence')
            for file in uploaded_files:
                if file and file.filename:
                    # 检查文件数量限制
                    if len(files) >= 5:
                        break
                    
                    # 检查文件大小 (10MB限制)
                    file.seek(0, os.SEEK_END)
                    file_length = file.tell()
                    file.seek(0)
                    
                    if file_length > 10 * 1024 * 1024:
                        logger.warning(f"文件过大被拒绝: {file.filename}")
                        continue
                    
                    # 检查文件类型
                    allowed_extensions = {'.jpg', '.jpeg', '.png', '.pdf', '.doc', '.docx'}
                    _, ext = os.path.splitext(file.filename.lower())
                    if ext not in allowed_extensions:
                        logger.warning(f"不支持的文件类型: {file.filename}")
                        continue
                    
                    # 生成安全的文件名
                    filename = f"{report_id}_{file.filename}"
                    file_path = os.path.join(REPORTS_DIR, filename)
                    
                    # 确保目录存在
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    
                    file.save(file_path)
                    files.append({
                        'original_name': file.filename,
                        'saved_name': filename,
                        'size': os.path.getsize(file_path)
                    })
        
        data['files'] = files
        
        # 保存报告到JSON文件
        report_file = os.path.join(REPORTS_DIR, f"{report_id}.json")
        # 确保目录存在
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 记录日志
        logger.info(f"新举报已提交: {report_id}, 诈骗类型: {data['fraud_type']}")
        
        # 返回成功响应
        return jsonify({
            "status": "success",
            "message": "举报信息已成功提交，感谢您的贡献！",
            "report_id": report_id
        }), 201
        
    except Exception as e:
        logger.error(f"提交举报时出错: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"服务器内部错误，请稍后再试: {str(e)}"
        }), 500

@app.route('/api/reports', methods=['GET'])
def get_reports():
    """获取举报列表（仅用于演示，实际应用中需要身份验证）"""
    try:
        reports = []
        for filename in os.listdir(REPORTS_DIR):
            if filename.endswith('.json'):
                with open(os.path.join(REPORTS_DIR, filename), 'r', encoding='utf-8') as f:
                    report = json.load(f)
                    # 移除敏感信息
                    report.pop('contact_info', None)
                    report.pop('emergency_contact', None)
                    report.pop('emergency_phone', None)
                    reports.append(report)
        
        return jsonify({
            "status": "success",
            "reports": reports,
            "count": len(reports)
        })
        
    except Exception as e:
        logger.error(f"获取举报列表时出错: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "获取举报列表时出错"
        }), 500

@app.route('/api/report/<report_id>', methods=['GET'])
def get_report(report_id):
    """获取单个举报详情（仅用于演示，实际应用中需要身份验证）"""
    try:
        report_file = os.path.join(REPORTS_DIR, f"{report_id}.json")
        if not os.path.exists(report_file):
            return jsonify({
                "status": "error",
                "message": "未找到指定的举报信息"
            }), 404
            
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)
            
        # 移除敏感信息
        report.pop('contact_info', None)
        report.pop('emergency_contact', None)
        report.pop('emergency_phone', None)
        
        return jsonify({
            "status": "success",
            "report": report
        })
        
    except Exception as e:
        logger.error(f"获取举报详情时出错: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "获取举报详情时出错"
        }), 500

# 为前端提供诈骗类型选项
@app.route('/api/fraud-types', methods=['GET'])
def get_fraud_types():
    """获取诈骗类型选项"""
    fraud_types = [
        {"value": "impersonation", "label": "冒充公检法"},
        {"value": "loan", "label": "网络贷款"},
        {"value": "shopping", "label": "网购退款"},
        {"value": "partTimeJob", "label": "兼职刷单"},
        {"value": "investment", "label": "虚假投资"},
        {"value": "onlineDating", "label": "杀猪盘/网恋诈骗"},
        {"value": "phishing", "label": "钓鱼网站/链接"},
        {"value": "other", "label": "其他类型"}
    ]
    
    return jsonify({
        "status": "success",
        "fraud_types": fraud_types
    })

# 提供统计信息接口
@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    try:
        # 计算报告数量
        report_count = 0
        total_files = 0
        
        if os.path.exists(REPORTS_DIR):
            for filename in os.listdir(REPORTS_DIR):
                if filename.endswith('.json'):
                    report_count += 1
                    # 读取报告统计文件数量
                    try:
                        with open(os.path.join(REPORTS_DIR, filename), 'r', encoding='utf-8') as f:
                            report = json.load(f)
                            total_files += len(report.get('files', []))
                    except:
                        pass
        
        return jsonify({
            "status": "success",
            "stats": {
                "daily_interceptions": report_count * 20,  # 模拟数据
                "blocked_websites": report_count * 10,     # 模拟数据
                "user_satisfaction": 95,                   # 固定值
                "protection_hours": 24                     # 固定值
            }
        })
    except Exception as e:
        logger.error(f"获取统计信息时出错: {str(e)}")
        # 返回默认统计数据
        return jsonify({
            "status": "success",
            "stats": {
                "daily_interceptions": 10000,
                "blocked_websites": 5000,
                "user_satisfaction": 95,
                "protection_hours": 24
            }
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)