"""
配置文件，包含应用程序的全局配置和常量
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=True)

# 应用程序名称和版本
APP_NAME = "小说章节爬虫与对话分析工具"
APP_VERSION = "1.0.0"

# 数据库默认配置
DEFAULT_DB_HOST = "localhost"
DEFAULT_DB_PORT = "27017"
DEFAULT_DB_NAME = "novels"
DEFAULT_AUTH_DB = "admin"

# 爬虫配置
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
MAX_RETRY_COUNT = 3
RETRY_DELAY = 2
MAX_DOWNLOAD_THREADS = 5

# AI 对话分析配置
DEFAULT_AI_NAME = "GeminiAI"
DEFAULT_AI_MODEL = "gemini-2.0-flash"
DEFAULT_API_BASE_URL = os.getenv(
    "GEMINI_API_URL", "https://generativelanguage.googleapis.com"
)

# # 对话分析提示词
# DIALOGUE_ANALYSIS_PROMPT = """
# 我发给你的是一章小说，请帮我仔细分析出来每句话都是谁说的，然后以json的形式给我
# 请以json的形式给我
# type为角色的名字 sex为角色性别 text为 角色这句话，性别有 男 女 中，如果不知道是什么性别就选中性
# 旁白固定式中性
# Use this JSON schema:
# Recipe ={
#     type:"xxx",
#     sex:"",
#     text:"xxxxxxx"
# }
# Return: list[Recipe]
# """

# 对话分析提示词
DIALOGUE_ANALYSIS_PROMPT = """
请仔细阅读以下小说章节，提取所有对话和旁白，并按照以下JSON格式输出：
# Use this JSON schema:
Recipe ={[
  {
    "type": "说话人",
    "sex": "男/女/中",
    "text": "该说话人所说的内容"
  },
  ...
]
# Return: list[Recipe]
对于无法判断性别的角色，请将 "sex" 标记为 "中"。
对于旁白描述，请将 "type" 标记为 "旁白"，"sex" 标记为 "中"。
请注意区分说话人和其所说的内容。如果同一段话中有多个人说话，请拆分成多个 JSON 对象。例如：
小说原文：“你好，”张三说，“李四吃饭了吗？”,“还没呢。”
应输出为：
[
  {
    "type": "张三",
    "sex": "男",
    "text": "你好"
  },
  {
    "type": "张三",
    "sex": "男",
    "text": "吃饭了吗？"
  },
  {
    "type": "李四",
    "sex": "男",
    "text": "还没呢。"
  }
]
"""



# 文件路径配置
API_KEYS_FILE = "api_keys.txt"

# UI 配置
UI_DEFAULT_WIDTH = 900
UI_DEFAULT_HEIGHT = 700
UI_MIN_WIDTH = 800
UI_MIN_HEIGHT = 600
UI_PADDING = 10
