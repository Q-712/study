from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
# 使用绝对路径指向实际数据库文件
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'library.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# 确保instance目录存在
os.makedirs(app.instance_path, exist_ok=True)

# 初始化数据库
db = SQLAlchemy(app)

# 初始化登录管理器
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# 用户角色常量
ROLE_READER = 0
ROLE_ADMIN = 1
ROLE_SUPER_ADMIN = 2

# 用户模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Integer, nullable=False, default=ROLE_READER)
    name = db.Column(db.String(100), nullable=False)
    reader_id = db.Column(db.String(20), unique=True)
    admin_id = db.Column(db.String(20), unique=True)
    borrowed_items = db.relationship('BorrowRecord', backref='reader', lazy=True)

# 系统配置模型
class SystemConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(50), unique=True, nullable=False)
    config_value = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(200), nullable=True)

# 出版物模型
class Publication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), unique=True, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'book' or 'magazine'
    author = db.Column(db.String(100))
    isbn = db.Column(db.String(50))
    category = db.Column(db.String(100))
    issue = db.Column(db.String(50))
    publisher = db.Column(db.String(100))
    is_latest = db.Column(db.Boolean, default=False)
    is_borrowed = db.Column(db.Boolean, default=False)
    max_loan_days = db.Column(db.Integer, nullable=False)
    borrow_records = db.relationship('BorrowRecord', backref='publication', lazy=True)

# 借阅记录模型
class BorrowRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    publication_id = db.Column(db.Integer, db.ForeignKey('publication.id'), nullable=False)
    borrow_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    due_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime)

# 登录管理器回调函数
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
                return redirect(url_for('reader_dashboard'))
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

# 学生端首页
@app.route('/reader/dashboard')
@login_required
def reader_dashboard():
    if current_user.role != ROLE_READER:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    return render_template('reader/dashboard.html')

# 学生端借阅图书页面
@app.route('/reader/borrow')
@login_required
def reader_borrow_books():
    if current_user.role != ROLE_READER:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    # 获取搜索关键词
    search_query = request.args.get('search', '')
    
    # 构建查询
    query = Publication.query.filter_by(is_borrowed=False)
    
    # 如果有搜索关键词，添加搜索条件
    if search_query:
        query = query.filter(
            (Publication.title.ilike(f'%{search_query}%')) | 
            (Publication.author.ilike(f'%{search_query}%')) | 
            (Publication.category.ilike(f'%{search_query}%')) |
            (Publication.isbn.ilike(f'%{search_query}%'))
        )
    
    # 执行查询
    available_books = query.all()
    return render_template('reader/borrow.html', books=available_books, search_query=search_query)

# 学生端借阅图书操作
@app.route('/reader/borrow/<int:book_id>', methods=['POST'])
@login_required
def reader_borrow_book(book_id):
    if current_user.role != ROLE_READER:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    book = Publication.query.get_or_404(book_id)
    if book.is_borrowed:
        flash('该书已被借阅！', 'danger')
        return redirect(url_for('reader_borrow_books'))
    
    # 创建借阅记录
    borrow_record = BorrowRecord(
        reader_id=current_user.id,
        publication_id=book.id,
        borrow_date=datetime.now(),
        due_date=datetime.now() + timedelta(days=book.max_loan_days)
    )
    
    # 更新图书状态
    book.is_borrowed = True
    
    # 保存到数据库
    db.session.add(borrow_record)
    db.session.commit()
    
    flash(f'成功借阅《{book.title}》，应归还日期：{borrow_record.due_date.strftime("%Y-%m-%d")}', 'success')
    return redirect(url_for('reader_borrow_books'))

# 学生端归还图书页面
@app.route('/reader/return')
@login_required
def reader_return_books():
    if current_user.role != ROLE_READER:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    # 获取当前用户的未归还借阅记录
    borrow_records = BorrowRecord.query.filter_by(reader_id=current_user.id, return_date=None).all()
    return render_template('reader/return.html', records=borrow_records)

