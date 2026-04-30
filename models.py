from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

# 用户角色常量
ROLE_USER = 0
ROLE_ADMIN = 1
ROLE_SUPER_ADMIN = 2

# 用户模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Integer, nullable=False, default=ROLE_USER)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.String(20), unique=True)
    admin_id = db.Column(db.String(20), unique=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

# 系统配置模型
class SystemConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(50), unique=True, nullable=False)
    config_value = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(200), nullable=True)

# 上传文件模型
class UploadedFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(500))
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    word_count = db.Column(db.Integer, default=0)
    char_count = db.Column(db.Integer, default=0)
    line_count = db.Column(db.Integer, default=0)
    
    visibility = db.Column(db.String(20), nullable=False, default='all')

# 文件可见用户关联表
class FileVisibility(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('uploaded_file.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

def init_db(app):
    """初始化数据库"""
    db.init_app(app)
    with app.app_context():
        db.create_all()