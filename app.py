from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from ai_service import AIService
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from urllib.parse import quote
import os

# 创建Flask应用
app = Flask(__name__)
CORS(app, resources={r"/user/book/analyze/*": {"origins": "*"}})
app.config['SECRET_KEY'] = 'your-secret-key'
# 使用绝对路径指向实际数据库文件
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'text_analysis.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# 文件上传配置
app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx', 'txt', 'md'}

# 确保目录存在
os.makedirs(app.instance_path, exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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
    return User.query.get(int(user_id))

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
            # 简单的中文和英文单词计数
            words = []
            for line in lines:
                # 按空白字符分割
                parts = line.split()
                for part in parts:
                    # 检测是否包含中文字符
                    if any('\u4e00' <= c <= '\u9fff' for c in part):
                        # 中文字符按字符计数
                        words.extend(list(part))
                    else:
                        # 英文按单词计数
                        words.append(part)
            word_count = len(words)
        return word_count, char_count, line_count
    except Exception as e:
        return 0, 0, 0

# 登录页面
@app.route('/login', methods=['GET', 'POST'])
def login():
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

# 登出功能
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已成功登出！', 'success')
    return redirect(url_for('login'))

# 用户端首页
@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if current_user.role != ROLE_USER:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    # 获取用户可见的文件统计
    visible_file_ids = db.session.query(FileVisibility.file_id).filter(FileVisibility.user_id == current_user.id).subquery()
    
    # 统计用户可见的所有文件
    total_files = UploadedFile.query.filter(
        (UploadedFile.visibility == 'all') | 
        (UploadedFile.id.in_(visible_file_ids))
    ).count()
    
    # 统计PDF文件数量
    pdf_count = UploadedFile.query.filter(
        UploadedFile.file_type == 'pdf',
        ((UploadedFile.visibility == 'all') | 
        (UploadedFile.id.in_(visible_file_ids)))
    ).count()
    
    # 统计Word文件数量（doc和docx）
    doc_count = UploadedFile.query.filter(
        UploadedFile.file_type.in_(['doc', 'docx']),
        ((UploadedFile.visibility == 'all') | 
        (UploadedFile.id.in_(visible_file_ids)))
    ).count()
    
    # 统计文本文件数量（txt和md）
    text_count = UploadedFile.query.filter(
        UploadedFile.file_type.in_(['txt', 'md']),
        ((UploadedFile.visibility == 'all') | 
        (UploadedFile.id.in_(visible_file_ids)))
    ).count()
    
    return render_template('user/dashboard.html', 
                           total_files=total_files,
                           pdf_count=pdf_count,
                           doc_count=doc_count,
                           text_count=text_count)

# 用户端文件列表页面
@app.route('/user/files')
@login_required
def user_files():
    if current_user.role != ROLE_USER:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    # 获取搜索关键词
    search_query = request.args.get('search', '')
    
    # 用户只能看到：
    # 1. 所有设置为"全部可见"的文件
    # 2. 设置为"指定用户可见"且该用户在可见列表中的文件
    visible_file_ids = db.session.query(FileVisibility.file_id).filter(FileVisibility.user_id == current_user.id).subquery()
    
    # 构建查询
    query = UploadedFile.query.filter(
        (UploadedFile.visibility == 'all') | 
        (UploadedFile.id.in_(visible_file_ids))
    )
    
    # 如果有搜索关键词，添加搜索条件
    if search_query:
        query = query.filter(
            (UploadedFile.original_filename.ilike(f'%{search_query}%')) | 
            (UploadedFile.description.ilike(f'%{search_query}%')) |
            (UploadedFile.file_type.ilike(f'%{search_query}%'))
        )
    
    # 执行查询
    files = query.order_by(UploadedFile.upload_date.desc()).all()
    return render_template('user/files.html', files=files, search_query=search_query)

# 检查用户是否有权限访问文件
def has_file_access(file_id, user_id):
    file = UploadedFile.query.get(file_id)
    if not file:
        return False
    
    # 如果文件设置为全部可见，所有用户都可以访问
    if file.visibility == 'all':
        return True
    
    # 如果文件设置为指定用户可见，检查该用户是否在可见列表中
    if file.visibility == 'specific':
        visibility = FileVisibility.query.filter_by(file_id=file_id, user_id=user_id).first()
        return visibility is not None
    
    return False

# 用户端预览文件
@app.route('/user/preview/<int:file_id>')
@login_required
def user_file_preview(file_id):
    if current_user.role != ROLE_USER:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    if not has_file_access(file_id, current_user.id):
        flash('您没有权限访问该文件！', 'danger')
        return redirect(url_for('user_files'))
    
    file = UploadedFile.query.get_or_404(file_id)
    
    file_content = ''
    if file.file_type in ['txt', 'md']:
        try:
            # 尝试多种编码读取文件
            encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'utf-16']
            file_content = ''
            for encoding in encodings:
                try:
                    with open(file.file_path, 'r', encoding=encoding) as f:
                        file_content = f.read()
                        break
                except:
                    continue
            
            if not file_content:
                file_content = '无法识别文件编码，无法预览'
        except Exception as e:
            file_content = f'读取文件内容失败: {str(e)}'
    elif file.file_type in ['doc', 'docx']:
        try:
            from docx import Document
            doc = Document(file.file_path)
            file_content = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            if not file_content:
                file_content = '文档内容为空'
        except Exception as e:
            file_content = f'读取Word文档失败: {str(e)}'
    
    return render_template('user/file_preview.html', file=file, file_content=file_content)

