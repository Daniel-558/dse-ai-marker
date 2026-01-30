import streamlit as st
import os
from google.genai import Client

# 1. 页面配置
st.set_page_config(page_title="DSE AI 精批助手", layout="wide")

# 2. 从 Secrets 读取 API Key
api_key_val = st.secrets.get("GEMINI_API_KEY", "")

# 3. 初始化客户端
@st.cache_resource
def get_client(key):
    if not key:
        return None
    try:
        return Client(api_key=key)
    except:
        return None

client = get_client(api_key_val)

# --- 界面开始 ---
st.title("📝 DSE English Writing AI Marker")
st.caption("项目蓝图阶段：DSE 英文作文 AI 精批 MVP")

if not api_key_val:
    st.error("⚠️ 未检测到 API Key，请在 Streamlit Cloud 后台配置 Secrets")
    st.stop()

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 📥 上传作文片段")
    task_type = st.selectbox("选择题型", ["Part A", "Part B", "Argumentative", "Letter to Editor"])
    target_lv = st.select_slider("目标等级", options=["3", "4", "5", "5*", "5**"])
    user_text = st.text_area("在此粘贴你的作文...", height=300)
    
    submit_button = st.button("🚀 开始智能批改", use_container_width=True)

with col2:
    st.markdown("### 📋 批改报告")
    if submit_button and user_text:
        with st.spinner("DSE 阅卷员正在评阅中..."):
            # 这里的 prompt 必须严格对齐
            prompt = f"""
            你是一位资深 DSE 英语科阅卷员。请针对以下 {task_type} 作文进行精批。
            学生目标等级：Level {target_lv}。
            待批改文本: "{user_text}"
            请按以下格式输出报告：
            # 📊 DSE 预估评分报告
            ## 1. 总体等级预估: [Level X]
            ## 2. 三大维度分析: (Content, Language, Organization)
            ## 3. Level 5** 示范改写
            ## 4. 重点词汇升级 (Killer Vocab)
            请使用繁体中文回答。
            """
            
            try:
                response = client.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents=prompt
                )
                st.markdown(response.text)
                st.success("批改完成！")
            except Exception as e:
                st.error(f"AI 调用失败，请检查网络或 API Key。错误详情: {e}")
    elif submit_button and not user_text:
        st.warning("请先输入作文内容。")
    else:
        st.info("👈 请在左侧输入内容并点击按钮开始。")
