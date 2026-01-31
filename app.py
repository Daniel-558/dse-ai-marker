import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import re

# 1. 页面配置
st.set_page_config(page_title="DSE AI 超级导师 Pro", layout="wide")

# 2. 增强版 CSS 框架 (加入卡片设计)
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    h1 { color: #1e3a8a !important; font-weight: 800; text-align: center; margin-bottom: 20px; }
    
    /* 模拟卡片框架 */
    .report-card {
        background-color: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border-left: 5px solid #fbbf24;
        margin-bottom: 20px;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white; border-radius: 10px; font-weight: bold; border: none; padding: 10px;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(59,130,246,0.4); }
    </style>
    """, unsafe_allow_html=True)

# 3. 初始化 API
api_key_val = st.secrets.get("GEMINI_API_KEY", "")
@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None
client = get_client(api_key_val)

if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "scores" not in st.session_state: st.session_state.scores = {"Content": 0, "Organization": 0, "Language": 0}
if "last_report" not in st.session_state: st.session_state.last_report = ""

# 4. 侧边栏 (口令与工具)
with st.sidebar:
    st.title("🔐 成员准入")
    access_code = st.text_input("请输入邀请码", type="password")
    if access_code != "DSE2026":
        st.warning("口令错误")
        st.stop()
    st.success("准入成功")
    st.markdown("---")
    st.markdown("### 🛠️ 快速工具")
    st.caption("双击下方词汇即可复制")
    st.code("Inextricably linked\nPrevalent trend\nExacerbate the issue", language="text")

# 5. 主界面布局
st.title("🤖 DSE AI 超级导师 Pro")

col1, col2 = st.columns([1.2, 0.8], gap="large")

with col1:
    with st.container():
        st.markdown("### 📥 提交作文片段")
        t_type = st.selectbox("题型", ["Part A", "Part B", "Argumentative", "Report"])
        t_lv = st.select_slider("目标等级", options=["3", "4", "5", "5*", "5**"])
        u_text = st.text_area("粘贴内容...", height=200, placeholder="在此输入你的作文...")
        
        btn = st.button("🚀 生成可视化批改框架")

    if btn and u_text:
        with st.spinner("考官正在生成结构化报告..."):
            prompt = f"""
            你是一位DSE考官。请分析这篇{t_type}作文。
            输出要求：
            1. 分成[Overall Score] [Strengths] [Weaknesses] [5** Rewrite]四个板块。
            2. 最后一行必须是: SCORES: C:数字, O:数字, L:数字 (满分7)
            使用繁体中文。作文：{u_text}
            """
            res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
            
            score_match = re.search(r"SCORES: C:(\d), O:(\d), L:(\d)", res.text)
            if score_match:
                st.session_state.scores = {"Content": int(score_match.group(1)), "Organization": int(score_match.group(2)), "Language": int(score_match.group(3))}
            st.session_state.last_report = res.text.split("SCORES:")[0]

    # --- 核心升级：可视化框架图展示区 ---
    if st.session_state.last_report:
        st.markdown("---")
        st.markdown("### 📊 评估框架图")
        
        # 布局：左仪表盘，右雷达图
        g1, g2 = st.columns(2)
        
        # 总分仪表盘 (Gauge Chart)
        total_score = sum(st.session_state.scores.values())
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = total_score,
            title = {'text': "总分 (满分21)"},
            gauge = {'axis': {'range': [0, 21]}, 'bar': {'color': "#1e3a8a"}}
        ))
        fig_gauge.update_layout(height=250, margin=dict(t=30, b=0))
        g1.plotly_chart(fig_gauge, use_container_width=True)

        # 维度雷达图
        cat = list(st.session_state.scores.keys())
        val = list(st.session_state.scores.values())
        fig_radar = go.Figure(data=go.Scatterpolar(r=val+[val[0]], theta=cat+[cat[0]], fill='toself', line_color='#fbbf24'))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), showlegend=False, height=250, margin=dict(t=30, b=0))
        g2.plotly_chart(fig_radar, use_container_width=True)

        # 结构化回馈框架
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        st.markdown("### 📋 深度批改报告")
        st.markdown(st.session_state.last_report)
        st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown("### 💬 1-on-1 导师互动")
    # 对话逻辑保持不变，确保对答如流...
    chat_container = st.container(height=500)
    with chat_container:
        for r, t in st.session_state.chat_history:
            with st.chat_message(r): st.write(t)
            
    if p_input := st.chat_input("针对评分提问..."):
        st.session_state.chat_history.append(("User", p_input))
        with st.chat_message("User"): st.write(p_input)
        with st.chat_message("AI"):
            ans = client.models.generate_content(model="gemini-3-flash-preview", contents=f"作文:{u_text}\n报告:{st.session_state.last_report}\n问题:{p_input}")
            st.write(ans.text)
            st.session_state.chat_history.append(("AI", ans.text))
            st.rerun()
