import streamlit as st
import os
from dotenv import load_dotenv
from google.genai import Client

# 1. 页面配置
st.set_page_config(page_title="DSE AI 精批助手", layout="wide")
load_dotenv()

# 2. 初始化 Gemini 客户端
if "API_KEY" not in st.session_state:
    st.session_state.API_KEY = os.getenv("GEMINI_API_KEY", "")

client = Client(api_key=st.session_state.API_KEY)

# --- 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 设置")
    st.session_state.API_KEY = st.text_input("Gemini API Key", value=st.session_state.API_KEY, type="password")
    st.info("这是你的 DSE 智能平台首个 MVP 模块：英文作文批改")

# --- 主界面 ---
st.title("📝 DSE English Writing AI Marker")
st.subheader("构建下一代 DSE 智能学习平台 - 第一阶段：尖刀功能")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 📥 学生上传区")
    task_type = st.selectbox("选择题型", ["Part A (Short)", "Part B (Elective)", "Argumentative", "Letter to Editor"])
    target_lv = st.select_slider("目标等级", options=["3", "4", "5", "5*", "5**"])
    user_text = st.text_area("在此粘贴你的作文或片段...", height=300, placeholder="Example: Nowadays, more and more people think that...")
    
    if st.button("🚀 开始智能批改", use_container_width=True):
        if not user_text:
            st.warning("请输入内容后再批改")
        elif not st.session_state.API_KEY:
            st.error("请在左侧填入 API Key")
        else:
            with st.spinner("阅卷员正在仔细阅读并对比 DSE 评分标准..."):
                try:
                    prompt = f"""
                    你是一位资深 DSE 英语科阅卷员。请针对以下 {task_type} 作文进行精批。
                    学生目标等级：Level {target_lv}。
                    
                    待批改文本: "{user_text}"
                    
                    请按以下格式输出报告：
                    # 📊 DSE 预估评分报告
                    ## 1. 总体等级预估: [Level X]
                    ## 2. 三大维度分析:
                    - **Content**: 优缺点分析
                    - **Language**: 语法及词汇分析
                    - **Organization**: 结构连贯性分析
                    ## 3. Level 5** 示范改写:
                    (在此提供一段高质量改写)
                    ## 4. 重点词汇升级 (Killer Vocab):
                    (提供3个可提分的词汇或短语)
                    """
                    response = client.models.generate_content(
                        model="gemini-3-flash-preview",
                        contents=prompt
                    )
                    st.session_state.result = response.text
                except Exception as e:
                    st.error(f"出错啦: {e}")

with col2:
    st.markdown("### 📋 批改报告")
    if "result" in st.session_state:
        st.markdown(st.session_state.result)
    else:
        st.info("批改结果将在此处显示。")

# --- 页脚 ---
st.divider()
st.caption("Powered by Google Gemini API | DSE 智能学习平台蓝图开发中")