# 用户端查看文件详情
@app.route('/user/files/<int:file_id>')
@login_required
def user_file_detail(file_id):
    if current_user.role != ROLE_USER:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    if not has_file_access(file_id, current_user.id):
        flash('您没有权限访问该文件！', 'danger')
        return redirect(url_for('user_files'))
    
    file = UploadedFile.query.get_or_404(file_id)
    return render_template('user/file_detail.html', file=file)

# 用户端下载文件
@app.route('/user/download/<int:file_id>')
@login_required
def user_download_file(file_id):
    if current_user.role != ROLE_USER:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    # 检查是否有权限访问该文件
    if not has_file_access(file_id, current_user.id):
        flash('您没有权限下载该文件！', 'danger')
        return redirect(url_for('user_files'))
    
    file = UploadedFile.query.get_or_404(file_id)
    
    # 确保文件名带有正确的后缀
    original_name = file.original_filename
    _, ext = os.path.splitext(original_name)
    
    # 如果原始文件名没有后缀，根据文件类型添加后缀
    if not ext:
        ext_map = {
            'pdf': '.pdf',
            'doc': '.doc',
            'docx': '.docx',
            'txt': '.txt',
            'md': '.md'
        }
        ext = ext_map.get(file.file_type, '.bin')
        original_name = original_name + ext
    
    # 设置正确的Content-Type
    content_type_map = {
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'txt': 'text/plain; charset=utf-8',
        'md': 'text/markdown; charset=utf-8'
    }
    content_type = content_type_map.get(file.file_type, 'application/octet-stream')
    
    # 使用send_file确保正确的文件名和内容类型
    response = send_from_directory(
        os.path.dirname(file.file_path), 
        os.path.basename(file.file_path),
        as_attachment=True,
        download_name=original_name,
        mimetype=content_type
    )
    
    # 处理中文文件名编码
    response.headers['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{quote(original_name)}'
    
    return response

# 管理端首页
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != ROLE_ADMIN and current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    # 统计信息
    total_files = UploadedFile.query.count()
    total_users = User.query.filter_by(role=ROLE_USER).count()
    total_admins = User.query.filter((User.role == ROLE_ADMIN) | (User.role == ROLE_SUPER_ADMIN)).count()
    today_uploads = UploadedFile.query.filter(db.func.date(UploadedFile.upload_date)==datetime.now().date()).count()
    
    return render_template('admin/dashboard.html', total_files=total_files, total_users=total_users, 
                          total_admins=total_admins, today_uploads=today_uploads)

# 管理端文件管理页面
@app.route('/admin/files')
@login_required
def admin_manage_files():
    if current_user.role != ROLE_ADMIN and current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    # 获取搜索关键词
    search_query = request.args.get('search', '')
    
    # 构建查询
    query = UploadedFile.query
    
    # 如果有搜索关键词，添加搜索条件
    if search_query:
        query = query.filter(
            (UploadedFile.original_filename.ilike(f'%{search_query}%')) | 
            (UploadedFile.description.ilike(f'%{search_query}%')) |
            (UploadedFile.file_type.ilike(f'%{search_query}%'))
        )
    
    # 执行查询
    files = query.order_by(UploadedFile.upload_date.desc()).all()
    return render_template('admin/files.html', files=files, search_query=search_query)

# 管理端上传文件页面
@app.route('/admin/files/upload', methods=['GET', 'POST'])
@login_required
def admin_upload_file():
    if current_user.role != ROLE_ADMIN and current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    # 获取当前管理员创建的用户列表（用于可见性设置）
    if current_user.role == ROLE_SUPER_ADMIN:
        available_users = User.query.filter_by(role=ROLE_USER).all()
    else:
        available_users = User.query.filter_by(role=ROLE_USER, created_by=current_user.id).all()
    
    if request.method == 'POST':
        # 检查是否有文件被上传
        if 'file' not in request.files:
            flash('没有选择文件！', 'danger')
            return redirect(url_for('admin_upload_file'))
        
        file = request.files['file']
        
        # 如果用户没有选择文件
        if file.filename == '':
            flash('没有选择文件！', 'danger')
            return redirect(url_for('admin_upload_file'))
        
        # 检查文件类型
        if file and allowed_file(file.filename):
            # 安全处理文件名
            original_filename = file.filename
            filename = secure_filename(file.filename)
            
            # 确保文件名唯一
            base_name, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
                filename = f"{base_name}_{counter}{ext}"
                counter += 1
            
            # 保存文件
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            
            # 获取文件类型：优先使用用户手动选择的类型，否则自动识别
            selected_file_type = request.form.get('file_type', '')
            if selected_file_type and selected_file_type in ['pdf', 'doc', 'docx', 'txt', 'md']:
                file_type = selected_file_type
            else:
                file_type = get_file_type(filename)
            
            # 获取文件描述
            description = request.form.get('description', '')
            
            # 获取可见性设置
            visibility = request.form.get('visibility', 'all')
            
            # 计算文件统计信息（仅对文本文件）
            if file_type in ['txt', 'md']:
                word_count, char_count, line_count = calculate_file_stats(file_path)
            else:
                word_count, char_count, line_count = 0, 0, 0
            
            # 创建文件记录
            new_file = UploadedFile(
                filename=filename,
                original_filename=original_filename,
                file_path=file_path,
                file_type=file_type,
                size=file_size,
                description=description,
                uploader_id=current_user.id,
                word_count=word_count,
                char_count=char_count,
                line_count=line_count,
                visibility=visibility
            )
            
            # 保存到数据库
            db.session.add(new_file)
            db.session.commit()
            
            # 如果设置为指定用户可见，保存关联关系
            if visibility == 'specific':
                selected_users = request.form.getlist('visible_users')
                for user_id in selected_users:
                    file_visibility = FileVisibility(
                        file_id=new_file.id,
                        user_id=int(user_id)
                    )
                    db.session.add(file_visibility)
                db.session.commit()
            
            flash(f'文件 "{original_filename}" 上传成功！文件类型：{file_type}', 'success')
            return redirect(url_for('admin_manage_files'))
        else:
            flash('不支持的文件类型！支持的类型：pdf, doc, docx, txt, md', 'danger')
            return redirect(url_for('admin_upload_file'))
    
    return render_template('admin/upload_file.html', available_users=available_users)

# 管理端删除文件操作
@app.route('/admin/files/delete/<int:file_id>', methods=['POST'])
@login_required
def admin_delete_file(file_id):
    if current_user.role != ROLE_ADMIN and current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    file = UploadedFile.query.get_or_404(file_id)
    
    # 删除物理文件
    if os.path.exists(file.file_path):
        os.remove(file.file_path)
    
    # 删除数据库记录
    db.session.delete(file)
    db.session.commit()
    
    flash('文件删除成功！', 'success')
    return redirect(url_for('admin_manage_files'))

# 管理端用户管理页面
@app.route('/admin/users')
@login_required
def admin_manage_users():
    if current_user.role != ROLE_ADMIN and current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    # 普通管理员只能看到自己创建的用户，超级管理员可以看到所有用户
    if current_user.role == ROLE_SUPER_ADMIN:
        users = User.query.filter_by(role=ROLE_USER).all()
    else:
        users = User.query.filter_by(role=ROLE_USER, created_by=current_user.id).all()
    
    return render_template('admin/users.html', users=users)

# 管理端添加用户页面
@app.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
def admin_add_user():
    if current_user.role != ROLE_ADMIN and current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        user_id = request.form['user_id']
        username = request.form['username']
        password = request.form['password']
        
        # 检查用户名是否已存在
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('用户名已存在！', 'danger')
            return redirect(url_for('admin_add_user'))
        
        # 检查用户ID是否已存在
        existing_uid = User.query.filter_by(user_id=user_id).first()
        if existing_uid:
            flash('用户ID已存在！', 'danger')
            return redirect(url_for('admin_add_user'))
        
        # 创建新用户，记录创建者
        new_user = User(
            name=name,
            user_id=user_id,
            username=username,
            password=generate_password_hash(password),
            role=ROLE_USER,
            created_by=current_user.id  # 记录创建者
        )
        
        # 保存到数据库
        db.session.add(new_user)
        db.session.commit()
        
        flash('用户添加成功！', 'success')
        return redirect(url_for('admin_manage_users'))
    
    return render_template('admin/add_user.html')

# 管理端删除用户
@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.role != ROLE_ADMIN and current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    user_to_delete = User.query.get_or_404(user_id)
    
    if user_to_delete.role == ROLE_ADMIN or user_to_delete.role == ROLE_SUPER_ADMIN:
        flash('不能删除管理员账户！', 'danger')
        return redirect(url_for('admin_manage_users'))
    
    if current_user.role == ROLE_ADMIN and user_to_delete.created_by != current_user.id:
        flash('您只能删除自己创建的用户！', 'danger')
        return redirect(url_for('admin_manage_users'))
    
    try:
        file_visibilities = FileVisibility.query.filter_by(user_id=user_id).all()
        for fv in file_visibilities:
            db.session.delete(fv)
        
        user_files = UploadedFile.query.filter_by(uploader_id=user_id).all()
        for uf in user_files:
            visibility_records = FileVisibility.query.filter_by(file_id=uf.id).all()
            for vr in visibility_records:
                db.session.delete(vr)
            
            if os.path.exists(uf.file_path):
                os.remove(uf.file_path)
            db.session.delete(uf)
        
        db.session.delete(user_to_delete)
        db.session.commit()
        
        flash(f'用户 {user_to_delete.username} 已删除，相关文件也已清除！', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}', 'danger')
    
    return redirect(url_for('admin_manage_users'))

# 超级管理员端首页
@app.route('/super_admin/dashboard')
@login_required
def super_admin_dashboard():
    if current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    # 统计信息
    total_admins = User.query.filter((User.role == ROLE_ADMIN) | (User.role == ROLE_SUPER_ADMIN)).count()
    total_users = User.query.filter_by(role=ROLE_USER).count()
    total_files = UploadedFile.query.count()
    
    return render_template('super_admin/dashboard.html', total_admins=total_admins, total_users=total_users, total_files=total_files)

# 超级管理员端管理员管理页面
@app.route('/super_admin/admins')
@login_required
def super_admin_manage_admins():
    if current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    admins = User.query.filter((User.role == ROLE_ADMIN) | (User.role == ROLE_SUPER_ADMIN)).all()
    return render_template('super_admin/admins.html', admins=admins)

# 超级管理员端添加管理员页面
@app.route('/super_admin/admins/add', methods=['GET', 'POST'])
@login_required
def super_admin_add_admin():
    if current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        admin_id = request.form['admin_id']
        username = request.form['username']
        password = request.form['password']
        
        # 检查用户名是否已存在
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('用户名已存在！', 'danger')
            return redirect(url_for('super_admin_add_admin'))
        
        # 检查管理员ID是否已存在
        existing_admin = User.query.filter_by(admin_id=admin_id).first()
        if existing_admin:
            flash('管理员ID已存在！', 'danger')
            return redirect(url_for('super_admin_add_admin'))
        
        # 创建新管理员
        new_admin = User(
            name=name,
            admin_id=admin_id,
            username=username,
            password=generate_password_hash(password),
            role=ROLE_ADMIN
        )
        
        # 保存到数据库
        db.session.add(new_admin)
        db.session.commit()
        
        flash('管理员添加成功！', 'success')
        return redirect(url_for('super_admin_manage_admins'))
    
    return render_template('super_admin/add_admin.html')

# 超级管理员端数据统计页面
@app.route('/super_admin/statistics')
@login_required
def super_admin_statistics():
    if current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    # 统计信息
    total_files = UploadedFile.query.count()
    total_users = User.query.filter_by(role=ROLE_USER).count()
    total_admins = User.query.filter((User.role == ROLE_ADMIN) | (User.role == ROLE_SUPER_ADMIN)).count()
    
    # 按文件类型统计
    pdf_count = UploadedFile.query.filter_by(file_type='pdf').count()
    doc_count = UploadedFile.query.filter_by(file_type='doc').count()
    docx_count = UploadedFile.query.filter_by(file_type='docx').count()
    txt_count = UploadedFile.query.filter_by(file_type='txt').count()
    md_count = UploadedFile.query.filter_by(file_type='md').count()
    
    # 总文件大小
    total_size = db.session.query(db.func.sum(UploadedFile.size)).scalar() or 0
    
    # 文本文件统计信息
    total_word_count = db.session.query(db.func.sum(UploadedFile.word_count)).scalar() or 0
    total_char_count = db.session.query(db.func.sum(UploadedFile.char_count)).scalar() or 0
    total_line_count = db.session.query(db.func.sum(UploadedFile.line_count)).scalar() or 0
    
    return render_template('super_admin/statistics.html', 
                          total_files=total_files,
                          total_users=total_users, 
                          total_admins=total_admins,
                          pdf_count=pdf_count,
                          doc_count=doc_count,
                          docx_count=docx_count,
                          txt_count=txt_count,
                          md_count=md_count,
                          total_size=total_size,
                          total_word_count=total_word_count,
                          total_char_count=total_char_count,
                          total_line_count=total_line_count)

# 超级管理员端系统配置页面
@app.route('/super_admin/system_config', methods=['GET', 'POST'])
@login_required
def super_admin_system_config():
    if current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    # 获取所有系统配置
    configs = SystemConfig.query.all()
    
    if request.method == 'POST':
        # 更新系统配置
        for config in configs:
            if config.config_key in request.form:
                config.config_value = request.form[config.config_key]
        
        # 提交更改到数据库
        db.session.commit()
        flash('系统配置已更新！', 'success')
        return redirect(url_for('super_admin_system_config'))
    
    # 创建配置字典，方便模板使用
    config_dict = {}
    for config in configs:
        config_dict[config.config_key] = config.config_value
    
    return render_template('super_admin/system_config.html', configs=configs, config_dict=config_dict)

# 初始化数据库和创建示例数据
def create_tables():
    with app.app_context():
        db.create_all()
        
        # 检查是否已有超级管理员
        if not User.query.filter_by(role=ROLE_SUPER_ADMIN).first():
            # 创建超级管理员
            super_admin = User(
                username='admin001',
                password=generate_password_hash('admin001'),
                role=ROLE_SUPER_ADMIN,
                name='系统管理员',
                admin_id='admin001'
            )
            db.session.add(super_admin)
            
            # 创建普通管理员
            admin = User(
                username='admin002',
                password=generate_password_hash('admin002'),
                role=ROLE_ADMIN,
                name='文件管理员',
                admin_id='admin002'
            )
            db.session.add(admin)
            
            # 创建普通用户
            user = User(
                username='user001',
                password=generate_password_hash('user001'),
                role=ROLE_USER,
                name='张三',
                user_id='2021001'
            )
            db.session.add(user)
        
        # 添加默认系统配置
        default_configs = [
            {'config_key': 'primary_color', 'config_value': '#007bff', 'description': '主色调'}, 
            {'config_key': 'secondary_color', 'config_value': '#6c757d', 'description': '次要色调'},
            {'config_key': 'success_color', 'config_value': '#28a745', 'description': '成功色调'},
            {'config_key': 'danger_color', 'config_value': '#dc3545', 'description': '危险色调'},
            {'config_key': 'warning_color', 'config_value': '#ffc107', 'description': '警告色调'},
            {'config_key': 'info_color', 'config_value': '#17a2b8', 'description': '信息色调'},
            {'config_key': 'system_name', 'config_value': '知境文本分析系统', 'description': '系统名称'}
        ]
        
        for config in default_configs:
            existing_config = SystemConfig.query.filter_by(config_key=config['config_key']).first()
            if not existing_config:
                new_config = SystemConfig(
                    config_key=config['config_key'],
                    config_value=config['config_value'],
                    description=config['description']
                )
                db.session.add(new_config)
        
        db.session.commit()
        
        # 添加示例文件（创建一个示例txt文件）
        if not UploadedFile.query.first():
            sample_content = """这是一个知境文本分析系统的示例文档。

系统功能：
1. 文件上传与管理
2. 文件统计分析
3. 文本内容分析
4. 用户权限管理

支持的文件类型：
- PDF文档
- Word文档（.doc, .docx）
- 文本文件（.txt）
- Markdown文件（.md）

系统特点：
- 支持多用户角色
- 安全的文件存储
- 详细的统计信息
- 友好的用户界面"""
            
            sample_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'sample.txt')
            with open(sample_file_path, 'w', encoding='utf-8') as f:
                f.write(sample_content)
            
            word_count, char_count, line_count = calculate_file_stats(sample_file_path)
            
            sample_file = UploadedFile(
                filename='sample.txt',
                original_filename='sample.txt',
                file_path=sample_file_path,
                file_type='txt',
                size=os.path.getsize(sample_file_path),
                description='文本分析系统示例文档',
                uploader_id=1,
                word_count=word_count,
                char_count=char_count,
                line_count=line_count
            )
            db.session.add(sample_file)
            db.session.commit()

