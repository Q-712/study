from datetime import datetime, timedelta
from typing import Optional

class Publication:
    """出版物基类 - 演示继承和多态"""
    
    def __init__(self, title: str) -> None:
        self.title = title
        self._is_borrowed = False  # 保护属性：借阅状态
        self._borrower = None      # 保护属性：当前借阅者
        self._due_date = None      # 保护属性：应归还日期

    @property
    def is_borrowed(self) -> bool:
        """是否被借出 - 只读属性"""
        return self._is_borrowed

    @property
    def borrower(self):
        """当前借阅者 - 只读属性"""
        return self._borrower

    @property
    def due_date(self):
        """应归还日期 - 只读属性"""
        return self._due_date

    def get_max_loan_days(self) -> int:
        """获取最大借阅天数 - 子类必须重写"""
        raise NotImplementedError("子类必须实现此方法")

    def receive_borrow_message(self, reader, days: int = None, **kwargs) -> tuple[bool, str]:
        """处理借阅消息 - 演示消息传递"""
        # 如果已被借出，返回失败信息
        if self._is_borrowed:
            due_date_str = self._due_date.strftime("%Y-%m-%d") if self._due_date else "未知"
            return (False, 
                    f"书已被{self._borrower.name}借出，预计{due_date_str}时间归还")
        
        # 确定借阅天数（不超过最大借阅天数）
        max_days = self.get_max_loan_days()
        borrow_days = days if days and 1 <= days <= max_days else max_days
        
        # 修改借阅状态
        self._is_borrowed = True
        self._borrower = reader
        self._due_date = datetime.now() + timedelta(days=borrow_days)
        
        # 返回成功信息
        due_date_str = self._due_date.strftime("%Y-%m-%d")
        return (True, 
                f"成功借阅《{self.title}》，借阅{borrow_days}天，应归还日期：{due_date_str}")

    def receive_return_message(self) -> bool:
        """处理归还消息"""
        if self._is_borrowed:
            self._is_borrowed = False
            self._borrower = None
            self._due_date = None
            return True
        return False

    def get_description(self) -> str:
        """获取描述 - 子类必须重写"""
        raise NotImplementedError("子类必须实现此方法")

class Book(Publication):
    """图书类 - 演示继承和多态"""
    
    def __init__(self, title: str, author: str, isbn: str, category: str = "技术") -> None:
        super().__init__(title)
        self.author = author      # 公有属性
        self.isbn = isbn          # 公有属性
        self.category = category  # 公有属性

    def get_max_loan_days(self) -> int:
        """书籍最大借阅14天"""
        return 14

    def get_description(self) -> str:
        return f"📚《{self.title}》- 作者: {self.author}, 分类: {self.category}"

class Magazine(Publication):
    """杂志类 - 演示继承和多态"""
    
    def __init__(self, title: str, issue: str, publisher: str) -> None:
        super().__init__(title)
        self.issue = issue          # 公有属性：期号
        self.publisher = publisher  # 公有属性：出版商
        self._is_latest = False     # 保护属性：是否最新期

    def mark_as_latest(self) -> None:
        """标记为最新期"""
        self._is_latest = True

    def mark_as_archive(self) -> None:
        """标记为过刊"""
        self._is_latest = False

    def get_max_loan_days(self) -> int:
        """杂志最大借阅7天"""
        return 7

    def get_description(self) -> str:
        latest_tag = "【最新】" if self._is_latest else ""
        return f"📖《{self.title}》{latest_tag}- 期号: {self.issue}, 出版商: {self.publisher}"

