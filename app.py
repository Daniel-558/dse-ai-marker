import streamlit as st
import os
from google.genai import Client

# 1. 页面配置 (必须是第一行代码)
st.set_page_config(page_title="DSE AI 精批助手", layout="wide")

# 2. 从 Secrets 读取 API Key
api_key_val = st.secrets.get("GEMINI_API_KEY", "")

# 3. 初始化客户端 (放在缓存中防止重复加载)
@st.cache_resource
def get_client(key):
    if not key:
        return None
    return Client(api_key=key)

client = get_client(api_key_val)

# --- 界面开始 ---
st.title("📝 DSE English Writing AI Marker")
st.caption("项目蓝图阶段：DSE 英文作文 AI 精批 MVP")

# 检查 Key 是否配置
if not api_key_val:
    st.error("⚠️ 未检测到 API Key，请在 Streamlit Cloud 的 Secrets 中配置 GEMINI_API_KEY")
    st.stop()

# 布局：左侧输入，右侧输出
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 📥 上传作文片段")
    task_type = st.selectbox("选择题型", ["Part A (Short)", "Part B (Elective)", "Argumentative", "Letter to Editor"])
    target_lv = st.select_slider("目标等级", options=["3", "4", "5", "5*", "5**"])
    user_text = st.text_area("在此粘贴你的作文...", height=300, placeholder="Example: In my opinion, the government should...")
    
    submit_button = st.button("🚀 开始智能批改", use_container_width=True)

with col2:
    st.markdown("### 📋 批改报告")
    if submit_button and user_text:
        with st.spinner("DSE 阅卷员正在评阅中..."):
            try:
                prompt = f"""
                你是一位资深 DSE 英语科阅卷员。请针对以下 {task_type} 作文进行精批。
                学生目标等级：Level {target_lv}。
                待批改
