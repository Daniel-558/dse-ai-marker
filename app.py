import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import re
from fpdf import FPDF
import io
import os
from datetime import datetime
from PIL import Image

# 1. 页面配置与高级 UI
st.set_page_config(page_title="DSE English All-in-One Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #f8fafc; }
    .main-header { background: linear-gradient(135deg, #1e293b 0%, #334155 100%); padding: 1.5rem; border-radius: 12px; color: white; text-align: center; margin-bottom: 20px; }
    /* 重点：报告容器样式 */
    .report-card { background: white; padding: 25px; border-radius: 15px; border-left: 6px solid #3b82f6; box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-top: 15px; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 8px 8px 0 0; padding: 12px 20px; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #3b82f6 !important; color: white !important; }
    /* 聊天气泡样式 */
    .chat-bubble { padding: 10px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #e2e8f0; }
    </style>
    """, unsafe_allow_html=True)

# 2. 初始化持久化状态 (这是修复消失问题的关键)
if "p2_data" not in st.session_state:
    st.session_state.p2_data = {"report": "", "scores": {"C": 0, "O": 0, "L": 0}}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 初始化 API
api_key_val = st.secrets.get("GEMINI_API_KEY", "")
@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None
client = get_client(api_key_val)

# 3. PDF 导出修复逻辑
def safe_generate_pdf(report_text, scores):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "DSE English Writing Diagnosis Report", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(0, 10, f"Score: C:{scores['C']} O:{scores['O']} L:{scores['L']} | Total: {sum(scores.values())}/21", ln=True)
    pdf.ln(5)
    # 过滤掉无法在标准 PDF 中显示的 Unicode 字符，防止 FPDFUnicodeEncodingException
    safe_content = "".join([i if ord(i) < 128 else ' ' for i in report_text])
    pdf.multi_cell(0, 8, safe_content[:2000] + "\n\n[Please view full Chinese details on the web portal]")
    return pdf.output()

# 4. 侧边栏：全局工具
with st.sidebar:
    st.title("🔐 DSE Portal")
    if st.text_input("解锁码", type="password") != "DSE2026":
        st.info("验证以解锁 P1-P4 全功能")
        st.stop()
    
    st.markdown("---")
    days = (datetime(2026, 4, 10) - datetime.now()).days
    st.metric("DSE 2026 倒数", f"{days} 天")
    
    st.markdown("---")
    st.subheader("📂 资料上传 (识图/PDF)")
    up_file = st.file_uploader("支持：作文照片、阅读文本、Data File", type=['png', 'jpg', 'jpeg', 'pdf'])
    
    if st.button("🗑️ 清空所有记录"):
        st.session_state.p2_data = {"report": "", "scores": {"C": 0, "O": 0, "L": 0}}
        st.session_state.chat_history = []
        st.rerun()

# 5. 主页面布局：左功能区 | 右答疑区
st.markdown('<div class="main-header"><h1>🇬🇧 DSE English AI 超级导师 Pro</h1><p>Reading • Writing • Integrated • Speaking 全能工作站</p></div>', unsafe_allow_html=True)

left_col, right_col = st.columns([1.3, 0.7], gap="large")

# --- 左侧：核心功能 Tabs ---
with left_col:
    tabs = st.tabs(["📖 P1 Reading", "✍️ P2 Writing", "🎧 P3 Integrated", "🗣️ P4 Speaking"])

    # --- P1: Reading ---
    with tabs[0]:
        st.markdown("### 🔍 Reading 逻辑拆解")
        p1_input = st.text_area("输入复杂句子或段落：", height=150, placeholder="Once you paste a sentence here...", key="p1_txt")
        if st.button("AI 深度拆解"):
            with st.spinner("分析中..."):
                res = client.models.generate_content(model="gemini-2.0-flash", contents=f"解析DSE閱讀：1.翻譯 2.句法拆解 3.預測考點。原文：{p1_input}")
                st.info(res.text)

    # --- P2: Writing (修复核心：持久化显示报告) ---
    with tabs[1]:
        st.markdown("### ✍️ 作文深度批改与 5** 范文")
        p2_part = st.radio("选择考部分", ["Part A (Short)", "Part B (Long)"], horizontal=True)
        target_lv = st.select_slider("目标等级", options=["3", "4", "5", "5*", "5**"])
        user_p2 = st.text_area("在此输入作文内容...", height=250, placeholder="Start writing here...", key="p2_txt")
        
        if st.button("🚀 开始 AI 识图与深度批改"):
            with st.spinner("阅卷主席评分中..."):
                prompt = f"""你是一位資深DSE閱卷主席。批改這篇 {p2_part} 作文，目標 {target_lv}。
                內容須包含：1.等級評估 2.分項分析(C/O/L) 3.5**範文示範 4.改進建議。
                最後一行輸出：SCORES: C:數字, O:數字, L:數字。使用繁體中文。"""
                inputs = [prompt, user_p2]
                if up_file: inputs.append(Image.open(up_file))
                
                response = client.models.generate_content(model="gemini-2.0-flash", contents=inputs)
                st.session_state.p2_data["report"] = response.text
                
                # 提取分数
                match = re.search(r"SCORES: C:(\d), O:(\d), L:(\d)", response.text)
                if match:
                    st.session_state.p2_data["scores"] = {"C": int(match.group(1)), "O": int(match.group(2)), "L": int(match.group(3))}

        # ！！修复点：只要有报告，切换 Tab 回来依然显示 ！！
        if st.session_state.p2_data["report"]:
            st.markdown("---")
            rep_col, chart_col = st.columns([2, 1])
            with rep_col:
                st.subheader(f"批改结果 (总分: {sum(st.session_state.p2_data['scores'].values())}/21)")
                # PDF 导出按钮
                try:
                    pdf_bytes = safe_generate_pdf(st.session_state.p2_data["report"], st.session_state.p2_data["scores"])
                    st.download_button("📥 下载 5** 诊断报告", data=pdf_bytes, file_name="DSE_Writing_Report.pdf")
                except: pass
            with chart_col:
                # 雷达图可视化
                s = st.session_state.p2_data["scores"]
                fig = go.Figure(data=go.Scatterpolar(r=[s['C'], s['O'], s['L'], s['C']], theta=['C','O','L','C'], fill='toself', line_color='#3b82f6'))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), height=250, margin=dict(t=30, b=30, l=30, r=30))
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown(f'<div class="report-card">{st.session_state.p2_data["report"]}</div>', unsafe_allow_html=True)

    # --- P3: Integrated ---
    with tabs[2]:
        st.markdown("### 🎧 P3 格式库与整合技巧")
        p3_type = st.selectbox("选择任务类型", ["Formal Letter", "Report", "Proposal", "Article", "Email"])
        if st.button("获取 5** 格式模板"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"提供DSE P3 {p3_type} 的標准格式、常用句式及 Data File 整合技巧。")
            st.success(res.text)

    # --- P4: Speaking ---
    with tabs[3]:
        st.markdown("### 🗣️ Speaking 论点生成器")
        spk_topic = st.text_input("输入口试题目：", placeholder="e.g. Mandatory garbage bags in HK")
        if st.button("脑暴 5** 观点"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"針對'{spk_topic}'提供3個具備深度的論點、高級詞彙及轉折金句。")
            st.info(res.text)

# --- 右侧：全卷通用导师答疑 ---
with right_col:
    st.markdown("### 💬 导师实时答疑 (1-on-1)")
    st.caption("你可以在此针对 Paper 1-4 的任何问题进行追问。")
    
    chat_container = st.container(height=550, border=True)
    with chat_container:
        if not st.session_state.chat_history:
            st.info("👋 你好！我是你的 DSE AI 导师。你可以问我：\n- 为什么我这篇作文的 Language 只有 4 分？\n- 这个 Reading 难句怎么理解？\n- P3 的 Data File 怎么整合？")
        for role, text in st.session_state.chat_history:
            with st.chat_message(role):
                st.write(text)

    if q_input := st.chat_input("针对批改报告或考试内容提问..."):
        st.session_state.chat_history.append(("user", q_input))
        # 自动携带 Paper 2 的上下文
        ctx = f"当前批改报告内容：{st.session_state.p2_data['report']}" if st.session_state.p2_data['report'] else "暂无批改报告"
        full_prompt = f"上下文：{ctx}\n\n学生问题：{q_input}"
        
        with st.chat_message("user"): st.write(q_input)
        response = client.models.generate_content(model="gemini-2.0-flash", contents=full_prompt)
        st.session_state.chat_history.append(("assistant", response.text))
        st.rerun()
