import json
import os
from collections import defaultdict
from typing import Dict, List

def get_users_list(book_id: str) -> None:
    """
    读取指定书籍ID的所有章节JSON文件，统计角色信息并保存结果
    
    Args:
        book_id: 书籍ID
    """
    # 角色统计信息
    characters_info = defaultdict(lambda: {"gender": "", "lines_count": 0})
    
    # 构建章节文件目录路径
    chapters_dir = f"audio/{book_id}/chapter"
    
    # 确保目录存在
    if not os.path.exists(chapters_dir):
        print(f"目录不存在: {chapters_dir}")
        return
    
    # 遍历所有JSON文件
    for filename in os.listdir(chapters_dir):
        if not filename.endswith('.json'):
            continue
            
        file_path = os.path.join(chapters_dir, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                dialogues = json.load(f)
                
            # 处理每个对话
            for dialogue in dialogues:
                if not isinstance(dialogue, dict):
                    continue
                    
                character = dialogue.get("type", "")
                gender = dialogue.get("sex", "")
                
                if character:
                    characters_info[character]["gender"] = gender
                    characters_info[character]["lines_count"] += 1
                    
        except Exception as e:
            print(f"处理文件 {filename} 时出错: {str(e)}")
    
    # 转换为列表并排序
    characters_list = [
        {
            "name": name,
            "gender": info["gender"],
            "lines_count": info["lines_count"]
        }
        for name, info in characters_info.items()
    ]
    
    # 按台词数量降序排序
    characters_list.sort(key=lambda x: x["lines_count"], reverse=True)
    
    # 保存结果
    output_dir = f"audio/{book_id}"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "characters.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(characters_list, f, ensure_ascii=False, indent=2)
    
    print(f"角色统计信息已保存到: {output_file}")

if __name__ == "__main__":
    # 测试用例
    book_id = "115690"
    get_users_list(book_id)

