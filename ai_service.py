import os
import time
import socket
from dotenv import load_dotenv
from encryption import decrypt_string

load_dotenv()

class AIService:
    def __init__(self):
        # 阿里云百炼配置（使用OpenAI兼容模式）
        self.dashscope_api_key = decrypt_string(os.getenv('DASHSCOPE_API_KEY', ''))
        self.qwen_base_url = os.getenv('QWEN_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        self.qwen_model = os.getenv('QWEN_CHAT_MODEL', 'qwen-plus')
        
        # 备用配置
        self.aliyun_access_key_id = decrypt_string(os.getenv('ALIYUN_ACCESS_KEY_ID', ''))
        self.aliyun_access_key_secret = decrypt_string(os.getenv('ALIYUN_ACCESS_KEY_SECRET', ''))
        self.openai_api_key = decrypt_string(os.getenv('OPENAI_API_KEY', ''))
        self.openai_api_base = os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

        # 默认服务类型
        self.service_type = os.getenv('DEFAULT_AI_SERVICE', 'aliyun')

        # 超时设置
        self.timeout = 30  # 缩短超时时间，阿里云响应更快
        self.max_retries = 2

        # 分块分析设置
        self.chunk_size = 4000
        self.max_chunks = 10
        self.overlap_size = 500

        # 知识图谱存储
        self.knowledge_graph = {}

    def get_mock_response(self, prompt):
        """获取模拟响应（当API调用失败时使用）"""
        if '总结' in prompt or '简介' in prompt:
            return """【书籍内容总结】

这是一本书籍的内容总结。由于当前网络环境限制，无法连接到AI服务。

**主要内容：**
- 书籍介绍了核心主题和关键概念
- 包含多个章节，每个章节有独立的主题
- 通过实例和案例帮助读者理解内容

**核心思想：**
- 强调理论与实践相结合
- 提供系统化的知识框架
- 适合初学者和进阶学习者

> 提示：请配置阿里云API密钥以获得更好的分析效果，或检查网络连接后重试。"""

        elif '章节' in prompt or '概要' in prompt:
            return """【章节分析结果】

由于当前网络环境限制，无法连接到AI服务。

**章节结构分析：**
- 第一章：介绍基本概念和背景
- 第二章：深入讲解核心理论
- 第三章：通过实例演示应用
- 第四章：总结和扩展内容

**章节逻辑关系：**
各章节循序渐进，从基础概念到高级应用，形成完整的知识体系。

> 提示：请配置阿里云API密钥以获得更好的分析效果，或检查网络连接后重试。"""

        elif '人物' in prompt or '关系' in prompt:
            return """【人物关系分析】

由于当前网络环境限制，无法连接到AI服务。

**主要人物：**
- 主角：故事核心人物，推动情节发展
- 配角：辅助主角，丰富故事层次
- 反派：制造冲突，推动剧情

**人物关系：**
人物之间存在复杂的关系网络，包括亲情、友情、爱情、仇恨等。

> 提示：请配置阿里云API密钥以获得更好的分析效果，或检查网络连接后重试。"""

        elif '问题' in prompt.lower() or '什么' in prompt or '如何' in prompt:
            return f"""【问题回答】

您的问题：{prompt[:50]}...

由于当前网络环境限制，无法连接到AI服务进行深度分析。

**建议：**
1. 检查网络连接状态
2. 配置阿里云API密钥（国内服务器更稳定）
3. 稍后重试

> 提示：请在管理员端配置阿里云API密钥以获得更好的使用体验。"""

        else:
            return f"""【搜索结果】

搜索关键词：{prompt[:30]}...

由于当前网络环境限制，无法连接到AI服务进行深度搜索。

**建议：**
1. 检查网络连接状态
2. 配置阿里云API密钥（国内服务器更稳定）
3. 稍后重试

> 提示：请在管理员端配置阿里云API密钥以获得更好的使用体验。"""

    def call_qwen_api(self, prompt, max_tokens=4096, temperature=0.7):
        """调用阿里云百炼API（使用OpenAI兼容模式）"""
        if not self.dashscope_api_key:
            return self.get_mock_response(prompt)

        for attempt in range(self.max_retries + 1):
            try:
                socket.setdefaulttimeout(self.timeout)
                from openai import OpenAI

                # 使用阿里云百炼的OpenAI兼容接口
                client = OpenAI(
                    api_key=self.dashscope_api_key,
                    base_url=self.qwen_base_url,
                    timeout=self.timeout
                )

                response = client.chat.completions.create(
                    model=self.qwen_model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature
                )

                return response.choices[0].message.content

            except socket.timeout:
                if attempt < self.max_retries:
                    time.sleep(2)
                    continue
                return self.get_mock_response(prompt)
            except Exception as e:
                error_msg = str(e)
                if attempt < self.max_retries:
                    time.sleep(2)
                    continue
                if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                    return self.get_mock_response(prompt)
                return f"调用阿里云API失败: {error_msg}"

    def call_openai_api(self, prompt, max_tokens=4096, temperature=0.7):
        """调用OpenAI API"""
        if not self.openai_api_key:
            return self.get_mock_response(prompt)

        for attempt in range(self.max_retries + 1):
            try:
                socket.setdefaulttimeout(self.timeout)
                from openai import OpenAI

                client = OpenAI(
                    api_key=self.openai_api_key,
                    base_url=self.openai_api_base,
                    timeout=self.timeout
                )

                response = client.chat.completions.create(
                    model=self.openai_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature
                )

                return response.choices[0].message.content

            except socket.timeout:
                if attempt < self.max_retries:
                    time.sleep(3)
                    continue
                return self.get_mock_response(prompt)
            except Exception as e:
                error_msg = str(e)
                if attempt < self.max_retries:
                    time.sleep(3)
                    continue
                if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                    return self.get_mock_response(prompt)
                return f"调用OpenAI API失败: {error_msg}"

    def generate_response(self, prompt, max_tokens=4096, temperature=0.7):
        """生成AI响应"""
        if self.service_type == 'aliyun' or self.service_type == 'qwen':
            return self.call_qwen_api(prompt, max_tokens, temperature)
        else:
            return self.call_openai_api(prompt, max_tokens, temperature)

    # ==================== 小说专用分析策略 ====================

    def smart_chunk_novel(self, content):
        """智能分块：按章节/语义边界切割，带重叠窗口"""
        chunks = []
        
        chapter_patterns = [
            r'第[零一二三四五六七八九十百千万]+[章节卷部回]',
            r'Chapter [0-9]+',
            r'[0-9]+\.',
            r'^[\u4e00-\u9fa5]{1,3}、',
        ]
        
        import re
        
        paragraphs = content.split('\n')
        chapter_start_indices = []
        
        for i, paragraph in enumerate(paragraphs):
            for pattern in chapter_patterns:
                if re.match(pattern, paragraph.strip()):
                    chapter_start_indices.append(i)
                    break
        
        if chapter_start_indices:
            chapter_start_indices.append(len(paragraphs))
            
            for i in range(len(chapter_start_indices) - 1):
                start = chapter_start_indices[i]
                end = chapter_start_indices[i + 1]
                
                chapter_paragraphs = paragraphs[start:end]
                chapter_text = '\n'.join(chapter_paragraphs)
                
                if len(chapter_text) > self.chunk_size:
                    sub_chunks = self.split_with_overlap(chapter_text)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(chapter_text)
        else:
            chunks = self.split_with_overlap(content)
        
        return chunks[:self.max_chunks]

    def split_with_overlap(self, content):
        """带重叠窗口的分块"""
        chunks = []
        start = 0
        length = len(content)
        
        while start < length:
            end = min(start + self.chunk_size, length)
            
            if end < length:
                boundary = content.rfind('\n', start, end)
                if boundary > start + self.chunk_size // 2:
                    end = boundary
            
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.overlap_size
            
            if start >= length:
                break
        
        return chunks

    def analyze_paragraph_level(self, chunk, chunk_index, total_chunks):
        """段落级分析"""
        prompt = f"""请分析以下小说片段（{chunk_index}/{total_chunks}）：

{chunk[:4000]}

请提取：
1. **场景描述**：时间、地点、环境氛围
2. **人物动作**：主要人物的行为和动作
3. **对话要点**：关键对话内容和含义
4. **情感变化**：人物情感状态和变化
5. **叙事节奏**：这段的紧张程度和节奏

请用简洁的条目列出。
"""
        return self.generate_response(prompt, max_tokens=1500)

    def analyze_chapter_level(self, chunk_analyses, chapter_info):
        """章节级分析"""
        combined = "\n\n".join(chunk_analyses)
        
        prompt = f"""请根据以下对{chapter_info}的各段落分析，整合生成章节总结：

{combined}

请提供：
1. **章节核心事件**：本章发生的主要事件
2. **人物发展**：主要人物在本章的成长/变化
3. **情节推进**：本章如何推动整体剧情
4. **主题深化**：本章如何体现或深化小说主题
5. **关键伏笔**：本章留下的线索或伏笔

请确保分析连贯，逻辑清晰。
"""
        return self.generate_response(prompt, max_tokens=2000)

    def build_knowledge_graph(self, content):
        """构建小说知识图谱"""
        chunks = self.smart_chunk_novel(content)
        character_info = []
        
        for i, chunk in enumerate(chunks):
            prompt = f"""请从以下小说片段中提取人物信息（{i+1}/{len(chunks)}）：

{chunk[:4000]}

请列出：
1. **人物列表**：出现的所有人物及其身份
2. **人物关系**：人物之间的关系（亲情、友情、爱情、敌对、师徒等）
3. **人物特征**：外貌、性格、动机、目标

用结构化的方式输出。
"""
            result = self.generate_response(prompt, max_tokens=1500)
            character_info.append(result)
            time.sleep(0.5)
        
        combined = "\n\n".join(character_info)
        
        prompt = f"""请根据以下各片段的人物分析，整合构建完整的知识图谱：

{combined}

请构建：
1. **人物关系图**：所有主要人物及其关系（用文字描述）
2. **人物档案**：每个人物的详细档案（身份、性格、动机、发展轨迹）
3. **情节时间线**：按时间顺序梳理主要事件
4. **主题关联**：各主题之间的联系和发展

请输出详细的结构化内容。
"""
        knowledge_graph = self.generate_response(prompt, max_tokens=3000)
        self.knowledge_graph['characters'] = knowledge_graph
        
        return knowledge_graph

    def analyze_novel_structure(self, content):
        """分析小说整体结构"""
        chunks = self.smart_chunk_novel(content)
        total_chunks = len(chunks)
        
        paragraph_analyses = []
        for i, chunk in enumerate(chunks):
            analysis = self.analyze_paragraph_level(chunk, i+1, total_chunks)
            paragraph_analyses.append(f"【第{i+1}部分】\n{analysis}")
            time.sleep(0.5)
        
        chapter_summary = self.analyze_chapter_level(paragraph_analyses, f"全书（共{total_chunks}部分）")
        knowledge_graph = self.build_knowledge_graph(content)
        
        final_prompt = f"""请根据以下小说分析结果，生成完整的小说解析报告：

【章节总结】
{chapter_summary}

【知识图谱】
{knowledge_graph}

请整合提供：
1. **故事概述**：完整的故事梗概（约300字）
2. **人物群像**：主要人物介绍和关系网
3. **情节结构**：三幕式结构分析（开端、发展、高潮、结局）
4. **主题深度**：小说探讨的核心主题和思想
5. **叙事特色**：写作风格、叙事手法、视角选择
6. **亮点与价值**：小说的独特之处和文学价值

请输出详细、深入的分析报告。
"""
        final_report = self.generate_response(final_prompt, max_tokens=4000)
        
        return {
            'paragraph_analyses': paragraph_analyses,
            'chapter_summary': chapter_summary,
            'knowledge_graph': knowledge_graph,
            'final_report': final_report
        }

    def novel_character_analysis(self, content):
        """小说人物深度分析"""
        chunks = self.smart_chunk_novel(content)
        
        all_characters = []
        for i, chunk in enumerate(chunks):
            prompt = f"""从以下小说片段中提取人物信息（{i+1}/{len(chunks)}）：

{chunk[:4000]}

请列出所有出现的人物，包括：
- 姓名/称呼
- 身份/职业
- 性格特征
- 与其他人物的关系
- 在本片段中的行为和表现
"""
            result = self.generate_response(prompt, max_tokens=1500)
            all_characters.append(result)
            time.sleep(0.5)
        
        combined = "\n\n".join(all_characters)
        
        prompt = f"""请根据以下各片段的人物信息，生成完整的人物分析报告：

{combined}

请提供：
1. **主要人物列表**：列出所有重要人物
2. **人物关系图**：描述人物之间的复杂关系网络
3. **核心人物深度剖析**：
   - 主角：成长弧线、内心挣扎、人物弧光
   - 配角：功能定位、对主角的影响
   - 反派：动机分析、复杂性
4. **人物塑造手法**：作者如何刻画人物
5. **人物关系演变**：随剧情发展的关系变化

请输出详细的人物分析报告。
"""
        return self.generate_response(prompt, max_tokens=3500)

    def novel_plot_analysis(self, content):
        """小说情节分析"""
        chunks = self.smart_chunk_novel(content)
        
        plot_points = []
        for i, chunk in enumerate(chunks):
            prompt = f"""分析以下小说片段的情节（{i+1}/{len(chunks)}）：

{chunk[:4000]}

请分析：
1. **事件内容**：发生了什么
2. **冲突类型**：内部冲突/外部冲突
3. **情节功能**：铺垫/发展/转折/高潮/收尾
4. **伏笔与呼应**：是否有伏笔或前后呼应
5. **节奏变化**：紧张度和节奏

用简洁的条目列出。
"""
            result = self.generate_response(prompt, max_tokens=1500)
            plot_points.append(result)
            time.sleep(0.5)
        
        combined = "\n\n".join(plot_points)
        
        prompt = f"""请根据以下各片段的情节分析，生成完整的情节分析报告：

{combined}

请提供：
1. **情节时间线**：按时间顺序梳理主要事件
2. **三幕式结构分析**：
   - 第一幕（开端）：引入、激发事件
   - 第二幕（发展）：上升动作、中点转折
   - 第三幕（高潮结局）：高潮、结局
3. **冲突体系**：主要冲突类型和解决方式
4. **情节节奏**：整体节奏变化和节奏控制
5. **伏笔与呼应**：全书中的伏笔设置和回收
6. **情节漏洞**：逻辑不一致或未解释的地方

请输出详细的情节分析报告。
"""
        return self.generate_response(prompt, max_tokens=3500)

    def novel_theme_analysis(self, content):
        """小说主题分析"""
        chunks = self.smart_chunk_novel(content)
        
        theme_elements = []
        for i, chunk in enumerate(chunks):
            prompt = f"""分析以下小说片段的主题元素（{i+1}/{len(chunks)}）：

{chunk[:4000]}

请分析：
1. **主题关键词**：出现的主题相关词汇和概念
2. **象征意义**：物品、场景、颜色的象征意义
3. **主题表达**：如何体现小说主题
4. **价值观**：传递的价值观念

用简洁的条目列出。
"""
            result = self.generate_response(prompt, max_tokens=1500)
            theme_elements.append(result)
            time.sleep(0.5)
        
        combined = "\n\n".join(theme_elements)
        
        prompt = f"""请根据以下各片段的主题元素分析，生成完整的主题分析报告：

{combined}

请提供：
1. **核心主题**：小说探讨的主要主题（列出3-5个）
2. **主题层次**：表面主题和深层主题
3. **主题发展**：主题如何随情节发展而深化
4. **象征体系**：关键象征物及其含义
5. **价值探讨**：小说对人性、社会、人生的思考
6. **主题共鸣**：读者可能产生的共鸣点

请输出详细的主题分析报告。
"""
        return self.generate_response(prompt, max_tokens=3500)

    # ==================== 通用分析方法 ====================

    def summarize_book(self, content, max_tokens=2000):
        """总结书籍内容"""
        if not content or len(content.strip()) == 0:
            return "书籍内容为空，无法进行分析。"

        chunks = self.smart_chunk_novel(content)

        if len(chunks) == 1:
            prompt = f"""请帮我总结以下书籍的内容：

{content[:5000]}

请提供：
1. 书籍简介（不超过200字）
2. 主要人物/角色介绍
3. 核心主题和思想
4. 故事梗概（如果是小说）或内容大纲（如果是教材）
"""
            return self.generate_response(prompt, max_tokens)

        total_chunks = len(chunks)
        chunk_summaries = []

        for i, chunk in enumerate(chunks):
            chunk_prompt = f"""请分析以下书籍片段（{i+1}/{total_chunks}）的内容：

{chunk[:4000]}

请提供：
1. 本片段的核心内容
2. 主要人物/概念
3. 关键情节/要点（用简洁的bullet points）
"""
            summary = self.generate_response(chunk_prompt, max_tokens=1500)
            chunk_summaries.append(f"【第{i+1}部分分析】\n{summary}")
            time.sleep(0.5)

        combined_summaries = "\n\n".join(chunk_summaries)

        final_prompt = f"""请根据以下书籍各部分的分析，汇总生成全书的完整总结：

{combined_summaries}

请整合所有分析，提供：
1. 书籍完整简介（约200字）
2. 主要人物/角色完整列表
3. 核心主题和思想
4. 全书完整故事梗概/内容大纲
5. 书籍的价值和意义

请确保总结连贯完整，涵盖全书内容。
"""
        return self.generate_response(final_prompt, max_tokens=2500)

    def analyze_chapters(self, content, max_tokens=3000):
        """分析书籍章节结构"""
        if not content or len(content.strip()) == 0:
            return "书籍内容为空，无法进行分析。"

        chunks = self.smart_chunk_novel(content)

        if len(chunks) == 1:
            prompt = f"""请帮我分析以下书籍的章节结构：

{content[:8000]}

请提供：
1. 章节划分（如果能识别）
2. 每一章节的梗概/要点
3. 章节之间的逻辑关系
"""
            return self.generate_response(prompt, max_tokens)

        total_chunks = len(chunks)
        chapter_analysis = []

        for i, chunk in enumerate(chunks):
            chunk_prompt = f"""请分析以下书籍片段（{i+1}/{total_chunks}）的章节结构：

{chunk[:4000]}

请识别：
1. 本片段涉及的章节
2. 每章节的核心要点（简洁列出）
3. 章节间的承接关系
"""
            analysis = self.generate_response(chunk_prompt, max_tokens=1500)
            chapter_analysis.append(f"【第{i+1}部分章节分析】\n{analysis}")
            time.sleep(0.5)

        combined_analysis = "\n\n".join(chapter_analysis)

        final_prompt = f"""请根据以下书籍各部分的章节分析，整合生成全书完整的章节结构分析：

{combined_analysis}

请整合所有分析，提供：
1. 全书章节完整划分
2. 每章节的详细梗概和要点
3. 章节间的逻辑关系和整体架构
4. 各章节的承接和递进关系

请确保章节结构清晰，逻辑连贯。
"""
        return self.generate_response(final_prompt, max_tokens=3500)

    def answer_question(self, content, question, max_tokens=2000):
        """根据书籍内容回答问题"""
        if not content or len(content.strip()) == 0:
            return "书籍内容为空，无法回答问题。"

        chunks = self.smart_chunk_novel(content)

        if len(chunks) == 1:
            prompt = f"""根据以下书籍内容回答问题：

书籍内容：
{content[:10000]}

问题：{question}

请基于书籍内容给出详细的回答，如果书籍中没有相关信息，请说明。
"""
            return self.generate_response(prompt, max_tokens)

        total_chunks = len(chunks)
        relevant_info = []

        for i, chunk in enumerate(chunks):
            chunk_prompt = f"""根据以下书籍片段（{i+1}/{total_chunks}）回答问题：

书籍片段：
{chunk[:4000]}

问题：{question}

如果本片段中有相关信息，请提供相关内容片段和分析；如果没有，请简短说明"本片段无相关内容"。
"""
            answer = self.generate_response(chunk_prompt, max_tokens=1000)
            if "无相关内容" not in answer and "本片段无" not in answer:
                relevant_info.append(f"【来自第{i+1}部分】\n{answer}")
            time.sleep(0.5)

        if not relevant_info:
            return f"在整本书中未找到与「{question}」直接相关的内容。\n\n建议：\n1. 尝试使用更general的关键词\n2. 换个角度提问\n3. 使用全局搜索功能在所有藏书中查找"

        combined_info = "\n\n".join(relevant_info)

        final_prompt = f"""根据以下从书籍各部分找到的相关信息，回答问题：

{combined_info}

原问题：{question}

请整合所有相关信息，给出完整、准确的回答。如果信息不足以完全回答问题，请基于现有信息给出最佳答案，并指出信息的局限性。
"""
        return self.generate_response(final_prompt, max_tokens=2000)

    def search_content(self, content, query, max_tokens=2000):
        """在书籍内容中搜索相关信息"""
        if not content or len(content.strip()) == 0:
            return "书籍内容为空，无法搜索。"

        chunks = self.smart_chunk_novel(content)

        if len(chunks) == 1:
            prompt = f"""请在以下书籍内容中搜索与"{query}"相关的信息：

书籍内容：
{content[:10000]}

请提供：
1. 与"{query}"相关的内容片段
2. 相关内容在书中的位置（章节/段落）
3. 对相关内容的解释和分析
"""
            return self.generate_response(prompt, max_tokens)

        total_chunks = len(chunks)
        search_results = []

        for i, chunk in enumerate(chunks):
            chunk_prompt = f"""在以下书籍片段（{i+1}/{total_chunks}）中搜索与"{query}"相关的信息：

{chunk[:4000]}

请提供：
1. 相关内容片段（如果有）
2. 在本片段中的位置
3. 对相关内容的简要分析
"""
            result = self.generate_response(chunk_prompt, max_tokens=1000)
            if "无相关内容" not in result and "未找到" not in result:
                search_results.append(f"【第{i+1}部分搜索结果】\n{result}")
            time.sleep(0.5)

        if not search_results:
            return f"在本书中未找到与「{query}」直接相关的内容。\n\n尝试：\n1. 使用更general的关键词\n2. 尝试同义词搜索\n3. 使用全局搜索在所有藏书中查找"

        combined_results = "\n\n".join(search_results)

        final_prompt = f"""请根据以下从书籍各部分搜索到的与「{query}」相关的信息，进行整合：

{combined_results}

请整合提供：
1. 全书中与"{query}"相关的所有内容片段
2. 各片段的来源位置
3. 综合分析和总结
"""
        return self.generate_response(final_prompt, max_tokens=2500)

    def multi_book_search(self, book_contents, query, max_tokens=3000):
        """在多本书籍中搜索相关信息"""
        if not book_contents:
            return "没有书籍可供搜索。"

        total_books = len(book_contents)
        book_results = []

        for i, content in enumerate(book_contents):
            if not content or len(content.strip()) == 0:
                continue

            book_prompt = f"""在以下书籍（书籍{i+1}/{total_books}）中搜索与"{query}"相关的信息：

{content[:3000]}

请简要提供：
1. 是否找到相关内容（是/否）
2. 相关内容片段（如果有）
3. 在本书中的位置
"""
            result = self.generate_response(book_prompt, max_tokens=1000)
            book_results.append(f"【书籍{i+1}】\n{result}")
            time.sleep(0.5)

        if not book_results:
            return f"在所有{len(book_contents)}本书中均未找到与「{query}」相关的内容。"

        combined = "\n\n".join(book_results)

        final_prompt = f"""请根据以下在{len(book_contents)}本书籍中的搜索结果，整合提供与「{query}」相关的综合分析：

{combined}

请整合提供：
1. 哪些书籍包含相关内容
2. 每本书中的关键相关内容片段
3. 跨书籍的综合分析和总结
4. 对"{query}"的整体认知
"""
        return self.generate_response(final_prompt, max_tokens=3000)