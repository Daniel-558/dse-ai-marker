import streamlit as st
from google.genai import Client

# 1. 配置
st.set_page_config(page_title="DSE 超级导师 AI", layout="wide")
api_key_val = st.secrets.get("GEMINI_API_KEY", "")

@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None

client = get_client(api_key_val)

# 初始化对话历史
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_report" not in st.session_state:
    st.session_state.last_report = ""

st.title("🤖 DSE AI 超级导师")
st.caption("24小时在线：批改、讲解、追问，一站式搞定")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### ✍️ 第一步：提交作文")
    task_type = st.selectbox("选择题型", ["Part A", "Part B", "Argumentative", "Letter to Editor"])
    target_lv = st.select_slider("目标等级", options=["3", "4", "5", "5*", "5**"])
    user_text = st.text_area("粘贴你的作文内容...", height=250)
    
    if st.button("🚀 深度批改报告", use_container_width=True):
        if user_text:
            with st.spinner("阅卷官正在深度分析..."):
                prompt = f"你是一位精通DSE评分标准的考官，请针对这篇{task_type}作文给Level {target_lv}目标的同学写一份详细批改报告。必须包含评分、语法改进建议、5**范文改写和Killer词汇。请用繁体中文。"
                response = client.models.generate_content(model="gemini-3-flash-preview", contents=[prompt, user_text])
                st.session_state.last_report = response.text
                # 存入对话背景
                st.session_state.chat_history = [("AI", "这是你的批改报告。如果有任何不明白的地方，比如某个语法点或词汇用法，可以直接在下方问我！")]
        else:
            st.warning("请输入内容")

    if st.session_state.last_report:
        st.markdown("---")
        st.markdown("### 💡 批改详情")
        st.markdown(st.session_state.last_report)

with col2:
    st.markdown("### 💬 第二 step：与导师互动")
    if not st.session_state.last_report:
        st.info("完成左侧批改后，即可开启 1-on-1 追问模式。")
    else:
        # 显示对话历史
        for role, text in st.session_state.chat_history:
            with st.chat_message(role):
                st.write(text)
        
        # 追问输入框
        if prompt_input := st.chat_input("问问导师：为什么这里要这样改？"):
            st.session_state.chat_history.append(("User", prompt_input))
            with st.chat_message("User"):
                st.write(prompt_input)
            
            with st.chat_message("AI"):
                # 将作文内容、批改报告和对话历史作为上下文发给 AI
                context = f"学生作文: {user_text}\n\n你的批改报告: {st.session_state.last_report}\n\n学生现在问: {prompt_input}"
                response = client.models.generate_content(model="gemini-3-flash-preview", contents=context)
                st.write(response.text)
                st.session_state.chat_history.append(("AI", response.text))
