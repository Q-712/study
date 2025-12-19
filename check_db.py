import os
import sys
from app import app, db, User

# 获取数据库中的所有用户
with app.app_context():
    users = User.query.all()
    print(f"共有 {len(users)} 个用户")
    for user in users:
        print(f"ID: {user.id}, 用户名: {user.username}, 角色: {user.role}, 密码哈希: {user.password}")
