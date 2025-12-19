import unittest
from flask import Flask
from app import app, db, User, Publication, BorrowRecord, ROLE_READER, ROLE_ADMIN, ROLE_SUPER_ADMIN
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

class LibrarySystemTests(unittest.TestCase):
    def setUp(self):
        """设置测试环境，创建内存数据库"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        
        self.app = app.test_client()
        
        with app.app_context():
            db.create_all()
            self.create_test_data()
    
    def tearDown(self):
        """清理测试环境"""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def create_test_data(self):
        """创建测试数据"""
        # 创建测试用户
        super_admin = User(
            username='test_super_admin',
            password=generate_password_hash('password123'),
            role=ROLE_SUPER_ADMIN,
            name='测试超级管理员',
            admin_id='sa001'
        )
        
        admin = User(
            username='test_admin',
            password=generate_password_hash('password123'),
            role=ROLE_ADMIN,
            name='测试管理员',
            admin_id='a001'
        )
        
        reader = User(
            username='test_reader',
            password=generate_password_hash('password123'),
            role=ROLE_READER,
            name='测试读者',
            reader_id='r001'
        )
        
        # 创建测试图书
        book1 = Publication(
            title='测试图书1',
            type='book',
            author='测试作者1',
            isbn='9787111000001',
            category='测试分类1',
            max_loan_days=14
        )
        
        book2 = Publication(
            title='测试图书2',
            type='book',
            author='测试作者2',
            isbn='9787111000002',
            category='测试分类2',
            max_loan_days=14
        )
        
        magazine1 = Publication(
            title='测试杂志1',
            type='magazine',
            author='测试杂志作者1',
            isbn='9770000000001',
            category='测试杂志分类1',
            issue='2023年第1期',
            max_loan_days=7
        )
        
        # 添加到数据库
        db.session.add_all([super_admin, admin, reader, book1, book2, magazine1])
        db.session.commit()
    
    # ------------------------------
    # 单元测试：各个类的测试
    # ------------------------------
    
    def test_user_model(self):
        """测试User类的基本功能"""
        with app.app_context():
            # 测试用户查询
            reader = User.query.filter_by(username='test_reader').first()
            self.assertIsNotNone(reader)
            self.assertEqual(reader.name, '测试读者')
            self.assertEqual(reader.role, ROLE_READER)
            self.assertTrue(reader.is_authenticated)
            
            # 测试用户角色
            admin = User.query.filter_by(username='test_admin').first()
            self.assertEqual(admin.role, ROLE_ADMIN)
            
            super_admin = User.query.filter_by(username='test_super_admin').first()
            self.assertEqual(super_admin.role, ROLE_SUPER_ADMIN)
    
    def test_publication_model(self):
        """测试Publication类的基本功能"""
        with app.app_context():
            # 测试图书查询
            book1 = Publication.query.filter_by(title='测试图书1').first()
            self.assertIsNotNone(book1)
            self.assertEqual(book1.type, 'book')
            self.assertEqual(book1.author, '测试作者1')
            self.assertEqual(book1.max_loan_days, 14)
            self.assertFalse(book1.is_borrowed)
            
            # 测试杂志查询
            magazine1 = Publication.query.filter_by(title='测试杂志1').first()
            self.assertIsNotNone(magazine1)
            self.assertEqual(magazine1.type, 'magazine')
            self.assertEqual(magazine1.issue, '2023年第1期')
            self.assertEqual(magazine1.max_loan_days, 7)
    
    def test_borrow_record_model(self):
        """测试BorrowRecord类的基本功能"""
        with app.app_context():
            # 创建借阅记录
            reader = User.query.filter_by(username='test_reader').first()
            book = Publication.query.filter_by(title='测试图书1').first()
            
            borrow_date = datetime.now()
            due_date = borrow_date + timedelta(days=14)
            
            record = BorrowRecord(
                reader_id=reader.id,
                publication_id=book.id,
                borrow_date=borrow_date,
                due_date=due_date
            )
            
            db.session.add(record)
            db.session.commit()
            
            # 测试借阅记录查询
            retrieved_record = BorrowRecord.query.first()
            self.assertIsNotNone(retrieved_record)
            self.assertEqual(retrieved_record.reader_id, reader.id)
            self.assertEqual(retrieved_record.publication_id, book.id)
            self.assertEqual(retrieved_record.borrow_date.date(), borrow_date.date())
            self.assertEqual(retrieved_record.due_date.date(), due_date.date())
            self.assertIsNone(retrieved_record.return_date)
    
    # ------------------------------
    # 集成测试：流程测试
    # ------------------------------
    
    def test_borrow_return_process(self):
        """测试借阅和归还流程集成"""
        with app.app_context():
            # 获取测试数据
            reader = User.query.filter_by(username='test_reader').first()
            book = Publication.query.filter_by(title='测试图书1').first()
            
            # 登录读者账号
            response = self.app.post('/login', data={
                'username': 'test_reader',
                'password': 'password123'
            }, follow_redirects=True)
            
            # 测试借阅图书
            response = self.app.post(f'/reader/borrow/{book.id}', follow_redirects=True)
            response_text = response.get_data(as_text=True)
            self.assertIn('成功借阅', response_text)
            
            # 验证图书状态已更新为已借阅
            updated_book = Publication.query.get(book.id)
            self.assertTrue(updated_book.is_borrowed)
            
            # 验证借阅记录已创建
            borrow_record = BorrowRecord.query.filter_by(publication_id=book.id, return_date=None).first()
            self.assertIsNotNone(borrow_record)
            
            # 测试归还图书
            response = self.app.get(f'/reader/return/{borrow_record.id}', follow_redirects=True)
            response_text = response.get_data(as_text=True)
            self.assertIn('成功归还', response_text)
            
            # 验证图书状态已更新为可借阅
            updated_book = Publication.query.get(book.id)
            self.assertFalse(updated_book.is_borrowed)
            
            # 验证借阅记录已更新归还日期
            updated_record = BorrowRecord.query.get(borrow_record.id)
            self.assertIsNotNone(updated_record.return_date)
    
    def test_permission_control(self):
        """测试权限控制集成"""
        with app.app_context():
            # 测试1：读者无法访问管理员页面
            # 登录读者账号
            self.app.post('/login', data={
                'username': 'test_reader',
                'password': 'password123'
            }, follow_redirects=True)
            
            response = self.app.get('/admin/dashboard', follow_redirects=True)
            response_text = response.get_data(as_text=True)
            self.assertIn('权限不足', response_text)
            
            # 测试2：读者无法访问超级管理员页面
            response = self.app.get('/super_admin/dashboard', follow_redirects=True)
            response_text = response.get_data(as_text=True)
            self.assertIn('权限不足', response_text)
            
            # 登出
            self.app.get('/logout', follow_redirects=True)
            
            # 测试3：管理员可以访问管理员页面
            # 登录管理员账号
            self.app.post('/login', data={
                'username': 'test_admin',
                'password': 'password123'
            }, follow_redirects=True)
            
            response = self.app.get('/admin/dashboard', follow_redirects=True)
            response_text = response.get_data(as_text=True)
            self.assertNotIn('权限不足', response_text)
            
            # 测试4：管理员无法访问超级管理员页面
            response = self.app.get('/super_admin/dashboard', follow_redirects=True)
            response_text = response.get_data(as_text=True)
            self.assertIn('权限不足', response_text)
            
            # 登出
            self.app.get('/logout', follow_redirects=True)
            
            # 测试5：超级管理员可以访问所有页面
            # 登录超级管理员账号
            self.app.post('/login', data={
                'username': 'test_super_admin',
                'password': 'password123'
            }, follow_redirects=True)
            
            response = self.app.get('/admin/dashboard', follow_redirects=True)
            response_text = response.get_data(as_text=True)
            self.assertNotIn('权限不足', response_text)
            
            response = self.app.get('/super_admin/dashboard', follow_redirects=True)
            response_text = response.get_data(as_text=True)
            self.assertNotIn('权限不足', response_text)
    
    # ------------------------------
    # 系统测试：模拟真实使用场景
    # ------------------------------
    
    def test_reader_full_workflow(self):
        """测试读者完整使用流程"""
        with app.app_context():
            # 获取测试用户和图书
            book1 = Publication.query.filter_by(title='测试图书1').first()
            book2 = Publication.query.filter_by(title='测试图书2').first()
            
            # 登录读者账号
            self.app.post('/login', data={
                'username': 'test_reader',
                'password': 'password123'
            }, follow_redirects=True)
            
            # 1. 查看可借阅图书
            response = self.app.get('/reader/borrow', follow_redirects=True)
            response_text = response.get_data(as_text=True)
            self.assertIn('测试图书1', response_text)
            self.assertIn('测试图书2', response_text)
            self.assertIn('测试杂志1', response_text)
            
            # 2. 借阅第一本图书
            response = self.app.post(f'/reader/borrow/{book1.id}', follow_redirects=True)
            response_text = response.get_data(as_text=True)
            self.assertIn('成功借阅', response_text)
            
            # 3. 查看已借阅图书（应只有一本）
            response = self.app.get('/reader/return', follow_redirects=True)
            response_text = response.get_data(as_text=True)
            self.assertIn('测试图书1', response_text)
            self.assertNotIn('测试图书2', response_text)
            
            # 4. 借阅第二本图书
            response = self.app.post(f'/reader/borrow/{book2.id}', follow_redirects=True)
            response_text = response.get_data(as_text=True)
            self.assertIn('成功借阅', response_text)
            
            # 5. 查看借阅历史（应显示两本已借阅图书）
            response = self.app.get('/reader/history', follow_redirects=True)
            response_text = response.get_data(as_text=True)
            self.assertIn('测试图书1', response_text)
            self.assertIn('测试图书2', response_text)
            
            # 6. 归还第一本图书
            borrow_record = BorrowRecord.query.filter_by(publication_id=book1.id, return_date=None).first()
            response = self.app.get(f'/reader/return/{borrow_record.id}', follow_redirects=True)
            response_text = response.get_data(as_text=True)
            self.assertIn('成功归还', response_text)
            
            # 7. 再次查看借阅历史（应显示一本已归还，一本未归还）
            response = self.app.get('/reader/history', follow_redirects=True)
            response_text = response.get_data(as_text=True)
            self.assertIn('测试图书1', response_text)  # 已归还的图书仍在历史记录中
            self.assertIn('测试图书2', response_text)  # 未归还的图书仍在历史记录中
    
    def test_admin_book_management(self):
        """测试管理员图书管理功能"""
        with app.app_context():
            # 登录管理员账号
            self.app.post('/login', data={
                'username': 'test_admin',
                'password': 'password123'
            }, follow_redirects=True)
            
            # 1. 查看图书管理页面
            response = self.app.get('/admin/books', follow_redirects=True)
            response_text = response.get_data(as_text=True)
            self.assertIn('测试图书1', response_text)
            
            # 2. 添加新图书
            new_book_data = {
                'title': '新添加的测试图书',
                'type': 'book',
                'author': '新测试作者',
                'isbn': '9787111000003',
                'category': '新测试分类',
                'publisher': '新测试出版社'
            }
            
            response = self.app.post('/admin/books/add', data=new_book_data, follow_redirects=True)
            response_text = response.get_data(as_text=True)
            self.assertIn('图书添加成功', response_text)
            
            # 3. 验证新图书已添加
            response = self.app.get('/admin/books', follow_redirects=True)
            response_text = response.get_data(as_text=True)
            self.assertIn('新添加的测试图书', response_text)
            
            # 4. 检查新图书的属性
            with app.app_context():
                new_book = Publication.query.filter_by(title='新添加的测试图书').first()
                self.assertIsNotNone(new_book)
                self.assertEqual(new_book.author, '新测试作者')
                self.assertEqual(new_book.isbn, '9787111000003')
                self.assertEqual(new_book.max_loan_days, 14)
                self.assertFalse(new_book.is_borrowed)
    
    def test_login_logout_functionality(self):
        """测试登录登出功能"""
        # 测试1：使用正确的凭据登录
        response = self.app.post('/login', data={
            'username': 'test_reader',
            'password': 'password123'
        }, follow_redirects=True)
        response_text = response.get_data(as_text=True)
        # 检查登录成功消息（可能带感叹号）
        self.assertTrue('登录成功' in response_text or '登录成功！' in response_text)
        # 检查是否跳转到了读者相关页面
        self.assertTrue('学生端仪表板' in response_text or '读者首页' in response_text or '欢迎' in response_text)
        
        # 测试2：登出
        response = self.app.get('/logout', follow_redirects=True)
        response_text = response.get_data(as_text=True)
        # 检查登出成功消息
        self.assertTrue('已成功登出' in response_text or '退出登录' in response_text or '登录' in response_text)
        
        # 测试3：使用错误的密码登录
        response = self.app.post('/login', data={
            'username': 'test_reader',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        response_text = response.get_data(as_text=True)
        # 检查错误消息
        self.assertTrue('用户名或密码错误' in response_text or '密码错误' in response_text or '登录失败' in response_text)
        
        # 测试4：使用不存在的用户名登录
        response = self.app.post('/login', data={
            'username': 'nonexistentuser',
            'password': 'password123'
        }, follow_redirects=True)
        response_text = response.get_data(as_text=True)
        # 检查错误消息
        self.assertTrue('用户名或密码错误' in response_text or '用户不存在' in response_text or '登录失败' in response_text)

if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
