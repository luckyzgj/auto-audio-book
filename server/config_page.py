# 确保文件顶部有正确的导入
import os
import streamlit as st
from config_manager import ConfigManager


def show_config_page():
    """显示配置页面"""
    st.title("全局配置")

    config_manager = ConfigManager()

    # 创建三个标签页
    tab1, tab2, tab3 = st.tabs(["硅基流动API设置", "Gemini API设置", "角色语音模型"])

    # 硅基流动API设置
    with tab1:
        st.subheader("硅基流动API配置")

        # API URL设置
        silica_url = st.text_input(
            "硅基流动API URL",
            value=config_manager.get_silica_api_url(),
            key="silica_url",
        )

        if st.button("保存URL", key="save_silica_url"):
            if config_manager.set_silica_api_url(silica_url):
                st.success("硅基流动API URL已保存")
            else:
                st.error("保存硅基流动API URL失败")

        st.divider()

        # 显示现有API Keys
        st.subheader("硅基流动API Keys")
        if not config_manager.get_silica_api_keys():
            st.info("未添加硅基流动API Keys")
        else:
            for i, key in enumerate(config_manager.get_silica_api_keys()):
                col1, col2, col3, col4 = st.columns([4, 1, 1, 1])

                with col1:
                    # 显示密钥的前8位和后4位，中间用星号替代
                    if len(key) > 12:
                        masked_key = key[:8] + "*" * (len(key) - 12) + key[-4:]
                    else:
                        masked_key = key
                    st.code(masked_key)

                with col2:
                    if st.button("测试", key=f"test_silica_{i}"):
                        with st.spinner("正在测试API Key..."):
                            success, message = config_manager.test_silica_api_key(key)

                        if success:
                            st.success(message)
                        else:
                            st.error(message)

                with col3:
                    if st.button("查询余额", key=f"balance_silica_{i}"):
                        with st.spinner("正在查询余额..."):
                            success, data = config_manager.get_silica_api_balance(key)

                        if success:
                            # 创建一个信息卡片展示余额详情
                            with st.expander("账户详情", expanded=True):
                                st.write(f"**用户名:** {data['username']}")
                                st.write(f"**余额:** {data['balance']}")
                                st.write(f"**充值余额:** {data['charge_balance']}")
                                st.write(f"**总余额:** {data['total_balance']}")
                        else:
                            st.error(data)  # 这里data是错误消息

                with col4:
                    if st.button("删除", key=f"delete_silica_{i}"):
                        if config_manager.delete_silica_api_key(key):
                            st.success("删除成功")
                            st.rerun()
                        else:
                            st.error("删除失败")

        # 添加新的API Keys
        st.subheader("添加硅基流动API Keys")

        new_silica_keys = st.text_area(
            "输入API Keys（每行一个）",
            key="new_silica_keys",
            help="每行输入一个API Key，可以一次添加多个",
        )

        if st.button("添加Keys", key="add_silica_keys"):
            if config_manager.add_multiple_api_keys(new_silica_keys, "silica"):
                st.success("API Keys添加成功")
                st.rerun()
            else:
                st.error("API Keys添加失败或没有新的有效Keys")

    # Gemini API设置
    with tab2:
        st.subheader("Gemini API配置")

        # API URL设置
        gemini_url = st.text_input(
            "Gemini API URL",
            value=config_manager.get_gemini_api_url(),
            key="gemini_url",
        )

        if st.button("保存URL", key="save_gemini_url"):
            if config_manager.set_gemini_api_url(gemini_url):
                st.success("Gemini API URL已保存")
            else:
                st.error("保存Gemini API URL失败")

        st.divider()

        # 显示现有API Keys
        st.subheader("Gemini API Keys")
        if not config_manager.get_gemini_api_keys():
            st.info("未添加Gemini API Keys")
        else:
            for i, key in enumerate(config_manager.get_gemini_api_keys()):
                col1, col2, col3 = st.columns([4, 1, 1])

                with col1:
                    # 显示密钥的前8位和后4位，中间用星号替代
                    if len(key) > 12:
                        masked_key = key[:8] + "*" * (len(key) - 12) + key[-4:]
                    else:
                        masked_key = key
                    st.code(masked_key)

                with col2:
                    if st.button("测试", key=f"test_gemini_{i}"):
                        with st.spinner("正在测试API Key..."):
                            success, message = config_manager.test_gemini_api_key(key)

                        if success:
                            st.success(message)
                        else:
                            st.error(message)

                with col3:
                    if st.button("删除", key=f"delete_gemini_{i}"):
                        if config_manager.delete_gemini_api_key(key):
                            st.success("删除成功")
                            st.rerun()
                        else:
                            st.error("删除失败")

        # 添加新的API Keys
        st.subheader("添加Gemini API Keys")

        new_gemini_keys = st.text_area(
            "输入API Keys（每行一个）",
            key="new_gemini_keys",
            help="每行输入一个API Key，可以一次添加多个",
        )

        if st.button("添加Keys", key="add_gemini_keys"):
            if config_manager.add_multiple_api_keys(new_gemini_keys, "gemini"):
                st.success("API Keys添加成功")
                st.rerun()
            else:
                st.error("API Keys添加失败或没有新的有效Keys")

    # 角色语音模型设置
    with tab3:
        # 硅基流动语音模型
        st.subheader("硅基流动CosyVoice2语音模型")

        # 检查是否有API密钥配置
        silica_keys = config_manager.get_silica_api_keys()
        if not silica_keys:
            st.warning(
                "您尚未配置硅基流动API密钥，请先在'硅基流动API设置'标签页中添加API密钥"
            )
        else:
            # 手动定义硅基流动语音模型
            silica_voices = [
                {"id": "FunAudioLLM/CosyVoice2-0.5B:alex", "name": "Alex"},
                {"id": "FunAudioLLM/CosyVoice2-0.5B:anna", "name": "Anna"},
                {"id": "FunAudioLLM/CosyVoice2-0.5B:bella", "name": "Bella"},
                {"id": "FunAudioLLM/CosyVoice2-0.5B:benjamin", "name": "Benjamin"},
                {"id": "FunAudioLLM/CosyVoice2-0.5B:charles", "name": "Charles"},
                {"id": "FunAudioLLM/CosyVoice2-0.5B:claire", "name": "Claire"},
                {"id": "FunAudioLLM/CosyVoice2-0.5B:david", "name": "David"},
                {"id": "FunAudioLLM/CosyVoice2-0.5B:diana", "name": "Diana"},
            ]

            # 使用表格样式布局显示语音模型
            for voice in silica_voices:
                col1, col2 = st.columns([3, 1])  # 3:1的比例分配空间
                
                with col1:
                    st.write(f"**{voice['name']}**")
                
                with col2:
                    # 获取样本路径
                    sample_dir = os.path.join("data", "samples")
                    os.makedirs(sample_dir, exist_ok=True)
                    voice_name = voice["id"].split(":")[-1]
                    sample_path = os.path.join(sample_dir, f"silica_{voice_name}.mp3")

                    if os.path.exists(sample_path) and os.path.getsize(sample_path) > 0:
                        # 如果有样本，显示播放按钮
                        if st.button("播放", key=f"play_silica_{voice['id']}", use_container_width=True):
                            st.audio(sample_path)
                    else:
                        # 如果没有样本，显示获取按钮
                        if st.button("获取示例", key=f"get_silica_{voice['id']}", use_container_width=True):
                            with st.spinner(f"正在生成'{voice['name']}'的语音示例..."):
                                try:
                                    success, result = config_manager.generate_silica_voice_sample(
                                        voice["id"],
                                        f"你好，我是{voice['name']}的语音模型",
                                    )

                                    if success and os.path.exists(result):
                                        st.success("示例生成成功！")
                                        st.audio(result)
                                        st.rerun()
                                    else:
                                        st.error(f"生成示例失败: {result}")
                                except Exception as e:
                                    st.error(f"处理过程出错: {str(e)}")

        st.divider()

        # Edge TTS语音模型
        st.subheader("Microsoft Edge TTS语音模型")

        # 手动定义Edge TTS语音模型
        edge_voices = [
            {"id": "zh-CN-XiaoxiaoNeural", "name": "普通话-小晓"},
            {"id": "zh-CN-XiaoyiNeural", "name": "普通话-小艺"},
            {"id": "zh-CN-YunjianNeural", "name": "普通话-云健"},
            {"id": "zh-CN-YunxiNeural", "name": "普通话-云希"},
            {"id": "zh-CN-YunxiaNeural", "name": "普通话-云霞"},
            {"id": "zh-CN-YunyangNeural", "name": "普通话-云扬"},
            {"id": "zh-CN-liaoning-XiaobeiNeural", "name": "辽宁话-小北"},
            {"id": "zh-HK-HiuGaaiNeural", "name": "粤语-欢歌"},
            {"id": "zh-HK-HiuMaanNeural", "name": "粤语-华文"},
            {"id": "zh-HK-WanLungNeural", "name": "粤语-文勇"},
            {"id": "zh-TW-HsiaoChenNeural", "name": "台湾话-晓晨"},
            {"id": "zh-TW-HsiaoYuNeural", "name": "台湾话-晓语"},
            {"id": "zh-TW-YunJheNeural", "name": "台湾话-韵杰"},
        ]

        # 使用表格样式布局显示语音模型
        for voice in edge_voices:
            col1, col2 = st.columns([3, 1])  # 3:1的比例分配空间
            
            with col1:
                st.write(f"**{voice['name']}**")
            
            with col2:
                # 获取样本路径
                sample_dir = os.path.join("data", "samples")
                os.makedirs(sample_dir, exist_ok=True)
                voice_name = voice["id"].split("-")[-1].replace("Neural", "")
                sample_path = os.path.join(sample_dir, f"edge_{voice_name}.mp3")

                if os.path.exists(sample_path) and os.path.getsize(sample_path) > 0:
                    # 如果有样本，显示播放按钮
                    if st.button("播放", key=f"play_edge_{voice['id']}", use_container_width=True):
                        st.audio(sample_path)
                else:
                    # 如果没有样本，显示获取按钮
                    if st.button("获取示例", key=f"get_edge_{voice['id']}", use_container_width=True):
                        with st.spinner(f"正在生成'{voice['name']}'的语音示例..."):
                            try:
                                success, result = config_manager.generate_edge_tts_sample(
                                    voice["id"],
                                    f"你好，我是{voice['name']}的语音模型",
                                )

                                if success and os.path.exists(result):
                                    st.success("示例生成成功！")
                                    st.audio(result)
                                    st.rerun()
                                else:
                                    st.error(f"生成示例失败: {result}")
                            except Exception as e:
                                st.error(f"处理过程出错: {str(e)}")
