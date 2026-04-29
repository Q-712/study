# 知境文本分析系统 - Railway 部署指南

## 部署到 Railway

### 方式一：使用 Railway CLI

1. 安装 Railway CLI
```bash
npm install -g @railway/cli
```

2. 登录 Railway
```bash
railway login
```

3. 初始化项目
```bash
cd d:\class\liberary
railway init
```

4. 设置环境变量
```bash
railway variables set DASHSCOPE_API_KEY=your_api_key
railway variables set ENCRYPTION_KEY=your_encryption_key
```

5. 部署
```bash
railway up
```

### 方式二：使用 GitHub 部署

1. 将项目推送到 GitHub 仓库
2. 在 Railway 中连接 GitHub 仓库
3. 在 Railway 项目设置中添加环境变量：
   - `DASHSCOPE_API_KEY`: 阿里云API密钥
   - `ENCRYPTION_KEY`: 加密密钥

### 环境变量说明

| 变量名 | 必填 | 说明 |
|--------|------|------|
| DASHSCOPE_API_KEY | 是 | 阿里云百炼API密钥 |
| ENCRYPTION_KEY | 是 | 数据加密密钥 |
| QWEN_BASE_URL | 否 | 阿里云API地址（默认已配置）|
| QWEN_CHAT_MODEL | 否 | 模型名称（默认qwen-plus）|
| DEFAULT_AI_SERVICE | 否 | AI服务类型（默认aliyun）|

### Railway 配置文件

- `railway.toml` - Railway 部署配置
- `Procfile` - Gunicorn 进程配置
- `runtime.txt` - Python 版本
- `requirements.txt` - Python 依赖
- `.env.example` - 环境变量示例

### 注意事项

1. **数据库**: 使用 SQLite（已在 instance 文件夹中），Railway 会持久化存储
2. **文件上传**: 上传的文件存储在 instance/uploads，建议配置对象存储
3. **超时设置**: Gunicorn 超时设置为 120 秒，适合 AI 响应较慢的场景