class Library:
    """数据存储 - 使用基类方法检查权限"""
    
    def __init__(self, name: str) -> None:
        self.name = name
        self._publications = []
        self._readers = []
        self._admins = []
        self._create_initial_admin()

    def _create_initial_admin(self):
        """创建初始超级管理员"""
        admin = Admin("系统管理员", "admin001", self)
        self._admins.append(admin)
        # 设置第一个管理员为超级管理员
        self._super_admin_id = "admin001"

    # 检查是否为超级管理员
    def _is_super_admin(self, admin) -> bool:
        """检查是否为超级管理员"""
        return hasattr(admin, 'admin_id') and admin.admin_id == self._super_admin_id

    # 统一的权限检查方法
    def _check_permission(self, admin) -> bool:
        return admin in self._admins

    # 只读属性
    @property
    def publications(self): return self._publications.copy()
    @property
    def readers(self): return self._readers.copy()
    @property
    def admins(self): return self._admins.copy()

    # 简化的数据操作方法
    def _add_publication(self, admin: 'Admin', publication: Publication) -> tuple[bool, str]:
        """
        返回操作结果和详细错误信息
        返回: (success: bool, message: str)
        """
        # 权限检查
        if not self._check_permission(admin):
            return False, "权限不足"
        
        # 数据完整性检查（核心业务规则）
        if any(p.title == publication.title for p in self._publications):
            return False, "出版物已存在"
        
        # 执行操作
        self._publications.append(publication)
        return True, "添加成功"

    def _remove_publication(self, admin: 'Admin', title: str) -> tuple[bool, str]:
        if not self._check_permission(admin):
            return False, "权限不足"

        for pub in self._publications:
            if pub.title == title:
                self._publications.remove(pub)
                return True, "移除成功"
        return False, "出版物不存在"
    
    def _add_reader(self, admin: 'Admin', reader: 'Reader') -> tuple[bool, str]:
        if not self._check_permission(admin):
            return False, "权限不足"
            
        if any(r.reader_id == reader.reader_id for r in self._readers):
            return False, "❌ 读者ID已存在"

        self._readers.append(reader)
        return True, "添加成功"

    def _add_admin(self, admin: 'Admin', new_admin: 'Admin') -> tuple[bool, str]:
        """添加管理员 - 只有超级管理员可以调用"""
        # 只有超级管理员可以添加管理员
        if not self._is_super_admin(admin):
            return False, "权限不足，只有超级管理员可以添加管理员"

        if any(a.admin_id == new_admin.admin_id for a in self._admins):
            return False, "❌ 管理员ID已存在"

        self._admins.append(new_admin)
        return True, "添加成功"

    # 查询方法
    def get_publication(self, title: str) -> Optional[Publication]:
        return next((p for p in self._publications if p.title == title), None)

    def get_available_publications(self):
        """获取可借阅的出版物 - 模板需要这个方法"""
        return [p for p in self._publications if not p.is_borrowed]

class Admin:
    def __init__(self, name: str, admin_id: str, library: Library):
        self.name = name
        self.admin_id = admin_id
        self.library = library

    def add_publication(self, publication: Publication) -> str:
        """添加出版物"""
        success, message = self.library._add_publication(self, publication)
        
        if success:
            return f"✅ {self.name} 添加了: {publication.title}"
        else:
            return f"❌ {message}"

    def remove_publication(self, title: str) -> str:
        """移除出版物"""
        success, message = self.library._remove_publication(self, title)
        if success:
            return f"✅ {self.name} 移除了: {title}"
        else:
            return f"❌ {message}"

    def register_reader(self, reader: 'Reader') -> str:
        """注册读者"""
        success, message = self.library._add_reader(self, reader)
        if success:
            return f"✅ {self.name} 注册了读者: {reader.name}"
        else:
            return f"❌ {message}"

    def register_admin(self, new_admin: 'Admin') -> str:
        """注册新管理员 - 只有超级管理员可以注册"""
        success, message = self.library._add_admin(self, new_admin)
        if success:
            return f"✅ {self.name} 添加了管理员: {new_admin.name}"
        else:
            return f"❌ {message}"

class Reader:
    """读者类 - 只能借阅和查询"""
    
    def __init__(self, name: str, reader_id: str) -> None:
        self.name = name
        self.reader_id = reader_id
        self._borrowed_items = []     # 保护属性

    @property
    def borrowed_items(self):
        """借阅列表 - 只读"""
        return self._borrowed_items.copy()

    def send_borrow_message(self, library: Library, title: str, days: int = 14, **kwargs) -> str:
        """
        根据出版物title属性，查询图书馆里是否存有该出版，如果有，获取该出版物publication
        然后调用publication.receive_borrow_message()
        如果借阅成功，更新读者的相关属性，返回成功借阅信息
        否则，返回错误信息
        """
        # 查询出版物
        publication = library.get_publication(title)
        if not publication:
            return f"❌ 图书馆未找到《{title}》"
        
        # 发送借阅消息
        success, msg = publication.receive_borrow_message(self, days, **kwargs)
        if success:
            self._borrowed_items.append(publication)
            return f"✅ {self.name} {msg}"
        else:
            return f"❌ {self.name} {msg}"

    def send_return_message(self, title: str) -> str:
        """归还出版物"""
        print(f"📨 {self.name} 请求归还《{title}》")
        
        # 在借阅列表中查找
        publication_to_return = None
        for item in self._borrowed_items:
            if item.title == title:
                publication_to_return = item
                break
        
        if not publication_to_return:
            return f"❌ {self.name} 没有借阅《{title}》"
        
        # 发送归还消息给出版物
        result = publication_to_return.receive_return_message()

        # 从借阅列表中移除  
        if result:
            self._borrowed_items.remove(publication_to_return)    
            return f"✅ {self.name} 成功归还《{title}》"
        else:
            return f"❌ 信息不一致，请检查！！！"

