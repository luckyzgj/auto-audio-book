"""
数据模型模块，定义应用程序中使用的各种数据结构和模型类
"""

from datetime import datetime


class Novel:
    """小说数据模型类"""

    def __init__(self, name="", author="", description="", source_url=""):
        self.id = None  # MongoDB中的_id
        self.name = name
        self.author = author
        self.description = description
        self.source_url = source_url
        self.volumes = []  # 卷/分组列表
        self.created_at = None
        self.updated_at = None

    def add_volume(self, text, list_url):
        """添加卷/分组"""
        # 检查是否已存在相同URL的卷
        for volume in self.volumes:
            if volume["list_url"] == list_url:
                return False

        self.volumes.append({"text": text, "list_url": list_url})
        return True

    def to_dict(self):
        """转换为字典，用于MongoDB存储"""
        data = {
            "name": self.name,
            "author": self.author,
            "description": self.description,
            "source_url": self.source_url,
            "volumes": self.volumes,
        }

        # 如果有ID，则包含ID
        if self.id:
            data["_id"] = self.id

        return data

    @classmethod
    def from_dict(cls, data):
        """从字典创建对象"""
        novel = cls(
            name=data.get("name", ""),
            author=data.get("author", ""),
            description=data.get("description", ""),
            source_url=data.get("source_url", ""),
        )

        if "_id" in data:
            novel.id = data["_id"]

        novel.volumes = data.get("volumes", [])
        novel.created_at = data.get("created_at")
        novel.updated_at = data.get("updated_at")

        return novel


class Chapter:
    """章节数据模型类"""

    def __init__(self, title="", url="", group=""):
        self.id = None  # MongoDB中的_id
        self.novel_id = None  # 所属小说ID
        self.title = title
        self.url = url
        self.group = group  # 卷/分组
        self.word_count = 0
        self.content = []  # 章节内容段落列表
        self.dialogues = []  # 对话分析结果
        self.created_at = None
        self.updated_at = None
        self.dialogue_updated_at = None

    def to_dict(self):
        """转换为字典，用于MongoDB存储"""
        data = {
            "novel_id": self.novel_id,
            "title": self.title,
            "url": self.url,
            "volume": self.group,
            "word_count": self.word_count,
            "content": self.content,
        }

        # 如果有对话分析，则包含
        if self.dialogues:
            data["dialogues"] = self.dialogues

        # 如果有ID，则包含ID
        if self.id:
            data["_id"] = self.id

        # 包含时间戳
        if self.created_at:
            data["created_at"] = self.created_at
        if self.updated_at:
            data["updated_at"] = self.updated_at
        if self.dialogue_updated_at:
            data["dialogue_updated_at"] = self.dialogue_updated_at

        return data

    @classmethod
    def from_dict(cls, data):
        """从字典创建对象"""
        chapter = cls(
            title=data.get("title", ""),
            url=data.get("url", ""),
            group=data.get("volume", ""),
        )

        if "_id" in data:
            chapter.id = data["_id"]

        chapter.novel_id = data.get("novel_id")
        chapter.word_count = data.get("word_count", 0)
        chapter.content = data.get("content", [])
        chapter.dialogues = data.get("dialogues", [])
        chapter.created_at = data.get("created_at")
        chapter.updated_at = data.get("updated_at")
        chapter.dialogue_updated_at = data.get("dialogue_updated_at")

        return chapter

    @classmethod
    def from_crawler_format(cls, crawler_chapter, novel_id=None):
        """从爬虫格式转换为章节对象"""
        chapter = cls(
            title=crawler_chapter.get("chapter_title", ""),
            url=crawler_chapter.get("chapter_url", ""),
            group=crawler_chapter.get("group", ""),
        )

        chapter.novel_id = novel_id
        chapter.word_count = crawler_chapter.get("word_count", 0)
        chapter.content = crawler_chapter.get("content", [])

        return chapter

    def to_crawler_format(self):
        """转换为爬虫格式"""
        return {
            "chapter_title": self.title,
            "chapter_url": self.url,
            "group": self.group,
            "word_count": self.word_count,
            "content": self.content,
        }


class APIKey:
    """API密钥数据模型类"""

    def __init__(self, api_key="", ai_name="GeminiAI", is_default=False):
        self.id = None  # MongoDB中的_id
        self.api_key = api_key
        self.ai_name = ai_name
        self.is_default = is_default
        self.created_at = None
        self.updated_at = None

    def to_dict(self):
        """转换为字典，用于MongoDB存储"""
        data = {
            "api_key": self.api_key,
            "ai_name": self.ai_name,
            "is_default": self.is_default,
        }

        # 如果有ID，则包含ID
        if self.id:
            data["_id"] = self.id

        # 包含时间戳
        now = datetime.now()
        if self.created_at:
            data["created_at"] = self.created_at
        else:
            data["created_at"] = now

        data["updated_at"] = now

        return data

    @classmethod
    def from_dict(cls, data):
        """从字典创建对象"""
        api_key = cls(
            api_key=data.get("api_key", ""),
            ai_name=data.get("ai_name", "GeminiAI"),
            is_default=data.get("is_default", False),
        )

        if "_id" in data:
            api_key.id = data["_id"]

        api_key.created_at = data.get("created_at")
        api_key.updated_at = data.get("updated_at")

        return api_key


class DialogueEntry:
    """对话条目模型"""

    def __init__(self, character_type="", character_sex="中", text=""):
        self.character_type = character_type  # 角色类型/名称
        self.character_sex = character_sex  # 角色性别
        self.text = text  # 对话内容

    def to_dict(self):
        """转换为字典"""
        return {
            "type": self.character_type,
            "sex": self.character_sex,
            "text": self.text,
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建对象"""
        return cls(
            character_type=data.get("type", ""),
            character_sex=data.get("sex", "中"),
            text=data.get("text", ""),
        )
