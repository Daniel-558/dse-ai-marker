import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import re

# 1. 页面配置 (必须在最前面)
st.set_page_config(page_title="DSE AI 超级导师", layout="wide")

# 2. 注入自定义 CSS 样式 (打造专业补习社风格)
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    h1 { color: #1e3a8a !important; font-weight: 800; border-bottom: 3px solid #fbbf24; padding-bottom: 10px; }
    .stButton>button { 
        background-color: #1e3a8a; color: white; border-radius: 8px; 
        font-weight: bold; width: 100%; transition: 0.3s;
    }
    .stButton>button:hover { background-color: #fbbf24; color: #1e3a8a; }
    .stChatMessage { border-radius: 15px; }
    /* 侧边栏样式 */
    [data-testid="stSidebar"] { background-color: #f1f5f9; }
    </style>
    """, unsafe_allow_html=True)

# 3. 初始化 API 客户端
api_key_val = st.secrets.get("GEMINI_API_KEY", "")
@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None

client = get_client(api_key_val)

# 4. 初始化状态变量
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "scores" not in st.session_state:
    st.session_state.scores = {"Content": 0, "Organization": 0, "Language": 0}
if "last_report" not in st.session_state:
    st.session_state.last_report = ""

# 5. 侧边栏：入场口令与工具箱
with st.sidebar:
    st.title("🔐 成员准入")
    access_code = st.text_input("请输入邀请码解锁", type="password")
    
    # 这里的口令你可以随时改
    if access_code != "DSE2026":
        st.warning("请输入正确邀请码以使用导师功能。")
        st.info("💡 提示：邀请码可在我们的官方 Threads 获取。")
        st.stop()
    
    st.success("验证成功！")
    st.markdown("---")
    st.title("📚 DSE 工具箱")
    with st.expander("高分连词库"):
        st.write("- Addition: Furthermore, Notably\n- Contrast: Paradoxically\n- Cause: Stemming from")
    with st.expander("5** 词汇替换"):
        st.table({"Common": ["Think", "Help", "Big"], "Elite": ["Advocate", "Facilitate", "Substantial"]})

# 6. 主界面布局
st.title("🤖 DSE AI 超级导师 Pro")
st.caption("全港首个基于考官逻辑的 AI 互动批改平台")

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown("### 📥 第一步：提交作文")
    task_type = st.selectbox("选择题型", ["Part A", "Part B", "Argumentative", "Letter to Editor"])
    target_lv = st.select_slider("目标等级", options=["3", "4", "5", "5*", "5**"])
    user_text = st.text_area("在此粘贴你的作文...", height=250)
    
    if st.button("🚀 生成深度批改报告"):
        if user_text:
            with st.spinner("阅卷官正在打分并分析..."):
                prompt = f"""
                你是一位精通DSE评分标准的考官。请对这篇{task_type}作文给Level {target_lv}目标的同学写报告。
                必须包含：评分、具体改进建议、Level 5** 示范改写和重点词汇。
                最后一行必须严格输出格式如下：SCORES: C:数字, O:数字, L:数字 (满分7)
                请使用繁体中文。
                """
                response = client.models.generate_content(model="gemini-3-flash-preview", contents=[prompt, user_text])
                full_text = response.text
                
                # 提取分数绘制雷达图
                score_match = re.search(r"SCORES: C:(\d), O:(\d), L:(\d)", full_text)
                if score_match:
                    st.session_state.scores = {
                        "Content": int(score_match.group(1)),
                        "Organization": int(score_match.group(2)),
                        "Language": int(score_match.group(3))
                    }
                st.session_state.last_report = full_text.split("SCORES:")[0]
                st.session_state.chat_history = [("AI", "报告已生成！查看左侧雷达图，不明白的地方在右侧问我。")]
        else:
            st.warning("请先输入作文内容。")

    # 雷达图显示
    if st.session_state.last_report:
        categories = list(st.session_state.scores.keys())
        values = list(st.session_state.scores.values())
        fig = go.Figure(data=go.Scatterpolar(r=values + [values[0]], theta=categories + [categories[0]], fill='toself', line_color='#fbbf24'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), showlegend=False, height=300, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(st.session_state.last_report)

    # 金句实验室
    st.markdown("---")
    st.markdown("### ✨ 金句实验室")
    s_input = st.text_input("输入普通句子进行 5** 升级：")
    if st.button("瞬间升级") and s_input:
        with st.spinner("升级中..."):
            res = client.models.generate_content(model="gemini-3-flash-preview", contents=f"将此句子升级为DSE Level 5**水平并解释加分点：{s_input}")
            st.info(res.text)

with col2:
    st.markdown("### 💬 第二步：1-on-1 导师追问")
    if not st.session_state.last_report:
        st.info("完成左侧批改后，导师将在此为你解答疑问。")
    else:
        for role, text in st.session_state.chat_history:
            with st.chat_message(role):
                st.write(text)
        
        if prompt_input := st.chat_input("问问导师：为什么这里要这样改？"):
            st.session_state.chat_history.append(("User", prompt_input))
            with st.chat_message("User"):
                st.write(prompt_input)
            with st.chat_message("AI"):
                context = f"学生原文: {user_text}\n报告内容: {st.session_state.last_report}\n学生提问: {prompt_input}"
                response = client.models.generate_content(model="gemini-3-flash-preview", contents=context)
                st.write(response.text)
                st.session_state.chat_history.append(("AI", response.text))
