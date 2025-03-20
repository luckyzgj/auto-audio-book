import json
import random


def fpjs(book_id: str):
    # 读取角色列表
    with open(f"audio/{book_id}/characters.json", "r", encoding="utf-8") as f:
        characters = json.load(f)
    # 读取用户列表
    with open(f"audio/{book_id}/user.json", "r", encoding="utf-8") as f:
        user = json.load(f)
    # 读取模型列表
    with open(f"audio/model.json", "r", encoding="utf-8") as f:
        model = json.load(f)

    # 获取旁白模型
    narrator_model = user.get("旁白", "")

    # 按性别分组模型
    male_models = [m["name"] for m in model if m["gender"] == "男"]
    female_models = [m["name"] for m in model if m["gender"] == "女"]

    # 遍历每个角色
    for character in characters:
        name = character["name"]

        # 规则1: 如果已分配模型（非空字符串）则跳过
        if name in user and user[name]:
            continue

        # 规则3: 如果台词数量小于50，使用旁白模型
        if character["lines_count"] < 50:
            user[name] = narrator_model
            continue

        # 规则2: 根据性别随机选择模型
        if character["gender"] == "男" and male_models:
            user[name] = random.choice(male_models)
        elif character["gender"] == "女" and female_models:
            user[name] = random.choice(female_models)
        else:
            # 如果没有对应性别的模型，设置为空字符串
            user[name] = narrator_model

    # 保存更新后的user.json
    with open(f"audio/{book_id}/user.json", "w", encoding="utf-8") as f:
        json.dump(user, f, ensure_ascii=False, indent=4)

    return user


if __name__ == "__main__":
    fpjs("115690")
    pass
