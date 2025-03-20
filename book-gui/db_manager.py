"""
数据库管理模块，提供MongoDB数据库的连接和操作功能
"""

import time
from datetime import datetime
from pymongo import MongoClient, UpdateOne
from bson import ObjectId


class MongoDBManager:
    """MongoDB数据库管理类"""

    def __init__(self):
        """初始化MongoDB管理器"""
        self.client = None
        self.db = None
        self.connected = False
        self.last_config = None  # 保存最后一次的连接配置

    def connect(self, connection_string, db_name):
        """连接到MongoDB数据库"""
        try:
            # 如果已连接，先断开
            if self.client:
                self.client.close()

            # 创建新连接
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            # 检查连接是否成功
            self.client.server_info()
            self.db = self.client[db_name]
            self.connected = True
            return True, "连接成功"
        except Exception as e:
            self.connected = False
            return False, f"连接失败: {str(e)}"

    def reconnect(self):
        """使用上次的配置重新连接"""
        if not self.last_config:
            return False, "没有保存的连接配置"

        return self.connect(
            self.last_config["connection_string"], self.last_config["db_name"]
        )

    def disconnect(self):
        """断开数据库连接"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            self.connected = False

    def is_connected(self):
        """检查是否已连接到数据库"""
        return self.connected

    def save_connection_config(self, config):
        """保存连接配置"""
        self.last_config = config

    def save_novel(self, novel_data):
        """保存或更新小说信息"""
        if not self.is_connected():
            return False, None, "未连接到数据库"

        try:
            novels_collection = self.db.novels

            # 如果小说已存在（根据名称查找），则更新
            existing_novel = novels_collection.find_one({"name": novel_data["name"]})

            if existing_novel:
                # 更新现有小说
                novel_data["_id"] = existing_novel["_id"]
                novel_data["created_at"] = existing_novel["created_at"]
                novel_data["updated_at"] = datetime.now()

                result = novels_collection.replace_one(
                    {"_id": existing_novel["_id"]}, novel_data
                )
                return True, existing_novel["_id"], "小说信息已更新"
            else:
                # 插入新小说
                novel_data["created_at"] = datetime.now()
                novel_data["updated_at"] = datetime.now()

                result = novels_collection.insert_one(novel_data)
                return True, result.inserted_id, "小说信息已保存"

        except Exception as e:
            return False, None, f"保存小说信息失败: {str(e)}"

    def save_chapters(self, novel_id, chapters):
        """保存章节信息"""
        if not self.is_connected():
            return False, "未连接到数据库"

        try:
            chapters_collection = self.db.chapters
            now = datetime.now()
            new_count = 0
            update_count = 0

            for chapter in chapters:
                # 添加小说ID和时间戳
                chapter_data = {
                    "novel_id": novel_id,
                    "volume": chapter.get("group", ""),
                    "title": chapter.get("chapter_title", ""),
                    "url": chapter.get("chapter_url", ""),
                    "word_count": chapter.get("word_count", 0),  # 添加字数字段
                    "content": chapter.get("content", []),  # 添加内容字段
                    "created_at": now,
                    "updated_at": now,
                }

                # 检查章节是否已存在
                existing_chapter = chapters_collection.find_one(
                    {"novel_id": novel_id, "url": chapter_data["url"]}
                )

                if not existing_chapter:
                    # 新增章节
                    chapters_collection.insert_one(chapter_data)
                    new_count += 1
                elif "word_count" in chapter and chapter["word_count"] > 0:
                    # 如果已存在但有新的字数统计，则更新
                    if existing_chapter.get("word_count", 0) != chapter["word_count"]:
                        chapters_collection.update_one(
                            {"_id": existing_chapter["_id"]},
                            {
                                "$set": {
                                    "word_count": chapter["word_count"],
                                    "content": chapter.get(
                                        "content", []
                                    ),  # 添加内容更新
                                    "updated_at": now,
                                }
                            },
                        )
                        update_count += 1

            return True, f"已保存 {new_count} 个新章节，更新 {update_count} 个章节"

        except Exception as e:
            return False, f"保存章节失败: {str(e)}"

    def save_chapter_dialogues(self, chapter_id, dialogues):
        """保存章节对话分析结果"""
        if not self.is_connected():
            return False, "未连接到数据库"

        try:
            # 更新章节记录，添加对话分析结果
            result = self.db.chapters.update_one(
                {"_id": chapter_id},
                {
                    "$set": {
                        "dialogues": dialogues,
                        "dialogue_updated_at": datetime.now(),
                    }
                },
            )

            if result.modified_count > 0:
                return True, "对话分析结果已保存"
            else:
                return False, "未找到章节或无需更新"
        except Exception as e:
            return False, f"保存对话分析结果失败: {str(e)}"

    def save_batch_dialogues(self, chapter_dialogue_map):
        """批量保存多个章节的对话分析结果"""
        if not self.is_connected():
            return False, "未连接到数据库"

        try:
            chapters_collection = self.db.chapters
            update_operations = []
            now = datetime.now()

            for chapter_id, dialogues in chapter_dialogue_map.items():
                operation = UpdateOne(
                    filter={"_id": chapter_id},
                    update={
                        "$set": {
                            "dialogues": dialogues,
                            "dialogue_updated_at": now,
                        }
                    },
                )
                update_operations.append(operation)

            if update_operations:
                result = chapters_collection.bulk_write(update_operations)
                return True, f"已更新 {result.modified_count} 个章节的对话分析结果"
            else:
                return False, "没有需要更新的章节"

        except Exception as e:
            return False, f"批量保存对话分析结果失败: {str(e)}"

    def get_novels(self):
        """获取所有小说列表"""
        if not self.is_connected():
            return []

        try:
            novels_collection = self.db.novels
            return list(novels_collection.find())
        except Exception as e:
            print(f"获取小说列表失败: {str(e)}")
            return []

    def get_novel(self, novel_id):
        """获取指定小说信息"""
        if not self.is_connected():
            return None

        try:
            novels_collection = self.db.novels
            return novels_collection.find_one({"_id": ObjectId(novel_id)})
        except Exception as e:
            print(f"获取小说信息失败: {str(e)}")
            return None

    def get_chapters(self, novel_id):
        """获取指定小说的所有章节"""
        if not self.is_connected():
            return []

        try:
            chapters_collection = self.db.chapters
            return list(chapters_collection.find({"novel_id": ObjectId(novel_id)}))
        except Exception as e:
            print(f"获取章节列表失败: {str(e)}")
            return []

    def delete_novel(self, novel_id):
        """删除小说及其章节"""
        if not self.is_connected():
            return False, "未连接到数据库"

        try:
            # 转换为ObjectId
            novel_id = ObjectId(novel_id)

            # 删除小说
            self.db.novels.delete_one({"_id": novel_id})

            # 删除相关章节
            result = self.db.chapters.delete_many({"novel_id": novel_id})

            return True, f"已删除小说及其 {result.deleted_count} 个章节"
        except Exception as e:
            return False, f"删除小说失败: {str(e)}"

    # API密钥管理相关方法
    def save_api_key(self, api_key, ai_name="GeminiAI", is_default=False):
        """保存API密钥到数据库"""
        if not self.is_connected():
            return False, "未连接到数据库"

        try:
            api_keys_collection = self.db.api_keys
            now = datetime.now()

            # 检查API密钥是否已存在
            existing_key = api_keys_collection.find_one({"api_key": api_key})

            if existing_key:
                # 更新现有API密钥
                api_keys_collection.update_one(
                    {"_id": existing_key["_id"]},
                    {
                        "$set": {
                            "ai_name": ai_name,
                            "is_default": is_default,
                            "updated_at": now,
                        }
                    },
                )

                # 如果设为默认，取消其他默认
                if is_default:
                    api_keys_collection.update_many(
                        {"_id": {"$ne": existing_key["_id"]}},
                        {"$set": {"is_default": False}},
                    )

                return True, "API密钥已更新"
            else:
                # 插入新API密钥
                api_keys_collection.insert_one(
                    {
                        "api_key": api_key,
                        "ai_name": ai_name,
                        "is_default": is_default,
                        "created_at": now,
                        "updated_at": now,
                    }
                )

                # 如果设为默认，取消其他默认
                if is_default:
                    api_keys_collection.update_many(
                        {"api_key": {"$ne": api_key}}, {"$set": {"is_default": False}}
                    )

                return True, "API密钥已保存"

        except Exception as e:
            return False, f"保存API密钥失败: {str(e)}"

    def get_api_keys(self, ai_name="GeminiAI"):
        """获取指定AI名称的所有API密钥"""
        if not self.is_connected():
            return []

        try:
            api_keys_collection = self.db.api_keys
            return list(api_keys_collection.find({"ai_name": ai_name}))
        except Exception as e:
            print(f"获取API密钥列表失败: {str(e)}")
            return []

    def get_default_api_key(self, ai_name="GeminiAI"):
        """获取默认API密钥"""
        if not self.is_connected():
            return None

        try:
            api_keys_collection = self.db.api_keys
            key = api_keys_collection.find_one({"ai_name": ai_name, "is_default": True})
            if key:
                return key

            # 如果没有默认密钥，返回第一个找到的密钥
            return api_keys_collection.find_one({"ai_name": ai_name})
        except Exception as e:
            print(f"获取默认API密钥失败: {str(e)}")
            return None

    def delete_api_key(self, api_key_id):
        """删除API密钥"""
        if not self.is_connected():
            return False, "未连接到数据库"

        try:
            # 转换为ObjectId
            api_key_id = ObjectId(api_key_id)

            # 获取要删除的密钥信息
            key_info = self.db.api_keys.find_one({"_id": api_key_id})

            # 删除密钥
            result = self.db.api_keys.delete_one({"_id": api_key_id})

            if result.deleted_count > 0:
                # 如果删除的是默认密钥，设置一个新的默认密钥
                if key_info and key_info.get("is_default", False):
                    # 找到同一AI名称的第一个密钥并设为默认
                    another_key = self.db.api_keys.find_one(
                        {"ai_name": key_info["ai_name"]}
                    )
                    if another_key:
                        self.db.api_keys.update_one(
                            {"_id": another_key["_id"]}, {"$set": {"is_default": True}}
                        )

                return True, "API密钥已删除"
            else:
                return False, "未找到要删除的API密钥"
        except Exception as e:
            return False, f"删除API密钥失败: {str(e)}"
