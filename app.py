import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import re
import numpy as np
from datetime import datetime
from PIL import Image

# --- 1. 页面配置 ---
st.set_page_config(page_title="DSE AI 超级工作站", layout="wide")

# --- 2. 统一 UI 样式 ---
st.markdown("""
    <style>
    .stApp { background: #f8fafc; }
    .main-header { padding: 1.5rem; border-radius: 12px; color: white; text-align: center; margin-bottom: 20px; }
    .eng-bg { background: linear-gradient(135deg, #1e293b 0%, #334155 100%); }
    .math-bg { background: linear-gradient(135deg, #065f46 0%, #059669 100%); }
    .report-card { background: white; padding: 20px; border-radius: 15px; border-left: 6px solid #3b82f6; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-top: 15px; white-space: pre-wrap; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 8px 8px 0 0; padding: 10px 18px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 初始化所有科目的持久化状态 ---
if "chat_history" not in st.session_state: st.session_state.chat_history = []
# 英文科数据
if "eng_p2_data" not in st.session_state: 
    st.session_state.eng_p2_data = {"report": "", "scores": {"C": 0, "O": 0, "L": 0}}
# 数学科数据
if "math_data" not in st.session_state:
    st.session_state.math_data = {"solution": ""}

# API 初始化
api_key_val = st.secrets.get("GEMINI_API_KEY", "")
@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None
client = get_client(api_key_val)

# --- 4. 侧边栏：全局控制 ---
with st.sidebar:
    st.title("🛡️ DSE Portal")
    if st.text_input("解锁码", type="password") != "DSE2026":
        st.info("请输入邀请码解锁全科功能")
        st.stop()
    
    st.markdown("---")
    # 学科切换
    subject = st.selectbox("📚 选择备考科目", ["🇬🇧 English Language", "🔢 Mathematics (Comp)"])
    
    st.markdown("---")
    st.subheader("📂 资料上传")
    up_file = st.file_uploader("支持照片识别 (作文/数学题)", type=['png', 'jpg', 'jpeg', 'pdf'])
    
    if st.button("🗑️ 清空所有记录"):
        st.session_state.eng_p2_data = {"report": "", "scores": {"C": 0, "O": 0, "L": 0}}
        st.session_state.math_data = {"solution": ""}
        st.session_state.chat_history = []
        st.rerun()

# --- 5. 主页面布局 ---
header_class = "eng-bg" if "English" in subject else "math-bg"
st.markdown(f'<div class="main-header {header_class}"><h1>{subject} AI 超级导师</h1><p>一站式 DSE 备考方案</p></div>', unsafe_allow_html=True)

main_col, chat_col = st.columns([1.3, 0.7], gap="large")

# ==========================================
# 🏠 逻辑 A: 英文科界面
# ==========================================
if "English" in subject:
    with main_col:
        tabs = st.tabs(["📖 P1 Reading", "✍️ P2 Writing", "🎧 P3 Integrated", "🗣️ P4 Speaking"])
        
        with tabs[0]: # P1
            st.markdown("### 🔍 Reading 难句逻辑拆解")
            p1_in = st.text_area("输入复杂段落：", height=100, key="eng_p1")
            if st.button("AI 拆解思路"):
                res = client.models.generate_content(model="gemini-2.0-flash", contents=f"解析DSE閱讀：1.翻譯 2.句法 3.考點。原文：{p1_in}")
                st.info(res.text)

        with tabs[1]: # P2 (保留所有批改功能)
            st.markdown("### ✍️ 作文深度批改与 5** 范文")
            p2_part = st.radio("卷别", ["Part A", "Part B"], horizontal=True)
            user_p2 = st.text_area("在此粘贴作文内容...", height=200, key="eng_p2_in")
            if st.button("🚀 启动 AI 批改"):
                with st.spinner("阅卷主席评分中..."):
                    prompt = f"你是一位DSE閱卷主席。批改這篇 {p2_part} 作文。給出等級、C/O/L評分、5**範文。最後一行輸出: SCORES: C:數字, O:數字, L:數字。"
                    inputs = [prompt, user_p2]
                    if up_file: inputs.append(Image.open(up_file))
                    resp = client.models.generate_content(model="gemini-2.0-flash", contents=inputs)
                    st.session_state.eng_p2_data["report"] = resp.text
                    m = re.search(r"SCORES: C:(\d), O:(\d), L:(\d)", resp.text)
                    if m: st.session_state.eng_p2_data["scores"] = {"C": int(m.group(1)), "O": int(m.group(2)), "L": int(m.group(3))}
            
            if st.session_state.eng_p2_data["report"]:
                sc = st.session_state.eng_p2_data["scores"]
                st.markdown(f"**当前总分: {sum(sc.values())}/21**")
                fig = go.Figure(data=go.Scatterpolar(r=[sc['C'], sc['O'], sc['L'], sc['C']], theta=['C','O','L','C'], fill='toself'))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), height=250, margin=dict(t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)
                st.markdown(f'<div class="report-card">{st.session_state.eng_p2_data["report"]}</div>', unsafe_allow_html=True)

# ==========================================
# 📐 逻辑 B: 数学科界面
# ==========================================
else:
    with main_col:
        tabs = st.tabs(["📝 Paper 1 解答", "🎯 MC 秒杀技巧", "📊 函数绘图", "📚 公式大全"])
        
        with tabs[0]:
            st.markdown("### 📝 Step-by-Step 题目拆解")
            math_q = st.text_area("输入题目内容：", height=150, key="math_p1_in")
            if st.button("🚀 生成详细解题步骤"):
                with st.spinner("AI 计算中..."):
                    prompt = "你是一位DSE數學名師。請分步解答此題，指出考點並提供LaTeX公式。"
                    inputs = [prompt, math_q]
                    if up_file: inputs.append(Image.open(up_file))
                    res = client.models.generate_content(model="gemini-2.0-flash", contents=inputs)
                    st.session_state.math_data["solution"] = res.text
            if st.session_state.math_data["solution"]:
                st.markdown(f'<div class="report-card">{st.session_state.math_data["solution"]}</div>', unsafe_allow_html=True)

        with tabs[2]: # 绘图
            ca, cb, cc = st.columns(3)
            a = ca.number_input("a", value=1.0)
            b = cb.number_input("b", value=0.0)
            c = cc.number_input("c", value=0.0)
            x = np.linspace(-10, 10, 400)
            y = a*x**2 + b*x + c
            fig = go.Figure(data=go.Scatter(x=x, y=y, name="f(x)"))
            fig.update_layout(title=f"y = {a}x² + {b}x + {c}", height=300)
            st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 💬 右侧：全卷通用导师答疑
# ==========================================
with chat_col:
    st.markdown(f"### 💬 {subject} 导师在线")
    chat_box = st.container(height=500, border=True)
    with chat_box:
        for role, text in st.session_state.chat_history:
            with st.chat_message(role): st.write(text)
    
    if q := st.chat_input("针对当前内容追问..."):
        st.session_state.chat_history.append(("user", q))
        with st.chat_message("user"): st.write(q)
        # 上下文感知
        ctx = st.session_state.eng_p2_data["report"] if "English" in subject else st.session_state.math_data["solution"]
        res = client.models.generate_content(model="gemini-2.0-flash", contents=f"你是DSE {subject}專家。參考內容：{ctx}\n\n回答問題：{q}")
        st.session_state.chat_history.append(("assistant", res.text))
        st.rerun()
