# 知境文本分析系统

一个基于 Flask 框架开发的智能文本分析系统，支持文档上传、智能问答、文本搜索等功能。

## 系统功能

- **智能问答**: 基于上传的文档内容进行智能问答分析
- **全局搜索**: 通过 AI 助手进行智能搜索和回答
- **文件管理**: 支持 PDF、Word、TXT 等多种格式文档上传和管理
- **用户权限**: 完整的三级用户权限体系（普通用户、管理员、超级管理员）

## 技术栈

- **后端框架**: Flask (Python)
- **数据库**: SQLite + Flask-SQLAlchemy
- **用户认证**: Flask-Login
- **AI 服务**: 阿里云百炼 API (DashScope)
- **前端框架**: Bootstrap 5 + Jinja2 模板引擎

## 系统架构

### 用户角色

1. **普通用户**: 上传文件、进行问答分析、搜索
2. **管理员**: 管理普通用户、管理文件
3. **超级管理员**: 系统配置、管理员账户

### 技术结构

- **模型层**: 用户、文件、权限等数据模型
- **视图层**: Flask 路由处理业务逻辑
- **模板层**: Jinja2 渲染动态页面
- **AI 服务层**: 阿里云百炼 API 集成

## 快速部署到 Railway

### 使用 Railway CLI

```bash
# 安装 Railway CLI
npm install -g @railway/cli

# 登录
railway login

# 初始化项目
railway init

# 设置环境变量
railway variables set DASHSCOPE_API_KEY=your_api_key
railway variables set ENCRYPTION_KEY=your_encryption_key

# 部署
railway up
```

### 使用 GitHub 部署

1. 将项目推送到 GitHub 仓库
2. 在 Railway 中连接 GitHub 仓库
3. 添加环境变量后自动部署

### 必需环境变量

| 变量名 | 说明 |
|--------|------|
| DASHSCOPE_API_KEY | 阿里云百炼 API 密钥 |
| ENCRYPTION_KEY | 数据加密密钥 |

## 本地运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入配置：

```bash
cp .env.example .env
```

### 3. 运行

```bash
python app.py
```

访问 http://127.0.0.1:5000

### 默认账户

- 超级管理员: admin001 / admin001
- 管理员: admin002 / admin002
- 普通用户: user001 / user001

## 项目结构

```
liberary/
├── app.py                 # 主应用文件
├── models.py              # 数据库模型
├── ai_service.py          # AI 服务模块
├── encryption.py          # 加密工具
├── templates/             # HTML 模板
│   ├── base.html         # 基础模板
│   ├── login.html        # 登录页面
│   ├── user/             # 用户端页面
│   ├── admin/            # 管理员页面
│   └── super_admin/      # 超级管理员页面
├── instance/              # 实例目录（数据库和上传文件）
├── requirements.txt       # Python 依赖
├── railway.toml          # Railway 部署配置
├── Procfile              # Gunicorn 配置
├── runtime.txt           # Python 版本
└── DEPLOY_RAILWAY.md     # Railway 部署指南
```

## 支持的文件格式

- PDF 文档 (.pdf)
- Word 文档 (.doc, .docx)
- 文本文件 (.txt, .md)

## 许可证

MIT License
