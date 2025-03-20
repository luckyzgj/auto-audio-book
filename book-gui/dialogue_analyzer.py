"""
对话分析模块，处理小说章节中的对话分析，提取角色、性别和对话内容
"""

import re
import json
import time
import threading
import random
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from tqdm import tqdm

# 导入自定义模块
from config import (
    DEFAULT_AI_NAME,
    DEFAULT_API_BASE_URL,
    DEFAULT_AI_MODEL,
    DIALOGUE_ANALYSIS_PROMPT,
    MAX_RETRY_COUNT,
    RETRY_DELAY,
)


class DialogueAnalyzer:
    """对话分析器，用于分析小说章节中的对话内容"""

    def __init__(self, db_manager=None):
        """初始化对话分析器"""
        self.db_manager = db_manager
        self.ai_name = DEFAULT_AI_NAME
        self.api_base_url = DEFAULT_API_BASE_URL
        self.model = DEFAULT_AI_MODEL
        self.prompt = DIALOGUE_ANALYSIS_PROMPT

        # 用于保存API密钥列表
        self.api_keys = []

        # 如果提供了数据库管理器，尝试加载API密钥
        if self.db_manager and self.db_manager.is_connected():
            self.load_api_keys_from_db()

    def load_api_keys_from_db(self):
        """从数据库加载API密钥列表"""
        if not self.db_manager or not self.db_manager.is_connected():
            return False

        try:
            # 获取指定AI名称的所有API密钥
            api_key_list = self.db_manager.get_api_keys(self.ai_name)
            if api_key_list:
                self.api_keys = [
                    key.get("api_key") for key in api_key_list if key.get("api_key")
                ]
                return True
            return False
        except Exception as e:
            print(f"从数据库加载API密钥失败: {str(e)}")
            return False

    def has_valid_api_keys(self):
        """检查是否有有效的API密钥"""
        return len(self.api_keys) > 0

    def get_random_api_key(self):
        """获取随机API密钥，用于负载均衡"""
        if not self.api_keys:
            return None
        return random.choice(self.api_keys)

    def create_client(self, api_key=None):
        """创建AI客户端"""
        if not api_key:
            api_key = self.get_random_api_key()

        if not api_key:
            return None

        try:
            return OpenAI(api_key=api_key, base_url=self.api_base_url)
        except Exception as e:
            print(f"创建AI客户端失败: {str(e)}")
            return None

    def analyze_text_chunk(
        self,
        chunk_text,
        client=None,
        max_retries=MAX_RETRY_COUNT,
        retry_delay=RETRY_DELAY,
    ):
        """分析文本块中的对话"""
        if not client:
            client = self.create_client()

        if not client:
            return None, "未能创建AI客户端"

        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.prompt},
                        {"role": "user", "content": chunk_text},
                    ],
                )

                content = response.choices[0].message.content
                # 清理JSON格式
                content = re.sub(r"```json\n?|\n?```", "", content)

                try:
                    result = json.loads(content)
                    # 验证结果非空
                    if result and isinstance(result, list) and len(result) > 0:
                        return result, None
                    else:
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                        continue
                except json.JSONDecodeError:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    continue

            except Exception as e:
                error_msg = f"API请求错误: {str(e)}"
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    return None, error_msg

        return None, "达到最大重试次数，分析失败"

    def analyze_chapter(
        self,
        chapter_content,
        callback=None,
        max_retries=MAX_RETRY_COUNT,
        retry_delay=RETRY_DELAY,
    ):
        """分析章节内容，提取对话信息"""
        if not self.has_valid_api_keys():
            return None, "未找到有效的API密钥"

        # 将文本按行分割
        lines = chapter_content.split("\n")

        # 检查是否需要分块处理
        if len(lines) > 50:
            # 分割成每块50行
            chunks = [lines[i : i + 50] for i in range(0, len(lines), 50)]
            all_results = []

            if callback:
                callback(f"文本过长，已分割为{len(chunks)}个块进行处理")

            # 处理每个块
            for i, chunk in enumerate(chunks):
                chunk_content = "\n".join(chunk)
                if callback:
                    callback(f"处理第{i+1}/{len(chunks)}块...")

                # 创建新的客户端
                client = self.create_client()
                if not client:
                    return None, "创建AI客户端失败"

                # 处理当前块
                chunk_result, error = self.analyze_text_chunk(
                    chunk_content, client, max_retries, retry_delay
                )

                # 将结果合并
                if chunk_result:
                    all_results.extend(chunk_result)
                elif error:
                    if callback:
                        callback(f"处理块{i+1}失败: {error}")
                    # 继续处理下一块，而不是完全失败

            if callback:
                callback(f"所有块处理完成，共获取{len(all_results)}个对话记录")

            if all_results:
                return all_results, None
            else:
                return None, "所有块处理均失败"
        else:
            # 创建客户端
            client = self.create_client()
            if not client:
                return None, "创建AI客户端失败"

            # 直接处理整个内容
            return self.analyze_text_chunk(
                chapter_content, client, max_retries, retry_delay
            )

    def batch_analyze_chapters(self, chapters, callback=None, max_workers=5):
        """批量分析多个章节的对话"""
        if not chapters:
            if callback:
                callback("没有章节需要分析")
            return {}

        if not self.has_valid_api_keys():
            if callback:
                callback("未找到有效的API密钥")
            return {}

        # 结果字典
        results = {}

        # 计数器
        total = len(chapters)
        completed = 0
        success_count = 0
        fail_count = 0

        # 线程锁
        lock = threading.Lock()

        def process_chapter(chapter):
            nonlocal completed, success_count, fail_count

            # 获取章节内容
            chapter_content = "\n".join(chapter.get("content", []))
            if not chapter_content:
                with lock:
                    completed += 1
                    if callback:
                        callback(
                            f"跳过无内容章节: {chapter.get('chapter_title')} ({completed}/{total})"
                        )
                return

            # 分析章节内容
            result, error = self.analyze_chapter(
                chapter_content,
                callback=lambda msg: (
                    callback(f"{chapter.get('chapter_title')}: {msg}")
                    if callback
                    else None
                ),
            )

            with lock:
                completed += 1

                if result:
                    # 保存结果
                    chapter_url = chapter.get("chapter_url", "")
                    results[chapter_url] = result
                    success_count += 1

                    if callback:
                        callback(
                            f"分析成功: {chapter.get('chapter_title')}，对话数: {len(result)} ({completed}/{total})"
                        )
                else:
                    fail_count += 1
                    if callback:
                        callback(
                            f"分析失败: {chapter.get('chapter_title')} - {error} ({completed}/{total})"
                        )

                # 控制请求速率
                time.sleep(0.5)

        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            futures = []
            for chapter in chapters:
                future = executor.submit(process_chapter, chapter)
                futures.append(future)

            # 等待所有任务完成
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    if callback:
                        callback(f"任务执行出错: {str(e)}")

        if callback:
            callback(f"对话分析完成，成功: {success_count}, 失败: {fail_count}")

        return results
