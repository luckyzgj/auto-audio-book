import os
import json
import streamlit as st
import requests
from openai import OpenAI


class ConfigManager:
    def __init__(self):
        self.config_file = os.path.join("data", "config.json")
        self.config = self.load_config()

    def load_config(self):
        """加载配置文件"""
        os.makedirs("data", exist_ok=True)

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                st.error(f"加载配置文件出错: {str(e)}")
                return self.get_default_config()
        else:
            return self.get_default_config()

    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            st.error(f"保存配置文件出错: {str(e)}")
            return False

    def get_default_config(self):
        """获取默认配置"""
        return {
            "silica_api": {"url": "https://api.siliconflow.cn/v1", "keys": []},
            "gemini_api": {
                "url": "https://generativelanguage.googleapis.com/v1beta",
                "keys": [],
            },
            "voice_models": {
                "silica_voice": [
                    {
                        "id": "FunAudioLLM/CosyVoice2-0.5B:alex",
                        "name": "Alex",
                        "sample_path": "",
                    },
                    {
                        "id": "FunAudioLLM/CosyVoice2-0.5B:anna",
                        "name": "Anna",
                        "sample_path": "",
                    },
                    {
                        "id": "FunAudioLLM/CosyVoice2-0.5B:bella",
                        "name": "Bella",
                        "sample_path": "",
                    },
                    {
                        "id": "FunAudioLLM/CosyVoice2-0.5B:benjamin",
                        "name": "Benjamin",
                        "sample_path": "",
                    },
                    {
                        "id": "FunAudioLLM/CosyVoice2-0.5B:charles",
                        "name": "Charles",
                        "sample_path": "",
                    },
                    {
                        "id": "FunAudioLLM/CosyVoice2-0.5B:claire",
                        "name": "Claire",
                        "sample_path": "",
                    },
                    {
                        "id": "FunAudioLLM/CosyVoice2-0.5B:david",
                        "name": "David",
                        "sample_path": "",
                    },
                    {
                        "id": "FunAudioLLM/CosyVoice2-0.5B:diana",
                        "name": "Diana",
                        "sample_path": "",
                    },
                ],
                "edge_tts": [
                    {
                        "id": "zh-CN-XiaoxiaoNeural",
                        "name": "普通话-小晓",
                        "sample_path": "",
                    },
                    {
                        "id": "zh-CN-XiaoyiNeural",
                        "name": "普通话-小艺",
                        "sample_path": "",
                    },
                    {
                        "id": "zh-CN-YunjianNeural",
                        "name": "普通话-云健",
                        "sample_path": "",
                    },
                    {
                        "id": "zh-CN-YunxiNeural",
                        "name": "普通话-云希",
                        "sample_path": "",
                    },
                    {
                        "id": "zh-CN-YunxiaNeural",
                        "name": "普通话-云霞",
                        "sample_path": "",
                    },
                    {
                        "id": "zh-CN-YunyangNeural",
                        "name": "普通话-云扬",
                        "sample_path": "",
                    },
                    {
                        "id": "zh-CN-liaoning-XiaobeiNeural",
                        "name": "辽宁话-小北",
                        "sample_path": "",
                    },
                    {
                        "id": "zh-HK-HiuGaaiNeural",
                        "name": "粤语-欢歌",
                        "sample_path": "",
                    },
                    {
                        "id": "zh-HK-HiuMaanNeural",
                        "name": "粤语-华文",
                        "sample_path": "",
                    },
                    {
                        "id": "zh-HK-WanLungNeural",
                        "name": "粤语-文勇",
                        "sample_path": "",
                    },
                    {
                        "id": "zh-TW-HsiaoChenNeural",
                        "name": "台湾话-晓晨",
                        "sample_path": "",
                    },
                    {
                        "id": "zh-TW-HsiaoYuNeural",
                        "name": "台湾话-晓语",
                        "sample_path": "",
                    },
                    {
                        "id": "zh-TW-YunJheNeural",
                        "name": "台湾话-韵杰",
                        "sample_path": "",
                    },
                ],
            },
        }

    def get_silica_api_url(self):
        """获取硅基流动API URL"""
        return self.config["silica_api"]["url"]

    def set_silica_api_url(self, url):
        """设置硅基流动API URL"""
        self.config["silica_api"]["url"] = url
        return self.save_config()

    def get_silica_api_keys(self):
        """获取硅基流动API Keys"""
        return self.config["silica_api"]["keys"]

    def add_silica_api_key(self, key):
        """添加硅基流动API Key"""
        if key and key not in self.config["silica_api"]["keys"]:
            self.config["silica_api"]["keys"].append(key)
            return self.save_config()
        return False

    def delete_silica_api_key(self, key):
        """删除硅基流动API Key"""
        if key in self.config["silica_api"]["keys"]:
            self.config["silica_api"]["keys"].remove(key)
            return self.save_config()
        return False

    def get_gemini_api_url(self):
        """获取Gemini API URL"""
        return self.config["gemini_api"]["url"]

    def set_gemini_api_url(self, url):
        """设置Gemini API URL"""
        self.config["gemini_api"]["url"] = url
        return self.save_config()

    def get_gemini_api_keys(self):
        """获取Gemini API Keys"""
        return self.config["gemini_api"]["keys"]

    def add_gemini_api_key(self, key):
        """添加Gemini API Key"""
        if key and key not in self.config["gemini_api"]["keys"]:
            self.config["gemini_api"]["keys"].append(key)
            return self.save_config()
        return False

    def delete_gemini_api_key(self, key):
        """删除Gemini API Key"""
        if key in self.config["gemini_api"]["keys"]:
            self.config["gemini_api"]["keys"].remove(key)
            return self.save_config()
        return False

    def add_multiple_api_keys(self, keys_text, api_type):
        """添加多个API Key"""
        if not keys_text:
            return False

        keys = [k.strip() for k in keys_text.split("\n")]
        keys = [k for k in keys if k]  # 过滤空行

        success = False
        for key in keys:
            if api_type == "silica":
                if key not in self.config["silica_api"]["keys"]:
                    self.config["silica_api"]["keys"].append(key)
                    success = True
            elif api_type == "gemini":
                if key not in self.config["gemini_api"]["keys"]:
                    self.config["gemini_api"]["keys"].append(key)
                    success = True

        if success:
            return self.save_config()
        return False

    def test_silica_api_key(self, api_key):
        """测试硅基流动API Key是否可用"""
        try:
            client = OpenAI(api_key=api_key, base_url=self.get_silica_api_url())

            # 尝试获取模型列表
            response = client.models.list()

            if hasattr(response, "data") and len(response.data) > 0:
                return True, f"有效 (发现{len(response.data)}个模型)"
            else:
                return False, "无效 (无法获取模型列表)"

        except Exception as e:
            error_message = str(e)
            if "Permission denied" in error_message:
                return False, "无效 (权限被拒绝)"
            elif "Invalid API key" in error_message:
                return False, "无效 (API密钥不正确)"
            elif "Request timed out" in error_message:
                return False, "无效 (请求超时)"
            return False, f"无效 ({error_message[:50]}...)"

    def get_silica_api_balance(self, api_key):
        """获取硅基流动API账户余额"""
        try:
            # 获取用户信息API路径
            base_url = self.get_silica_api_url()
            # 确保我们使用正确的端点，可能需要调整URL
            if "/v1" in base_url:
                base_url = base_url.rsplit("/v1", 1)[0]
            url = f"{base_url}/v1/user/info"

            headers = {"Authorization": f"Bearer {api_key}"}

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") and "data" in data:
                    user_data = data["data"]
                    balance = user_data.get("balance", "0")
                    charge_balance = user_data.get("chargeBalance", "0")
                    total_balance = user_data.get("totalBalance", "0")
                    username = user_data.get("name", "Unknown")

                    return True, {
                        "balance": balance,
                        "charge_balance": charge_balance,
                        "total_balance": total_balance,
                        "username": username,
                    }
                else:
                    return False, f"无法获取余额信息: {data.get('message', '未知错误')}"
            else:
                return False, f"API请求失败 (状态码: {response.status_code})"

        except Exception as e:
            return False, f"查询余额出错: {str(e)[:50]}..."

    def test_gemini_api_key(self, api_key):
        """测试Gemini API Key是否可用"""
        try:
            # 构建Gemini API请求URL
            base_url = self.get_gemini_api_url()
            url = f"{base_url}/models?key={api_key}"

            # 发送请求
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if "models" in data and len(data["models"]) > 0:
                    return True, f"有效 (发现{len(data['models'])}个模型)"
                else:
                    return False, "无效 (无法获取模型列表)"
            else:
                return False, f"无效 (HTTP状态码: {response.status_code})"

        except Exception as e:
            return False, f"无效 ({str(e)[:50]}...)"

    def get_voice_models_config(self):
        """获取语音模型配置"""
        if "voice_models" not in self.config:
            self.config["voice_models"] = self.get_default_config()["voice_models"]
            self.save_config()
        return self.config["voice_models"]

    def get_silica_voice_models(self):
        """获取硅基流动语音模型列表"""
        voice_models = self.get_voice_models_config()
        return voice_models.get(
            "silica_voice", self.get_default_config()["voice_models"]["silica_voice"]
        )

    def get_edge_tts_models(self):
        """获取edge_tts语音模型列表"""
        voice_models = self.get_voice_models_config()
        return voice_models.get(
            "edge_tts", self.get_default_config()["voice_models"]["edge_tts"]
        )

    def update_voice_sample_path(self, engine, voice_id, sample_path):
        """更新语音样本路径"""
        if "voice_models" not in self.config:
            self.config["voice_models"] = self.get_default_config()["voice_models"]

        if engine == "silica_voice":
            for voice in self.config["voice_models"]["silica_voice"]:
                if voice["id"] == voice_id:
                    voice["sample_path"] = sample_path
                    return self.save_config()
        elif engine == "edge_tts":
            for voice in self.config["voice_models"]["edge_tts"]:
                if voice["id"] == voice_id:
                    voice["sample_path"] = sample_path
                    return self.save_config()

        return False

    def generate_silica_voice_sample(self, voice_id, text="你好，我是语音模型"):
        """生成硅基流动的语音样本"""
        import requests
        import os

        # 确保目录存在
        sample_dir = os.path.join("data", "samples")
        os.makedirs(sample_dir, exist_ok=True)

        # 构建保存路径
        voice_name = voice_id.split(":")[-1]
        sample_path = os.path.join(sample_dir, f"silica_{voice_name}.mp3")

        # 如果样本已存在，直接返回路径
        if os.path.exists(sample_path) and os.path.getsize(sample_path) > 0:
            return True, sample_path

        # 获取API密钥，如果没有则返回错误
        api_keys = self.get_silica_api_keys()
        if not api_keys:
            return False, "没有配置硅基流动API密钥"

        api_key = api_keys[0]  # 使用第一个密钥

        # 准备请求
        url = f"{self.get_silica_api_url()}/audio/speech"

        payload = {
            "model": "FunAudioLLM/CosyVoice2-0.5B",
            "input": f"{text}",
            "voice": voice_id,
            "response_format": "mp3",
            "speed": 1,
            "gain": 0,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                # 将响应内容保存为音频文件
                with open(sample_path, "wb") as f:
                    f.write(response.content)

                # 不再尝试更新配置文件
                return True, sample_path
            else:
                return (
                    False,
                    f"API请求失败: HTTP {response.status_code}, {response.text}",
                )

        except Exception as e:
            return False, f"生成语音样本出错: {str(e)}"

    def generate_edge_tts_sample(self, voice_id, text="你好，我是语音模型"):
        """生成edge_tts的语音样本"""
        import os
        import asyncio

        try:
            from edge_tts import Communicate
        except ImportError:
            return False, "未安装edge-tts库，请先安装: pip install edge-tts"

        # 确保目录存在
        sample_dir = os.path.join("data", "samples")
        os.makedirs(sample_dir, exist_ok=True)

        # 构建保存路径
        voice_name = voice_id.split("-")[-1].replace("Neural", "")
        sample_path = os.path.join(sample_dir, f"edge_{voice_name}.mp3")

        # 如果样本已存在，直接返回路径
        if os.path.exists(sample_path) and os.path.getsize(sample_path) > 0:
            return True, sample_path

        # 构建和运行异步函数
        async def generate_speech():
            communicate = Communicate(text, voice_id)
            await communicate.save(sample_path)

        try:
            asyncio.run(generate_speech())
            # 不再尝试更新配置文件
            return True, sample_path
        except Exception as e:
            return False, f"生成语音样本出错: {str(e)}"
