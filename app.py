import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import re
from fpdf import FPDF
import io
import os
from datetime import datetime
from PIL import Image

# 1. 页面配置
st.set_page_config(page_title="DSE English All-in-One", layout="wide")

# 2. 增强 UI 样式
st.markdown("""
    <style>
    .stApp { background: #f8fafc; }
    .main-header { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 2rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 25px; }
    /* 报告容器样式 */
    .report-box { background: white; padding: 25px; border-radius: 15px; border-left: 6px solid #fbbf24; white-space: pre-wrap; margin-top: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
    /* 答疑区样式 */
    .chat-container { background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 15px; }
    /* 修复 Tab 样式 */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 8px 8px 0 0; padding: 10px 20px; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #3b82f6 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. 初始化 API 与持久化状态
api_key_val = st.secrets.get("GEMINI_API_KEY", "")
@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None
client = get_client(api_key_val)

# 核心：确保切换 Tab 时数据不丢失
if "p2_report" not in st.session_state: st.session_state.p2_report = ""
if "p2_scores" not in st.session_state: st.session_state.p2_scores = {"C": 0, "O": 0, "L": 0}
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# --- PDF 修复逻辑 (增加 UTF-8 兼容性提示) ---
def generate_pdf(report_text, scores):
    pdf = FPDF()
    pdf.add_page()
    # 这里的字体处理非常关键，防止报错
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "DSE English Diagnosis (Text Version)", ln=True, align='C')
    pdf.ln(10)
    pdf.multi_cell(0, 10, f"Scores -> Content: {scores['C']} | Org: {scores['O']} | Lang: {scores['L']}")
    pdf.ln(5)
    # 过滤掉无法在标准 PDF 中显示的特殊字符，防止编码错误
    safe_text = "".join([i if ord(i) < 128 else ' ' for i in report_text])
    pdf.multi_cell(0, 7, safe_text[:1000] + "\n\n[Note: Please view full Chinese report in the web portal.]")
    return pdf.output()

# 4. 侧边栏：全局工具
with st.sidebar:
    st.title("🔐 DSE Portal")
    if st.text_input("解锁码", type="password") != "DSE2026":
        st.info("验证以开启 P1-P4 全功能")
        st.stop()
    
    st.markdown("---")
    st.markdown(f"### ⏳ DSE 2026 倒数: **{(datetime(2026, 4, 10) - datetime.now()).days} Days**")
    
    st.markdown("---")
    uploaded_file = st.file_uploader("📂 资料扫描仪 (支持照片/PDF)", type=['png', 'jpg', 'jpeg', 'pdf'])
    
    st.markdown("---")
    if st.button("🧹 清除所有记录"):
        st.session_state.p2_report = ""
        st.session_state.chat_history = []
        st.rerun()

# 5. 主界面布局
st.markdown('<div class="main-header"><h1>🇬🇧 DSE English AI 超级导师 Pro</h1><p>全港首個 P1-P4 全方位 AI 備考平台</p></div>', unsafe_allow_html=True)

# 左右布局：左侧为 Paper 功能区，右侧为全局导师答疑
main_col, chat_col = st.columns([1.4, 0.6], gap="medium")

with main_col:
    tabs = st.tabs(["📖 P1 Reading", "✍️ P2 Writing", "🎧 P3 Integrated", "🗣️ P4 Speaking"])

    # --- P1: Reading ---
    with tabs[0]:
        st.markdown("### 🔍 Reading 逻辑拆解")
        p1_input = st.text_area("输入复杂段落：", height=150, key="p1_input")
        if st.button("AI 拆解思路"):
            with st.spinner("分析中..."):
                res = client.models.generate_content(model="gemini-2.0-flash", contents=f"解析DSE閱讀段落：1.翻譯 2.句法拆解 3.預測考點。原文：{p1_input}")
                st.info(res.text)

    # --- P2: Writing (修复：保持显示) ---
    with tabs[1]:
        st.markdown("### ✍️ 作文深度批改与 5** 范文")
        p2_part = st.radio("选择部分", ["Part A (Short)", "Part B (Long)"], horizontal=True)
        user_p2 = st.text_area("在此粘贴作文内容...", height=250, key="p2_main_input")
        
        if st.button("🚀 启动 AI 深度批改"):
            with st.spinner("阅卷主席评分中..."):
                prompt = f"""你是一位DSE閱卷主席。批改這篇 {p2_part} 作文。
                要求：1.[評分分析] 2.[優缺點] 3.[5** 範文示範]約200字 4.[金句]。
                最後一行必須輸出: SCORES: C:數字, O:數字, L:數字。使用繁體中文。"""
                inputs = [prompt, user_p2]
                if uploaded_file: inputs.append(Image.open(uploaded_file))
                
                response = client.models.generate_content(model="gemini-2.0-flash", contents=inputs)
                st.session_state.p2_report = response.text
                
                # 提取分数
                match = re.search(r"SCORES: C:(\d), O:(\d), L:(\d)", response.text)
                if match:
                    st.session_state.p2_scores = {"C": int(match.group(1)), "O": int(match.group(2)), "L": int(match.group(3))}
        
        # 即使切换 Tab 也会保持显示的报告区
        if st.session_state.p2_report:
            st.markdown("---")
            score_col, pdf_col = st.columns([2, 1])
            with score_col:
                st.subheader(f"总分: {sum(st.session_state.p2_scores.values())}/21")
                # 雷达图可视化
                fig = go.Figure(data=go.Scatterpolar(
                    r=[st.session_state.p2_scores['C'], st.session_state.p2_scores['O'], st.session_state.p2_scores['L'], st.session_state.p2_scores['C']],
                    theta=['Content','Organization','Language','Content'], fill='toself'
                ))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), height=300, margin=dict(t=30, b=30))
                st.plotly_chart(fig, use_container_width=True)
            with pdf_col:
                try:
                    pdf_data = generate_pdf(st.session_state.p2_report, st.session_state.p2_scores)
                    st.download_button("📥 下载诊断报告", data=pdf_data, file_name="DSE_Report.pdf")
                except: st.warning("PDF 下载暂不可用")
            
            st.markdown(f'<div class="report-box">{st.session_state.p2_report}</div>', unsafe_allow_html=True)

    # --- P3: Integrated ---
    with tabs[2]:
        st.markdown("### 🎧 P3 整合技巧")
        p3_type = st.selectbox("任务文体", ["Formal Letter", "Report", "Proposal", "Article"])
        if st.button("获取 5** 格式模板"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"提供DSE P3 {p3_type} 的5**格式及Data File搵point技巧。")
            st.success(res.text)

    # --- P4: Speaking ---
    with tabs[3]:
        st.markdown("### 🗣️ Speaking 论点库")
        spk_topic = st.text_input("输入口试题目：")
        if st.button("脑暴 5** 观点"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"針對'{spk_topic}'提供3個深度論點及轉折金句。")
            st.info(res.text)

# 6. 右侧：全局导师答疑 (不再随 Tab 消失)
with chat_col:
    st.markdown("### 💬 导师实时答疑")
    st.caption("你可以在此针对任何卷别或批改结果进行追问。")
    
    chat_box = st.container(height=500, border=True)
    with chat_box:
        for r, t in st.session_state.chat_history:
            with st.chat_message(r): st.write(t)
            
    if q := st.chat_input("针对批改报告或 DSE 提问..."):
        st.session_state.chat_history.append(("user", q))
        # 自动关联 Paper 2 的上下文
        context = f"学生当前的批改报告是：{st.session_state.p2_report}" if st.session_state.p2_report else ""
        res = client.models.generate_content(model="gemini-2.0-flash", contents=f"{context}\n\n学生问题：{q}")
        st.session_state.chat_history.append(("assistant", res.text))
        st.rerun()