# 根路由，重定向到登录页面
@app.route('/')
def index():
    return redirect(url_for('login'))

# 获取系统配置的JSON数据
@app.route('/api/system_config')
def get_system_config():
    # 获取所有系统配置
    configs = SystemConfig.query.all()
    # 转换为字典
    config_dict = {}
    for config in configs:
        config_dict[config.config_key] = config.config_value
    return config_dict

# 404错误处理
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# AI搜索分析路由

from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

ai_service = AIService()

def read_file_content(file_path):
    file_path = file_path.replace('\\', '/')

    if not os.path.exists(file_path):
        return f'文件不存在：{file_path}'

    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return '文件为空'

    file_ext = os.path.splitext(file_path)[1].lower()

    if file_ext == '.pdf':
        try:
            import PyPDF2
            text_content = []
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
            if text_content:
                return '\n'.join(text_content)
        except Exception as pdf_error:
            print(f"PDF read error: {pdf_error}")
            return f'无法读取PDF文件：{str(pdf_error)}'

    encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'utf-16']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
                if content.strip():
                    return content
        except:
            continue

    if file_ext in ['.doc', '.docx']:
        try:
            from docx import Document
            doc = Document(file_path)
            full_text = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    full_text.append(paragraph.text)
            if full_text:
                return '\n'.join(full_text)
            return '文档内容为空'
        except ImportError:
            return '无法读取Word文档：缺少python-docx库'
        except Exception as docx_error:
            return f'无法读取Word文档：{str(docx_error)}'

    return '无法读取文件内容'