# 学生端归还图书操作
@app.route('/reader/return/<int:record_id>')
@login_required
def reader_return_book(record_id):
    if current_user.role != ROLE_READER:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    record = BorrowRecord.query.get_or_404(record_id)
    if record.reader_id != current_user.id:
        flash('您没有权限归还该图书！', 'danger')
        return redirect(url_for('reader_return_books'))
    
    # 更新借阅记录
    record.return_date = datetime.now()
    
    # 更新图书状态
    book = Publication.query.get_or_404(record.publication_id)
    book.is_borrowed = False
    
    # 保存到数据库
    db.session.commit()
    
    flash(f'成功归还《{book.title}》', 'success')
    return redirect(url_for('reader_return_books'))

# 学生端借阅历史页面
@app.route('/reader/history')
@login_required
def reader_borrow_history():
    if current_user.role != ROLE_READER:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    # 获取当前用户的所有借阅记录
    borrow_records = BorrowRecord.query.filter_by(reader_id=current_user.id).order_by(BorrowRecord.borrow_date.desc()).all()
    return render_template('reader/history.html', records=borrow_records)

# 管理端首页
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != ROLE_ADMIN and current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    # 统计信息
    total_books = Publication.query.count()
    total_readers = User.query.filter_by(role=ROLE_READER).count()
    borrowed_books = Publication.query.filter_by(is_borrowed=True).count()
    today_borrows = BorrowRecord.query.filter(BorrowRecord.return_date==None, db.func.date(BorrowRecord.borrow_date)==datetime.now().date()).count()
    
    return render_template('admin/dashboard.html', total_books=total_books, total_readers=total_readers, 
                          borrowed_books=borrowed_books, today_borrows=today_borrows)

# 管理端图书管理页面
@app.route('/admin/books')
@login_required
def admin_manage_books():
    if current_user.role != ROLE_ADMIN and current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    # 获取搜索关键词
    search_query = request.args.get('search', '')
    
    # 构建查询
    query = Publication.query
    
    # 如果有搜索关键词，添加搜索条件
    if search_query:
        query = query.filter(
            (Publication.title.ilike(f'%{search_query}%')) | 
            (Publication.author.ilike(f'%{search_query}%')) | 
            (Publication.category.ilike(f'%{search_query}%')) |
            (Publication.isbn.ilike(f'%{search_query}%')) |
            (Publication.issue.ilike(f'%{search_query}%'))
        )
    
    # 执行查询
    books = query.all()
    return render_template('admin/books.html', books=books, search_query=search_query)

# 管理端添加图书页面
@app.route('/admin/books/add', methods=['GET', 'POST'])
@login_required
def admin_add_book():
    if current_user.role != ROLE_ADMIN and current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        type = request.form['type']
        author = request.form.get('author')
        isbn = request.form.get('isbn')
        category = request.form.get('category')
        issue = request.form.get('issue')
        publisher = request.form.get('publisher')
        is_latest = 'is_latest' in request.form
        
        # 从系统配置获取最大借阅天数
        max_borrow_days_config = SystemConfig.query.filter_by(config_key='max_borrow_days').first()
        if max_borrow_days_config:
            default_max_days = int(max_borrow_days_config.config_value)
        else:
            default_max_days = 30  # 默认值
        
        # 设置最大借阅天数
        if type == 'book':
            max_loan_days = default_max_days
        else:
            max_loan_days = default_max_days // 2  # 杂志借阅天数为图书的一半
        
        # 检查图书是否已存在
        existing_book = Publication.query.filter_by(title=title).first()
        if existing_book:
            flash('图书已存在！', 'danger')
            return redirect(url_for('admin_add_book'))
        
        # 创建新图书
        new_book = Publication(
            title=title,
            type=type,
            author=author,
            isbn=isbn,
            category=category,
            issue=issue,
            publisher=publisher,
            is_latest=is_latest,
            max_loan_days=max_loan_days
        )
        
        # 保存到数据库
        db.session.add(new_book)
        db.session.commit()
        
        flash('图书添加成功！', 'success')
        return redirect(url_for('admin_manage_books'))
    
    return render_template('admin/add_book.html')

