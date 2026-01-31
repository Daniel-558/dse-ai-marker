import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import re
from fpdf import FPDF
import io
import os
from docx import Document
from PIL import Image

# 1. 页面配置
st.set_page_config(page_title="DSE AI 超级导师 Pro", layout="wide")

# 2. 核心 CSS (包含范文卡片样式)
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    h1 { color: #1e3a8a !important; font-weight: 800; text-align: center; }
    .score-card { background-color: white; border-radius: 12px; padding: 20px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .report-container { background: white; padding: 25px; border-radius: 15px; border-left: 6px solid #fbbf24; margin-top: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); white-space: pre-wrap; }
    .stButton>button { background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; border-radius: 10px; font-weight: bold; height: 3.5em; width: 100%; border:none; }
    .lab-card { background: #eff6ff; padding: 15px; border-radius: 10px; border: 1px dashed #1e3a8a; margin-top: 10px; }
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

# --- PDF 生成逻辑 ---
def generate_pdf(report_text, scores):
    pdf = FPDF()
    pdf.add_page()
    font_path = "simhei.ttf" 
    if os.path.exists(font_path):
        pdf.add_font('SourceHan', '', font_path, uni=True)
        pdf.set_font('SourceHan', '', 12)
        content = report_text
    else:
        pdf.set_font("Helvetica", 'B', 14)
        content = "Detailed Report (Please view Chinese content in web portal):\n\n" + report_text[:300].encode('ascii', 'ignore').decode()
    
    pdf.cell(0, 10, "DSE English Writing Diagnosis", ln=True, align='C')
    pdf.ln(5)
    pdf.cell(0, 10, f"Scores -> C:{scores['Content']} O:{scores['Organization']} L:{scores['Language']}", ln=True)
    pdf.multi_cell(0, 8, content)
    return pdf.output()

# 4. 侧边栏：工具箱与参考
with st.sidebar:
    st.title("🔐 成员准入")
    access_code = st.text_input("验证码", type="password")
    if access_code != "DSE2026":
        st.warning("解锁后开启 5** 功能")
        st.stop()
    st.success("DSE 模式已激活")
    
    st.markdown("---")
    st.title("📂 多模态提交")
    uploaded_file = st.file_uploader("识图/文档上传", type=['png', 'jpg', 'jpeg', 'pdf', 'docx'])

    st.markdown("---")
    st.title("🌟 5** 必备参考")
    with st.expander("🔥 高分连词表"):
        st.write("- **Addition:** Furthermore, Notably\n- **Contrast:** Paradoxically, Conversely\n- **Cause:** Stemming from, Attributed to")
    
    with st.expander("💎 5** 词汇替换"):
        st.table({"普通": ["Think", "Help", "Big"], "Elite": ["Advocate", "Facilitate", "Substantial"]})

# 5. 主界面
st.title("🤖 DSE AI 超级导师 Pro")

col1, col2 = st.columns([1.2, 0.8], gap="large")

with col1:
    # 选项区
    st.markdown("### 📥 批改输入")
    task_type = st.selectbox("题型", ["Part A", "Part B", "Argumentative", "Letter to Editor"])
    target_lv = st.select_slider("目标等级", options=["3", "4", "5", "5*", "5**"])
    user_text = st.text_area("手动输入内容...", height=150)
    
    if st.button("🚀 开始 AI 识图与深度批改"):
        with st.spinner("AI 考官正在分析并生成 5** 示范..."):
            prompt_content = [f"你是一位DSE考官。请分析作文。必须包含：1.评分 2.优缺点 3.针对本题的 Level 5** 范文节选。最后一行严格输出: SCORES: C:数字, O:数字, L:数字。使用繁体中文。"]
            
            if uploaded_file:
                if uploaded_file.type in ["image/png", "image/jpeg"]:
                    prompt_content.append(Image.open(uploaded_file))
                elif uploaded_file.type == "application/pdf":
                    prompt_content.append(uploaded_file.getvalue())
                elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    doc = Document(uploaded_file)
                    prompt_content.append("\n".join([p.text for p in doc.paragraphs]))
            else:
                prompt_content.append(user_text)

            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt_content)
            full_text = response.text
            
            score_match = re.search(r"SCORES: C:(\d), O:(\d), L:(\d)", full_text)
            if score_match:
                st.session_state.scores = {"Content": int(score_match.group(1)), "Organization": int(score_match.group(2)), "Language": int(score_match.group(3))}
            st.session_state.last_report = full_text.split("SCORES:")[0]

    # --- 仪表盘与 PDF ---
    if st.session_state.last_report:
        d1, d2 = st.columns([1, 1.2])
        with d1:
            total = sum(st.session_state.scores.values())
            st.markdown(f'<div class="score-card"><h3 style="text-align:center;">总分 {total}/21</h3><p>C: {st.session_state.scores["Content"]} | O: {st.session_state.scores["Organization"]} | L: {st.session_state.scores["Language"]}</p></div>', unsafe_allow_html=True)
            try:
                pdf_data = generate_pdf(st.session_state.last_report, st.session_state.scores)
                st.download_button("📥 导出诊断报告 (PDF)", data=pdf_data, file_name="DSE_Report.pdf", mime="application/pdf")
            except:
                st.error("PDF 导出暂不可用")
        with d2:
            fig = go.Figure(data=go.Scatterpolar(r=list(st.session_state.scores.values())+[list(st.session_state.scores.values())[0]], theta=['Content','Organization','Language','Content'], fill='toself', line_color='#fbbf24'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), showlegend=False, height=220, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(f'<div class="report-container">{st.session_state.last_report}</div>', unsafe_allow_html=True)

    # --- 亮点功能：金句实验室 ---
    st.markdown("---")
    st.markdown("### ✨ 5** 金句实验室")
    s_input = st.text_input("输入普通句子，由导师为你升级：")
    if st.button("瞬间升华") and s_input:
        with st.spinner("正在炼金..."):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"将此句子升级为DSE Level 5**水平并解释加分点：{s_input}")
            st.markdown(f'<div class="lab-card">{res.text}</div>', unsafe_allow_html=True)

with col2:
    st.markdown("### 💬 导师答疑")
    chat_box = st.container(height=550)
    with chat_box:
        for role, text in st.session_state.chat_history:
            with st.chat_message(role): st.write(text)
    if p_input := st.chat_input("针对报告提问..."):
        st.session_state.chat_history.append(("User", p_input))
        with st.chat_message("User"): st.write(p_input)
        res = client.models.generate_content(model="gemini-2.0-flash", contents=f"基于报告内容回答问题: {p_input}")
        st.session_state.chat_history.append(("AI", res.text))
        st.rerun()
