# 知境文本分析系统 - Railway 部署指南

## 部署到 Railway

### 方式一：使用 GitHub 部署（推荐）

1. **创建 GitHub 仓库**
   - 将项目推送到 GitHub 仓库
   - 确保 `.gitignore` 中包含 `.env` 和 `instance/`

2. **连接 Railway**
   - 访问 [Railway](https://railway.app/)
   - 点击 "New Project" → "Deploy from GitHub repo"
   - 选择您的仓库

3. **添加环境变量**
   在 Railway 项目设置中添加以下环境变量：

   | 变量名 | 必填 | 值 |
   |--------|------|-----|
   | `SECRET_KEY` | 是 | 生成一个随机密钥 |
   | `DASHSCOPE_API_KEY` | 是 | 阿里云百炼 API 密钥 |
   | `ENCRYPTION_KEY` | 是 | 生成一个随机加密密钥 |
   | `DEFAULT_AI_SERVICE` | 否 | `aliyun`（默认）|

   **生成密钥的方法**：
   ```bash
   # 在终端中运行
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

4. **配置数据库**
   - Railway 会自动创建 PostgreSQL 数据库
   - 自动设置 `DATABASE_URL` 环境变量
   - 数据库表会自动创建

5. **部署**
   - Railway 会自动检测 Python 项目并部署
   - 等待部署完成后访问提供的域名

### 方式二：使用 Railway CLI

```bash
# 安装 Railway CLI
npm install -g @railway/cli

# 登录
railway login

# 初始化项目
cd your-project-directory
railway init

# 设置环境变量
railway variables set SECRET_KEY=your-secret-key
railway variables set DASHSCOPE_API_KEY=your-api-key
railway variables set ENCRYPTION_KEY=your-encryption-key

# 部署
railway up
```

## 环境变量说明

### 必需变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `SECRET_KEY` | Flask 会话密钥，必须设置为安全的随机字符串 | `abc123xyz...` |
| `DASHSCOPE_API_KEY` | 阿里云百炼 API 密钥 | `sk-xxxxxxxx...` |
| `ENCRYPTION_KEY` | 数据加密密钥 | `random-encryption-key` |

### 可选变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `FLASK_ENV` | 运行环境 | `production` |
| `DEFAULT_AI_SERVICE` | AI 服务类型 | `aliyun` |
| `QWEN_BASE_URL` | 阿里云 API 地址 | 已配置 |
| `QWEN_CHAT_MODEL` | 使用的模型 | `qwen-plus` |

## 部署注意事项

### 1. 数据库
- **本地开发**：使用 SQLite（instance/text_analysis.db）
- **Railway 部署**：自动使用 PostgreSQL
- 数据库表会在首次访问时自动创建
- 初始用户会自动创建：
  - 超级管理员: `admin001` / `admin001`
  - 管理员: `admin002` / `admin002`
  - 普通用户: `user001` / `user001`

### 2. 文件上传
- 上传的文件存储在 `/tmp` 目录（Railway 的临时存储）
- **重要**：Railway 的临时存储在重启后会丢失
- 如需持久化存储，建议配置阿里云 OSS 或其他对象存储服务

### 3. 性能优化
- 使用 Gunicorn 作为生产服务器
- 配置了 120 秒超时（适应 AI 响应较慢的情况）
- 建议配置 Railway 的 "Always On" 功能避免休眠

### 4. 日志查看
- 在 Railway 控制台查看应用日志
- 错误信息会输出到 stderr
- 可以通过 `railway logs` 命令查看实时日志

## 故障排除

### Internal Server Error

**常见原因：**

1. **环境变量未设置**
   - 确保 `SECRET_KEY` 已设置
   - 确保 `DASHSCOPE_API_KEY` 已设置

2. **数据库连接失败**
   - 检查 Railway 是否正确配置了 PostgreSQL
   - 确保 `DATABASE_URL` 环境变量存在

3. **依赖安装失败**
   - 检查构建日志是否有错误
   - 确保 `requirements.txt` 包含所有依赖

4. **权限问题**
   - 确保应用有写入权限到 `/tmp` 目录
   - 检查文件上传目录权限

### 查看日志

```bash
# 使用 Railway CLI 查看日志
railway logs

# 查看最近的错误
railway logs | grep -i error
```

## 默认账户

部署后可以使用以下账户登录：

| 用户名 | 密码 | 角色 |
|--------|------|------|
| `admin001` | `admin001` | 超级管理员 |
| `admin002` | `admin002` | 管理员 |
| `user001` | `user001` | 普通用户 |

**安全提醒**：部署后请立即修改默认密码！

## 更新部署

```bash
# 推送代码到 GitHub
git push origin main

# Railway 会自动重新部署
```

## 项目结构

```
liberary/
├── app.py                 # 主应用文件
├── models.py              # 数据库模型
├── ai_service.py          # AI 服务模块
├── templates/             # HTML 模板
├── instance/              # 实例目录（本地开发）
├── requirements.txt       # Python 依赖
├── railway.toml          # Railway 部署配置
├── Procfile              # Gunicorn 配置
├── runtime.txt           # Python 版本
└── .env.example          # 环境变量示例
```

## 许可证

MIT License