# 管理端删除图书操作
@app.route('/admin/books/delete/<int:book_id>', methods=['POST'])
@login_required
def admin_delete_book(book_id):
    if current_user.role != ROLE_ADMIN and current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    book = Publication.query.get_or_404(book_id)
    
    # 检查图书是否已被借阅
    if book.is_borrowed:
        flash('该书已被借阅，无法删除！', 'danger')
        return redirect(url_for('admin_manage_books'))
    
    # 删除图书
    db.session.delete(book)
    db.session.commit()
    
    flash('图书删除成功！', 'success')
    return redirect(url_for('admin_manage_books'))

# 管理端读者管理页面
@app.route('/admin/readers')
@login_required
def admin_manage_readers():
    if current_user.role != ROLE_ADMIN and current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    readers = User.query.filter_by(role=ROLE_READER).all()
    return render_template('admin/readers.html', readers=readers)

# 管理端添加读者页面
@app.route('/admin/readers/add', methods=['GET', 'POST'])
@login_required
def admin_add_reader():
    if current_user.role != ROLE_ADMIN and current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        reader_id = request.form['reader_id']
        username = request.form['username']
        password = request.form['password']
        
        # 检查用户名是否已存在
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('用户名已存在！', 'danger')
            return redirect(url_for('admin_add_reader'))
        
        # 检查读者ID是否已存在
        existing_reader = User.query.filter_by(reader_id=reader_id).first()
        if existing_reader:
            flash('读者ID已存在！', 'danger')
            return redirect(url_for('admin_add_reader'))
        
        # 创建新读者
        new_reader = User(
            name=name,
            reader_id=reader_id,
            username=username,
            password=generate_password_hash(password),
            role=ROLE_READER
        )
        
        # 保存到数据库
        db.session.add(new_reader)
        db.session.commit()
        
        flash('读者添加成功！', 'success')
        return redirect(url_for('admin_manage_readers'))
    
    return render_template('admin/add_reader.html')

# 管理端借阅管理页面
@app.route('/admin/borrows')
@login_required
def admin_manage_borrows():
    if current_user.role != ROLE_ADMIN and current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    # 获取所有借阅记录
    borrow_records = BorrowRecord.query.order_by(BorrowRecord.borrow_date.desc()).all()
    return render_template('admin/borrows.html', records=borrow_records)

