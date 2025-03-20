import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin


def fetch_options_from_url(url):
    # 获取页面内容
    response = requests.get(url)
    response.encoding = "utf-8"  # 确保中文编码正确

    if response.status_code != 200:
        return f"错误: 无法获取页面，状态码: {response.status_code}"

    # 解析HTML
    soup = BeautifulSoup(response.text, "html.parser")

    # 查找指定的select元素
    select_element = soup.find("select", attrs={"onchange": "location.href=this.value"})

    if not select_element:
        return "错误: 未找到指定的select元素"

    # 提取所有option元素
    options = select_element.find_all("option")

    # 创建结果列表
    result = []

    for option in options:
        value = option.get("value")
        text = option.text.strip()

        if value:
            # 处理相对URL
            if not value.startswith(("http://", "https://")):
                value = urljoin(url, value)

            result.append({"list_url": value, "text": text})  # 使用list_url作为键名

    return result


def save_to_json(data, filename="options.json"):
    # 保存为JSON文件
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return f"数据已保存到 {filename}"


def main():
    url = input("请输入要解析的URL: ")

    result = fetch_options_from_url(url)

    if isinstance(result, str):  # 如果是错误信息
        print(result)
    else:
        filename = input("请输入保存的文件名 (默认: options.json): ") or "options.json"
        print(save_to_json(result, filename))
        print(f"共提取了 {len(result)} 个选项")


if __name__ == "__main__":
    main()