def has_file_access(file_id, user_id):
    file = UploadedFile.query.get(file_id)
    if not file:
        return False
    if file.visibility == 'all':
        return True
    if file.visibility == 'specific':
        visibility = FileVisibility.query.filter_by(file_id=file_id, user_id=user_id).first()
        return visibility is not None
    return False

@app.route('/user/search')
@login_required
def user_search():
    if current_user.role != ROLE_USER:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    return render_template('user/search.html')

@app.route('/user/book/analyze/<int:file_id>', methods=['GET', 'POST'])
@login_required
def user_book_analyze(file_id):
    from flask import jsonify
    
    if current_user.role != ROLE_USER:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    if not has_file_access(file_id, current_user.id):
        flash('您没有权限访问该文件！', 'danger')
        return redirect(url_for('user_files'))
    
    file = UploadedFile.query.get_or_404(file_id)
    
    if request.method == 'POST':
        try:
            question = request.form.get('question', '').strip()
            if not question:
                return jsonify({"response": "请输入您的问题"})
            
            content = read_file_content(file.file_path)
            
            if not content or content.startswith('无法读取') or content.startswith('读取失败'):
                return jsonify({"response": "无法读取文件内容，请检查文件是否存在或格式是否正确。"})
            
            prompt = f"""根据以下书籍内容回答问题：

书籍内容：
{content[:5000]}

问题：{question}

请基于书籍内容给出详细的回答，如果书籍中没有相关信息，请说明。
"""
            answer = ai_service.generate_response(prompt, max_tokens=2000)
            return jsonify({"response": answer})
            
        except Exception as e:
            print(f"Error in user_book_analyze: {str(e)}")
            return jsonify({"response": f"处理请求时发生错误: {str(e)}"})
    
    return render_template('user/book_analyze.html', file=file, file_id=file_id)

