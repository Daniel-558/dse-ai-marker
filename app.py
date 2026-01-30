import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import re

# 1. 页面配置
st.set_page_config(page_title="DSE AI 超级导师 Pro", layout="wide")

# 2. 自定义 CSS
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    h1 { color: #1e3a8a !important; font-weight: 800; border-bottom: 3px solid #fbbf24; padding-bottom: 10px; }
    .stButton>button { background-color: #1e3a8a; color: white; border-radius: 8px; font-weight: bold; width: 100%; }
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    /* 限制雷达图容器高度 */
    .radar-container { max-height: 350px; }
    </style>
    """, unsafe_allow_html=True)

# 3. 初始化 API 客户端
api_key_val = st.secrets.get("GEMINI_API_KEY", "")
@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None

client = get_client(api_key_val)

# 4. 初始化状态变量 (持久化对话的关键)
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # 格式: {"role": "...", "content": "..."}
if "scores" not in st.session_state:
    st.session_state.scores = {"Content": 0, "Organization": 0, "Language": 0}
if "last_report" not in st.session_state:
    st.session_state.last_report = ""

# 5. 侧边栏
with st.sidebar:
    st.title("🔐 成员准入")
    access_code = st.text_input("请输入邀请码解锁", type="password")
    if access_code != "DSE2026":
        st.warning("请输入正确邀请码以使用导师功能。")
        st.stop()
    
    st.success("验证成功！")
    st.divider()
    st.title("📚 DSE 工具箱")
    with st.expander("高分连词库"):
        st.write("- Addition: Furthermore, Notably\n- Contrast: Paradoxically\n- Cause: Stemming from")

# 6. 主界面
st.title("🤖 DSE AI 超级导师 Pro")
st.caption("基于 Google Gemini 3.0 Flash 引擎的考官级互动平台")

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown("### 📥 第一步：提交作文")
    task_type = st.selectbox("选择题型", ["Part A", "Part B", "Argumentative", "Letter to Editor"])
    target_lv = st.select_slider("目标等级", options=["3", "4", "5", "5*", "5**"])
    user_text = st.text_area("在此粘贴你的作文...", height=300)
    
    if st.button("🚀 生成深度批改报告"):
        if user_text:
            with st.spinner("正在以考官逻辑阅卷..."):
                prompt = f"""
                你是一位精通DSE评分标准的考官。请对这篇{task_type}作文给Level {target_lv}目标的同学写一份繁体中文报告。
                要求：
                1. 指出 Content, Organization, Language 的优缺点。
                2. 提供 Level 5** 级别的示范改写。
                3. 最后一行必须严格输出：SCORES: C:数字, O:数字, L:数字 (满分7)
                """
                response = client.models.generate_content(model="gemini-3-flash-preview", contents=[prompt, user_text])
                full_text = response.text
                
                # 分数解析
                score_match = re.search(r"SCORES: C:(\d), O:(\d), L:(\d)", full_text)
                if score_match:
                    st.session_state.scores = {
                        "Content": int(score_match.group(1)),
                        "Organization": int(score_match.group(2)),
                        "Language": int(score_match.group(3))
                    }
                
                st.session_state.last_report = full_text.split("SCORES:")[0]
                # 初始化对话，并注入“考官记忆”
                st.session_state.chat_history = [
                    {"role": "ai", "content": "報告已生成！我已根據 DSE 標準完成批改。你可以針對報告內容向我提問。"}
                ]
        else:
            st.warning("請先輸入作文內容。")

    # 雷达图与报告显示
    if st.session_state.last_report:
        categories = list(st.session_state.scores.keys())
        values = list(st.session_state.scores.values())
        fig = go.Figure(data=go.Scatterpolar(r=values + [values[0]], theta=categories + [categories[0]], fill='toself', line_color='#fbbf24'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")
        st.markdown(st.session_state.last_report)

with col2:
    st.markdown("### 💬 第二步：1-on-1 导师追问")
    
    # 容器化对话框，防止滚动
    chat_container = st.container(height=600)
    
    with chat_container:
        if not st.session_state.last_report:
            st.info("完成左侧批改后，导师将在此为你解答疑问。")
        else:
            # 渲染历史对话
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
    
    # 对话输入框
    if prompt_input := st.chat_input("问问导师：为什么这里要这样改？"):
        # 显示用户输入
        st.session_state.chat_history.append({"role": "user", "content": prompt_input})
        with chat_container:
            with st.chat_message("user"):
                st.write(prompt_input)
            
            with st.chat_message("ai"):
                with st.spinner("思考中..."):
                    # 构建包含上下文的请求
                    context_msg = f"""
                    你是一位DSE導師。
                    學生原文：{user_text}
                    你的批改報告：{st.session_state.last_report}
                    學生提問：{prompt_input}
                    請針對提問給予專業、鼓勵性的指導。使用繁體中文。
                    """
                    response = client.models.generate_content(model="gemini-3-flash-preview", contents=context_msg)
                    st.write(response.text)
                    st.session_state.chat_history.append({"role": "ai", "content": response.text})