# 超级管理员端首页
@app.route('/super_admin/dashboard')
@login_required
def super_admin_dashboard():
    if current_user.role != ROLE_SUPER_ADMIN:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    # 统计信息
    total_admins = User.query.filter((User.role == ROLE_ADMIN) | (User.role == ROLE_SUPER_ADMIN)).count()
    total_readers = User.query.filter_by(role=ROLE_READER).count()
    total_books = Publication.query.count()
    
    return render_template('super_admin/dashboard.html', total_admins=total_admins, total_readers=total_readers, total_books=total_books)

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
    total_books = Publication.query.count()
    total_books_borrowed = Publication.query.filter_by(is_borrowed=True).count()
    total_books_available = Publication.query.filter_by(is_borrowed=False).count()
    total_readers = User.query.filter_by(role=ROLE_READER).count()
    total_admins = User.query.filter((User.role == ROLE_ADMIN) | (User.role == ROLE_SUPER_ADMIN)).count()
    total_borrow_records = BorrowRecord.query.count()
    total_active_borrows = BorrowRecord.query.filter_by(return_date=None).count()
    
    return render_template('super_admin/statistics.html', total_books=total_books, total_books_borrowed=total_books_borrowed, 
                          total_books_available=total_books_available, total_readers=total_readers, 
                          total_admins=total_admins, total_borrow_records=total_borrow_records, 
                          total_active_borrows=total_active_borrows)

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
                name='图书管理员',
                admin_id='admin002'
            )
            db.session.add(admin)
            
            # 创建学生读者
            reader = User(
                username='reader001',
                password=generate_password_hash('reader001'),
                role=ROLE_READER,
                name='张三',
                reader_id='2021001'
            )
            db.session.add(reader)
        
        # 添加默认系统配置
        default_configs = [
            {'config_key': 'primary_color', 'config_value': '#007bff', 'description': '主色调'}, 
            {'config_key': 'secondary_color', 'config_value': '#6c757d', 'description': '次要色调'},
            {'config_key': 'success_color', 'config_value': '#28a745', 'description': '成功色调'},
            {'config_key': 'danger_color', 'config_value': '#dc3545', 'description': '危险色调'},
            {'config_key': 'warning_color', 'config_value': '#ffc107', 'description': '警告色调'},
            {'config_key': 'info_color', 'config_value': '#17a2b8', 'description': '信息色调'},
            {'config_key': 'system_name', 'config_value': '图书馆借阅系统', 'description': '系统名称'},
            {'config_key': 'max_borrow_days', 'config_value': '30', 'description': '最大借阅天数'}
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
        
        # 添加示例图书
        if not Publication.query.first():
            book1 = Publication(
                title='Python编程从入门到实践',
                type='book',
                author='Eric Matthes',
                isbn='9787115428028',
                category='编程',
                max_loan_days=14
            )
            book2 = Publication(
                title='设计模式',
                type='book',
                author='刘溪',
                isbn='9787111075752',
                category='软件工程',
                max_loan_days=14
            )
            book3 = Publication(
                title='算法导论',
                type='book',
                author='Thomas H. Cormen',
                isbn='9787111407010',
                category='计算机科学',
                max_loan_days=14
            )
            book4 = Publication(
                title='深入理解计算机系统',
                type='book',
                author='Randal E. Bryant',
                isbn='9787111544937',
                category='计算机科学',
                max_loan_days=14
            )
            book5 = Publication(
                title='数据结构与算法分析',
                type='book',
                author='Mark Allen Weiss',
                isbn='9787115450638',
                category='计算机科学',
                max_loan_days=14
            )
            book6 = Publication(
                title='计算机网络：自顶向下方法',
                type='book',
                author='James F. Kurose',
                isbn='9787111609910',
                category='计算机科学',
                max_loan_days=14
            )
            book7 = Publication(
                title='操作系统概念',
                type='book',
                author='Abraham Silberschatz',
                isbn='9787111609859',
                category='计算机科学',
                max_loan_days=14
            )
            book8 = Publication(
                title='人工智能：一种现代的方法',
                type='book',
                author='Stuart Russell',
                isbn='9787111609842',
                category='人工智能',
                max_loan_days=14
            )
            book9 = Publication(
                title='软件工程：实践者的研究方法',
                type='book',
                author='Roger S. Pressman',
                isbn='9787111609835',
                category='软件工程',
                max_loan_days=14
            )
            book10 = Publication(
                title='机器学习',
                type='book',
                author='Tom Mitchell',
                isbn='9787111609828',
                category='人工智能',
                max_loan_days=14
            )
            book11 = Publication(
                title='计算机图形学原理及实践',
                type='book',
                author='James D. Foley',
                isbn='9787111609811',
                category='计算机科学',
                max_loan_days=14
            )
            magazine1 = Publication(
                title='计算机科学',
                type='magazine',
                issue='2023-10',
                publisher='科学出版社',
                is_latest=True,
                max_loan_days=7
            )
            magazine2 = Publication(
                title='编程世界',
                type='magazine',
                issue='2023-11',
                publisher='编程出版社',
                is_latest=True,
                max_loan_days=7
            )
            
            db.session.add_all([book1, book2, book3, book4, book5, book6, book7, book8, book9, book10, book11, magazine1, magazine2])
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

# 应用启动时调用初始化函数
if __name__ == '__main__':
    create_tables()
    app.run(debug=True)