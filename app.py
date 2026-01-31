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

# --- 1. 页面配置与高级 UI ---
st.set_page_config(page_title="DSE AI 超级导师 All-in-One", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #f8fafc; }
    .main-header { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 2rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 25px; }
    .card { background: white; border-radius: 12px; padding: 20px; border: 1px solid #e2e8f0; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .report-container { background: white; padding: 25px; border-radius: 15px; border-left: 6px solid #fbbf24; white-space: pre-wrap; margin-top: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 8px; padding: 12px 24px; font-weight: bold; transition: 0.3s; }
    .stTabs [aria-selected="true"] { background-color: #3b82f6 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 初始化 API 与 Session State ---
api_key_val = st.secrets.get("GEMINI_API_KEY", "")
@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None
client = get_client(api_key_val)

if "p2_report" not in st.session_state: st.session_state.p2_report = ""
if "p2_scores" not in st.session_state: st.session_state.p2_scores = {"Content": 0, "Organization": 0, "Language": 0}
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# --- 3. PDF 生成函数 (支持中文逻辑) ---
def generate_pdf(report_text, scores):
    pdf = FPDF()
    pdf.add_page()
    # 试图加载字体，若无则回退
    font_path = "simhei.ttf"
    if os.path.exists(font_path):
        pdf.add_font('SimHei', '', font_path, uni=True)
        pdf.set_font('SimHei', '', 12)
        content = report_text
    else:
        pdf.set_font("Helvetica", 'B', 14)
        content = "Detailed Report (Chinese text omitted, view on web):\n\n" + "".join(re.findall(r'[a-zA-Z0-9\s.,!?:-]', report_text[:500]))
    
    pdf.cell(0, 10, "DSE English Diagnosis Report", ln=True, align='C')
    pdf.ln(5)
    pdf.cell(0, 10, f"Scores: C:{scores['Content']} O:{scores['Organization']} L:{scores['Language']}", ln=True)
    pdf.multi_cell(0, 8, content)
    return pdf.output()

# --- 4. 侧边栏：核心工具 ---
with st.sidebar:
    st.title("🔐 DSE Portal")
    if st.text_input("解锁码", type="password") != "DSE2026":
        st.warning("请输入解锁码")
        st.stop()
    
    st.markdown("---")
    st.markdown("### ⏳ 考试倒计时")
    days = (datetime(2026, 4, 10) - datetime.now()).days
    st.metric("DSE 2026 英文科", f"{days} Days")
    
    st.markdown("---")
    st.markdown("### 📂 资料扫描仪 (多模态)")
    uploaded_file = st.file_uploader("支持：作文照片/阅读文本/Data File", type=['png', 'jpg', 'jpeg', 'pdf'])
    
    st.markdown("---")
    st.markdown("### ⏱️ 模拟计时器")
    m_time = st.selectbox("设定练习时间 (Min)", [20, 45, 60, 120])
    if st.button("开始计时"): st.toast(f"计时开始，请在 {m_time} 分钟内完成！")

# --- 5. 主界面布局 ---
st.markdown('<div class="main-header"><h1>🤖 DSE English AI 超级导师 Pro</h1><p>全港首个 P1-P4 全方位 AI 备考平台</p></div>', unsafe_allow_html=True)

tabs = st.tabs(["📖 Paper 1 Reading", "✍️ Paper 2 Writing", "🎧 Paper 3 Integrated", "🗣️ Paper 4 Speaking"])

# --- PAPER 1: READING ---
with tabs[0]:
    st.markdown("### 🔍 难句精读与考点拆解")
    p1_text = st.text_area("粘贴 Reading 复杂句子或段落：", height=150, placeholder="The daunting prospect of global economic volatility...")
    if st.button("AI 思路拆解", key="p1_btn"):
        with st.spinner("分析中..."):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"你是一位DSE閱讀名師。請解析：1. 繁中翻譯 2. 語法結構（拆解主從句） 3. 預測考題（指代詞/作者態度） 4. 核心詞彙。原文：{p1_text}")
            st.info(res.text)

# --- PAPER 2: WRITING (完整回归) ---
with tabs[1]:
    col_p2_1, col_p2_2 = st.columns([1.2, 0.8])
    with col_p2_1:
        st.markdown("### ✍️ 作文深度批改")
        p2_type = st.radio("选择考部分", ["Part A (Short)", "Part B (Long)"], horizontal=True)
        target_lv = st.select_slider("目标等级", options=["3", "4", "5", "5*", "5**"])
        user_p2_text = st.text_area("在此输入作文...", height=300)
        
        if st.button("🚀 启动批改系统"):
            with st.spinner("阅卷主席评分中..."):
                prompt = f"""
                你是一位資深DSE閱卷主席。批改這篇 {p2_type} 作文，目標 {target_lv}。
                要求：
                1. [評分分析] 詳細解釋 C/O/L 得分。
                2. [優缺點] Markdown 列表。
                3. [5** 範文示範] 針對本題撰寫 200 字示範。
                4. [金句] 3 個萬用句。
                最後一行輸出: SCORES: C:數字, O:數字, L:數字 (每項滿分7)。
                使用繁體中文。
                """
                inputs = [prompt, user_p2_text]
                if uploaded_file and uploaded_file.type.startswith("image"):
                    inputs.append(Image.open(uploaded_file))
                
                response = client.models.generate_content(model="gemini-2.0-flash", contents=inputs)
                st.session_state.p2_report = response.text
                match = re.search(r"SCORES: C:(\d), O:(\d), L:(\d)", response.text)
                if match:
                    st.session_state.p2_scores = {"Content": int(match.group(1)), "Organization": int(match.group(2)), "Language": int(match.group(3))}

    with col_p2_2:
        if st.session_state.p2_report:
            total = sum(st.session_state.p2_scores.values())
            st.markdown(f"#### 实时评估: {total}/21")
            # 雷达图
            fig = go.Figure(data=go.Scatterpolar(r=list(st.session_state.p2_scores.values())+[list(st.session_state.p2_scores.values())[0]], theta=['C','O','L','C'], fill='toself', line_color='#3b82f6'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), height=250, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
            
            # PDF 下载
            try:
                pdf_bytes = generate_pdf(st.session_state.p2_report, st.session_state.p2_scores)
                st.download_button("📥 下载 5** 诊断报告", data=pdf_bytes, file_name="DSE_Report.pdf")
            except: st.error("PDF 导出受限")
            
            st.markdown(f'<div class="report-container">{st.session_state.p2_report}</div>', unsafe_allow_html=True)

# --- PAPER 3: INTEGRATED ---
with tabs[2]:
    st.markdown("### 🎧 P3 格式模版与整合技巧")
    p3_task = st.selectbox("选择任务文体", ["Formal Letter", "Report", "Proposal", "Article", "Email"])
    if st.button("生成 5** 规范"):
        res = client.models.generate_content(model="gemini-2.0-flash", contents=f"給出 DSE P3 {p3_task} 的 5** 格式模板、常用句式及 Data File 整合技巧。")
        st.success(res.text)

# --- PAPER 4: SPEAKING ---
with tabs[3]:
    st.markdown("### 🗣️ Speaking 论点生成器")
    spk_topic = st.text_input("输入口试题目 (e.g. Mandatory garbage bags)：")
    if st.button("脑暴 5** 观点"):
        res = client.models.generate_content(model="gemini-2.0-flash", contents=f"針對 '{spk_topic}' 提供 3 個深度論點、5 個高級詞彙、3 個 Group Discussion 轉折句。")
        st.info(res.text)

    st.markdown("---")
    # 底部通用：导师问答
    st.markdown("### 💬 导师答疑")
    chat_box = st.container(height=300)
    for r, t in st.session_state.chat_history:
        with chat_box: st.chat_message(r).write(t)
    
    if q := st.chat_input("问问导师关于 P1-P4 的任何问题..."):
        st.session_state.chat_history.append(("User", q))
        ans = client.models.generate_content(model="gemini-2.0-flash", contents=q)
        st.session_state.chat_history.append(("AI", ans.text))
        st.rerun()