"""
面向对象方法学教学演示
核心概念：封装、继承、多态、抽象、消息传递
"""

# 1. 创建图书馆系统
print("\n1️⃣ 创建图书馆系统")
library = Library("北京大学图书馆")
print(f"📚 创建图书馆: {library.name}")

# 获取初始超级管理员
super_admin = library.admins[0]
print(f"👨‍💼 系统自动创建超级管理员: {super_admin.name}")

# 2. 演示封装
print("\n" + "=" * 60)
print("📦 封装 (Encapsulation) 演示")
print("=" * 60)

# 创建读者
reader1 = Reader("张三", "2021001")
print(f"👤 创建读者对象: {reader1.name}")
print(f"   ✅ 可以访问公共属性: name={reader1.name}, reader_id={reader1.reader_id}")
print(f"   ❌ 无法直接访问保护属性: _borrowed_items")
print(f"   ✅ 通过只读属性访问: borrowed_items = {reader1.borrowed_items}")

# 管理员添加图书
book1 = Book("Python编程从入门到实践", "Eric Matthes", "9787115428028", "编程")
result = super_admin.add_publication(book1)
print(f"📖 {result}")

# 3. 演示继承和多态
print("\n" + "=" * 60)
print("🧬 继承与多态 (Inheritance & Polymorphism) 演示")
print("=" * 60)

# 创建不同类型的出版物
book2 = Book("设计模式", "刘溪", "9787111075752", "软件工程")
magazine1 = Magazine("计算机科学", "2023-10", "科学出版社")
magazine1.mark_as_latest()

# 管理员添加出版物
super_admin.add_publication(book2)
super_admin.add_publication(magazine1)

print("\n📚 图书馆当前出版物:")
for pub in library.publications:
    # 多态：调用相同的get_description()方法，但表现不同
    print(f"  {pub.get_description()}")
    print(f"   最大借阅天数: {pub.get_max_loan_days()}天")

# 4. 演示消息传递
print("\n" + "=" * 60)
print("📨 消息传递 (Message Passing) 演示")
print("=" * 60)

# 读者借书
print(f"\n👤 {reader1.name} 开始借阅:")
result1 = reader1.send_borrow_message(library, "Python编程从入门到实践", 10)
print(f"  {result1}")

result2 = reader1.send_borrow_message(library, "设计模式")
print(f"  {result2}")

# 尝试借阅已被借出的书
reader2 = Reader("李四", "2021002")
print(f"\n👤 {reader2.name} 再次借阅同一本书:")
result3 = reader2.send_borrow_message(library, "Python编程从入门到实践")
print(f"  {result3}")

# 5. 演示借阅记录查看
print("\n" + "=" * 60)
print("📊 借阅状态演示")
print("=" * 60)

print(f"\n👤 {reader1.name} 的借阅记录:")
for item in reader1.borrowed_items:
    print(f"  📚 {item.title} - 应归还日期: {item.due_date.strftime('%Y-%m-%d') if item.due_date else '未借出'}")

# 6. 演示归还流程
print("\n" + "=" * 60)
print("🔄 归还流程演示")
print("=" * 60)

print(f"\n👤 {reader1.name} 归还图书:")
result4 = reader1.send_return_message("Python编程从入门到实践")
print(f"  {result4}")

print(f"\n👤 {reader1.name} 当前借阅:")
for item in reader1.borrowed_items:
    print(f"  📚 {item.title}")

print(f"\n📚 图书馆可借阅书籍:")
for pub in library.get_available_publications():
    print(f"  {pub.title}")

# 7. 演示管理员权限
print("\n" + "=" * 60)
print("🔐 权限控制演示")
print("=" * 60)

# 先让超级管理员添加admin2为新管理员
print(f"\n✅ 超级管理员添加新管理员admin2:")
admin2 = Admin("张华老师", "admin002", library)
reg_result = super_admin.register_admin(admin2)
print(f"  {reg_result}")

# admin2上架新书book3
print(f"\n✅ admin2上架新书book3:")
book3 = Book("漂亮餐厅手册", "匿名", "000300", "餐饮")
add_result = admin2.add_publication(book3)
print(f"  {add_result}")

# 验证新书是否添加成功
print(f"\n📚 图书馆最新出版物列表:")
for pub in library.publications:
    print(f"  {pub.title}")
    