@app.route('/user/search/query', methods=['POST'])
@login_required
def user_global_search():
    if current_user.role != ROLE_USER:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    query = request.form.get('query', '')
    search_results = []
    
    if query:
        try:
            prompt = f"""请回答以下问题：
            {query}
            """
            result = ai_service.generate_response(prompt, max_tokens=2000)
            search_results.append({
                'source': 'AI助手',
                'content': result
            })
        except Exception as e:
            print(f"Search error: {str(e)}")
            search_results.append({
                'source': 'AI助手',
                'content': f'搜索出错: {str(e)}'
            })
    
    return render_template('user/search_results.html', 
                           query=query, 
                           results=search_results)

@app.route('/admin/ai_settings', methods=['GET', 'POST'])
@login_required
def admin_ai_settings():
    if current_user.role not in [ROLE_ADMIN, ROLE_SUPER_ADMIN]:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        import os
        env_path = '.env'
        env_content = f'''# AI服务配置
ALIYUN_ACCESS_KEY_ID={request.form.get('aliyun_access_key_id', '')}
ALIYUN_ACCESS_KEY_SECRET={request.form.get('aliyun_access_key_secret', '')}
ALIYUN_API_ENDPOINT=dashscope.cn-beijing.aliyuncs.com
OPENAI_API_KEY={request.form.get('openai_api_key', '')}
OPENAI_API_BASE=https://api.openai.com/v1
DEFAULT_AI_SERVICE={request.form.get('ai_service', 'openai')}
ALIYUN_MODEL=qwen-plus
OPENAI_MODEL=gpt-3.5-turbo
ENCRYPTION_KEY=text_analysis_system_key_2026
'''
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        flash('AI配置已更新！', 'success')
        return redirect(url_for('admin_ai_settings'))
    
    import os
    config = {
        'aliyun_access_key_id': os.getenv('ALIYUN_ACCESS_KEY_ID', ''),
        'aliyun_access_key_secret': os.getenv('ALIYUN_ACCESS_KEY_SECRET', ''),
        'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
        'ai_service': os.getenv('DEFAULT_AI_SERVICE', 'openai')
    }
    
    return render_template('admin/ai_settings.html', config=config)

# 应用启动时调用初始化函数
if __name__ == '__main__':
    create_tables()
    app.run(debug=True)