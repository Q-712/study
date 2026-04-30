# AI搜索分析路由
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app import app, db, ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN
from models import UploadedFile, FileVisibility
from ai_service import AIService

ai_service = AIService()

def read_file_content(file_path):
    file_path = file_path.replace('\\', '/')
    try:
        encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'utf-16']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except:
                continue
        
        try:
            from docx import Document
            doc = Document(file_path)
            return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        except:
            pass
        
        return '无法读取文件内容'
    except Exception as e:
        return f'读取文件失败: {str(e)}'

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
    if current_user.role != ROLE_USER:
        flash('权限不足！', 'danger')
        return redirect(url_for('login'))
    
    if not has_file_access(file_id, current_user.id):
        flash('您没有权限访问该文件！', 'danger')
        return redirect(url_for('user_files'))
    
    file = UploadedFile.query.get_or_404(file_id)
    
    if request.method == 'POST':
        question = request.form.get('question', '')
        content = read_file_content(file.file_path)
        
        if question:
            answer = ai_service.answer_question(content, question)
            return jsonify({"response": answer})
        else:
            return jsonify({"response": "请输入您的问题"})
    
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
        visible_file_ids = db.session.query(FileVisibility.file_id).filter(FileVisibility.user_id == current_user.id).subquery()
        files = UploadedFile.query.filter(
            (UploadedFile.visibility == 'all') | 
            (UploadedFile.id.in_(visible_file_ids))
        ).all()
        
        book_contents = []
        for file in files:
            content = read_file_content(file.file_path)
            if content and content != '无法读取文件内容':
                book_contents.append(content)
        
        if book_contents:
            result = ai_service.multi_book_search(book_contents, query)
            search_results.append({
                'source': '综合搜索',
                'content': result
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
        ai_service = request.form.get('ai_service', 'aliyun')
        dashscope_api_key = request.form.get('dashscope_api_key', '')
        openai_api_key = request.form.get('openai_api_key', '')
        
        env_content = f'''# AI服务配置
# 阿里云百炼配置
DASHSCOPE_API_KEY={dashscope_api_key}
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_CHAT_MODEL=qwen-plus

# 备用配置
ALIYUN_ACCESS_KEY_ID=
ALIYUN_ACCESS_KEY_SECRET=
OPENAI_API_KEY={openai_api_key}
OPENAI_API_BASE=https://api.openai.com/v1

# 默认服务设置
DEFAULT_AI_SERVICE={ai_service}
ENCRYPTION_KEY=text_analysis_system_key_2026
'''
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        flash('AI配置已更新！', 'success')
        return redirect(url_for('admin_ai_settings'))
    
    import os
    config = {
        'dashscope_api_key': os.getenv('DASHSCOPE_API_KEY', ''),
        'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
        'ai_service': os.getenv('DEFAULT_AI_SERVICE', 'aliyun')
    }
    
    return render_template('admin/ai_settings.html', config=config)