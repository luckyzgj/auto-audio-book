from openai import OpenAI
from dotenv import load_dotenv
import os
import time

load_dotenv(override=True)

# 定义文件名变量
API_KEYS_FILE = "api_keys2.txt"
API_KEYS_ERROR_FILE = "api_keys_error2.txt"


def test_api_key(api_key):
    try:
        client = OpenAI(api_key=api_key.strip(), base_url=os.getenv("GEMINI_API_URL"))
        response = client.models.list()

        if len(response.data) > 0:
            first_model = response.data[0]
            # 更详细的模型属性检查
            required_attrs = ["id", "created", "object"]
            missing_attrs = [
                attr for attr in required_attrs if not hasattr(first_model, attr)
            ]

            if not missing_attrs:
                model_info = f"可以走通，找到{len(response.data)}个模型"
                return True, model_info
            else:
                return False, f"返回数据缺少必要属性: {', '.join(missing_attrs)}"
        return False, "返回模型列表为空"
    except Exception as e:
        error_message = str(e)
        if "Permission denied" in error_message:
            return False, "权限被拒绝"
        elif "Invalid API key" in error_message:
            return False, "无效的API密钥"
        elif "Request timed out" in error_message:
            return False, "请求超时"
        return False, f"错误: {error_message}"


# 读取API密钥文件
try:
    with open(API_KEYS_FILE, "r") as file:
        api_keys = file.readlines()
except FileNotFoundError:
    print(f"找不到 {API_KEYS_FILE} 文件")
    exit(1)

# 统计有效和无效的密钥
valid_keys = []
invalid_keys = []

# 循环所有的API密钥
for api_key in api_keys:
    api_key = api_key.strip()
    if not api_key:  # 跳过空行
        continue

    is_valid, message = test_api_key(api_key)
    if is_valid:
        valid_keys.append(api_key)
        print(f"✅ API密钥 {api_key} - {message}")
    else:
        invalid_keys.append((api_key, message))
        print(f"❌ API密钥 {api_key} - {message}")
    time.sleep(0.1)

# 打印统计信息
print("\n统计信息:")
print(f"总计密钥数: {len(api_keys)}")
print(f"有效密钥数: {len(valid_keys)}")
print(f"无效密钥数: {len(invalid_keys)}")

# 保存有效的API密钥到文件
with open(API_KEYS_FILE, "w") as file:
    for key in valid_keys:
        file.write(key + "\n")

# 保存无效的API密钥到错误文件
with open(API_KEYS_ERROR_FILE, "w") as file:
    for key, message in invalid_keys:
        file.write(f"{key} - {message}\n")

print(f"\n有效密钥已保存到 {API_KEYS_FILE}")
print(f"无效密钥已保存到 {API_KEYS_ERROR_FILE}")
