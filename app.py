from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from urllib.parse import quote
import os
import sys

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # 如果没有安装 dotenv，在 Railway 上会使用环境变量

# 创建Flask应用
app = Flask(__name__)

# 配置 SECRET_KEY - 使用环境变量或默认值
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret-key-for-development-only')

# 配置数据库 - 优先使用环境变量，支持 PostgreSQL 和 SQLite
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Railway 提供的 PostgreSQL URL
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace('postgres://', 'postgresql://')
else:
    # 默认使用 SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'text_analysis.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 文件上传配置
app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx', 'txt', 'md'}

# 确保目录存在
try:
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
except Exception as e:
    print(f"Error creating directories: {e}", file=sys.stderr)

# CORS配置
CORS(app, resources={r"/user/book/analyze/*": {"origins": "*"}})

# 延迟导入 AI 服务，先确保基本功能正常
try:
    from ai_service import AIService
    ai_service = AIService()
except Exception as e:
    print(f"Warning: AI service initialization failed: {e}", file=sys.stderr)
    ai_service = None

# 导入模型
from models import db, User, SystemConfig, UploadedFile, FileVisibility, ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN

# 初始化数据库
db.init_app(app)

# 初始化登录管理器
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# 登录管理器回调函数
@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        print(f"Error loading user: {e}", file=sys.stderr)
        return None

# 检查文件扩展名是否允许
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# 获取文件类型
def get_file_type(filename):
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return 'unknown'

# 计算文件统计信息
def calculate_file_stats(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.splitlines()
            line_count = len(lines)
            char_count = len(content)
            word_count = len(content.split())
        return {'lines': line_count, 'chars': char_count, 'words': word_count}
    except Exception as e:
        print(f"Error calculating file stats: {e}", file=sys.stderr)
        return {'lines': 0, 'chars': 0, 'words': 0}

# 检查用户是否有权限访问文件
def has_file_access(file_id, user_id):
    try:
        file = UploadedFile.query.get(file_id)
        if not file:
            return False
        # 超级管理员和管理员可以访问所有文件
        user = User.query.get(user_id)
        if user.role in [ROLE_ADMIN, ROLE_SUPER_ADMIN]:
            return True
        # 检查文件是否对用户可见
        visibility = FileVisibility.query.filter_by(file_id=file_id, user_id=user_id).first()
        return visibility is not None
    except Exception as e:
        print(f"Error checking file access: {e}", file=sys.stderr)
        return False

# 读取文件内容
def read_file_content(file_path):
    try:
        if not os.path.exists(file_path):
            return None
        
        file_ext = get_file_type(file_path).lower()
        
        if file_ext == 'pdf':
            try:
                from PyPDF2 import PdfReader
                text_content = []
                with open(file_path, 'rb') as f:
                    pdf_reader = PdfReader(f)
                    for page in pdf_reader.pages:
                        text = page.extract_text()
                        if text:
                            text_content.append(text)
                return '\n'.join(text_content)
            except Exception as e:
                print(f"Error reading PDF: {e}", file=sys.stderr)
                return None
        
        elif file_ext in ['doc', 'docx']:
            try:
                from docx import Document
                doc = Document(file_path)
                return '\n'.join([para.text for para in doc.paragraphs])
            except Exception as e:
                print(f"Error reading Word: {e}", file=sys.stderr)
                return None
        
        else:
            # 文本文件
            encodings = ['utf-8', 'gbk', 'gb2312', 'cp1252']
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            return None
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return None

# 生成响应
def generate_response(content, question):
    global ai_service
    if ai_service is None:
        return "AI服务未初始化，请检查配置。"
    
    try:
        return ai_service.generate_response(content, question)
    except Exception as e:
        print(f"Error generating response: {e}", file=sys.stderr)
        return f"生成回答时出错：{str(e)}"

# 登录页面
@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            
            # 查找用户
            user = User.query.filter_by(username=username).first()
            
            # 密码验证
            if user and check_password_hash(user.password, password):
                login_user(user)
                flash('登录成功！', 'success')
                
                # 根据用户角色重定向
                if user.role == ROLE_SUPER_ADMIN:
                    return redirect(url_for('super_admin_dashboard'))
                elif user.role == ROLE_ADMIN:
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('user_dashboard'))
            else:
                flash('用户名或密码错误！', 'danger')
        return render_template('login.html')
    except Exception as e:
        print(f"Error in login: {e}", file=sys.stderr)
        flash('登录时出现错误，请稍后重试。', 'danger')
        return render_template('login.html')

# 登出功能
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已成功登出！', 'success')
    return redirect(url_for('login'))