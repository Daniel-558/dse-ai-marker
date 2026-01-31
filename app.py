import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import re
from fpdf import FPDF
import io
import os
from datetime import datetime
from docx import Document
from PIL import Image

# 1. 页面配置
st.set_page_config(page_title="DSE English All-in-One", layout="wide")

# 2. 深度定制 UI
st.markdown("""
    <style>
    .stApp { background: #f8fafc; }
    .main-header { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 1.5rem; border-radius: 12px; color: white; text-align: center; margin-bottom: 20px; }
    .card { background: white; border-radius: 10px; padding: 20px; border: 1px solid #e2e8f0; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 8px 8px 0 0; padding: 10px 20px; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #3b82f6 !important; color: white !important; }
    .report-box { background: white; padding: 25px; border-radius: 15px; border-left: 6px solid #fbbf24; white-space: pre-wrap; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# 3. 初始化 API
api_key_val = st.secrets.get("GEMINI_API_KEY", "")
@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None
client = get_client(api_key_val)

# 初始化状态
if "p2_report" not in st.session_state: st.session_state.p2_report = ""
if "p2_scores" not in st.session_state: st.session_state.p2_scores = {"C": 0, "O": 0, "L": 0}

# 4. 侧边栏
with st.sidebar:
    st.title("🔐 DSE Portal")
    if st.text_input("解锁码", type="password") != "DSE2026":
        st.info("验证以开启 P1-P4 全功能")
        st.stop()
    
    st.markdown("---")
    st.markdown("### 📅 备考倒计时")
    days = (datetime(2026, 4, 10) - datetime.now()).days
    st.metric("距离 2026 DSE 英文科", f"{days} 天")
    
    st.markdown("---")
    st.markdown("### 📂 资料扫描仪")
    uploaded_file = st.file_uploader("支持：作文照片/阅读难段/P3 Data File", type=['png', 'jpg', 'jpeg', 'pdf'])

# 5. 主界面
st.markdown('<div class="main-header"><h1>🇬🇧 DSE English AI 超级导师 Pro</h1><p>Reading • Writing • Listening • Speaking 一站式升等平台</p></div>', unsafe_allow_html=True)

tabs = st.tabs(["📖 Paper 1 Reading", "✍️ Paper 2 Writing", "🎧 Paper 3 Integrated", "🗣️ Paper 4 Speaking"])

# --- TAB 1: Paper 1 Reading ---
with tabs[0]:
    st.markdown("### 🔍 Reading 逻辑拆解与长难句")
    p1_text = st.text_area("粘贴 Text A/B 的复杂句子或段落：", height=150, placeholder="The daunting prospect of global economic volatility has underscored the need for...")
    if st.button("AI 导师拆解思路", key="p1_btn"):
        with st.spinner("正在进行句法与考点分析..."):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"你是一位DSE閱讀名師。請解析此段落：1. 繁體中文對譯 2. 語法結構（拆解主從句） 3. 預測考題（指代詞/作者態度/填充） 4. 核心詞彙表。原文：{p1_text}")
            st.info(res.text)

# --- TAB 2: Paper 2 Writing (完整保留并优化) ---
with tabs[1]:
    col1, col2 = st.columns([1.2, 0.8])
    with col1:
        st.markdown("### ✍️ 作文批改系统")
        p2_part = st.radio("选择考部分", ["Part A (Short)", "Part B (Long)"], horizontal=True)
        p2_input = st.text_area("在此粘贴作文内容...", height=300, key="p2_area")
        if st.button("🚀 提交批改 & 生成 5** 范文"):
            with st.spinner("阅卷主席正在评分..."):
                prompt = f"""
                你是一位資深DSE閱卷主席。請對這篇 {p2_part} 作文進行批改。
                報告結構：
                1. [預估等級] (3 - 5**)
                2. [分項診斷] (Content/Org/Lang)
                3. [5** 範文示範]：撰寫約 200 字的高級示範。
                4. [金句升華]：3 個萬用金句。
                最後一行輸出: SCORES: C:數字, O:數字, L:數字 (每項滿分7)。
                """
                inputs = [prompt, p2_input]
                if uploaded_file and uploaded_file.type.startswith("image"):
                    inputs.append(Image.open(uploaded_file))
                res = client.models.generate_content(model="gemini-2.0-flash", contents=inputs)
                st.session_state.p2_report = res.text
                match = re.search(r"SCORES: C:(\d), O:(\d), L:(\d)", res.text)
                if match:
                    st.session_state.p2_scores = {"C": int(match.group(1)), "O": int(match.group(2)), "L": int(match.group(3))}
    
    with col2:
        if st.session_state.p2_report:
            total = sum(st.session_state.p2_scores.values())
            st.markdown(f"**总分预览: {total}/21**")
            fig = go.Figure(data=go.Scatterpolar(r=list(st.session_state.p2_scores.values())+[list(st.session_state.p2_scores.values())[0]], theta=['C','O','L','C'], fill='toself'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), height=250, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(f'<div class="report-box">{st.session_state.p2_report}</div>', unsafe_allow_html=True)

# --- TAB 3: Paper 3 Integrated ---
with tabs[2]:
    st.markdown("### 🎧 Integrated Skills 格式与逻辑")
    st.write("上传 Data File 或输入 Task 要求，AI 帮你理清整合逻辑。")
    task_type = st.selectbox("选择 Task 格式", ["Formal Letter", "Report", "Proposal", "Feature Article", "Email"])
    if st.button("查看 5** 格式模版 & 整合技巧"):
        with st.spinner("调取历年 5** 范例中..."):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"請給出 DSE P3 {task_type} 的 5** 標准格式模版，並列出在 Data File 搵 Point 時的常見陷阱 (Distractors)。")
            st.success(res.text)

# --- TAB 4: Paper 4 Speaking ---
with tabs[3]:
    st.markdown("### 🗣️ Speaking 论点库与模拟答疑")
    spk_topic = st.text_input("输入口试题目 (e.g. Benefits of social media for learning):")
    if st.button("生成 5** 论点"):
        with st.spinner("脑暴中..."):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"針對 DSE Speaking 題目 '{spk_topic}'：1. 提供 3 個具備深度(Insightful)的論點 2. 提供 3 組高級轉折詞 3. 模擬一段 1 分鐘的 Individual Response 優質回答。")
            st.info(res.text)

    st.markdown("---")
    st.markdown("### ✨ 1-on-1 导师答疑")
    chat_box = st.container(height=300)
    # 此处可接入之前的对话逻辑
    if query := st.chat_input("问问导师任何关于 DSE 的问题..."):
        with chat_box:
            st.chat_message("user").write(query)
            ans = client.models.generate_content(model="gemini-2.0-flash", contents=query)
            st.chat_message("assistant").write(ans.text)
