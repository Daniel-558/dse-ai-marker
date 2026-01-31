import streamlit as st
from google.genai import Client
from google.genai import types as gen_types
import plotly.graph_objects as go
import re
from fpdf import FPDF
import io
from docx import Document
from PIL import Image

# 1. 页面配置
st.set_page_config(page_title="DSE AI 超级导师 Pro", layout="wide")

# 2. 核心 CSS 框架
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    h1 { color: #1e3a8a !important; font-weight: 800; text-align: center; }
    .score-card { background-color: white; border-radius: 12px; padding: 20px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); height: 100%; }
    .report-container { background: white; padding: 25px; border-radius: 15px; border-left: 6px solid #fbbf24; margin-top: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
    .stButton>button { background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; border-radius: 10px; font-weight: bold; height: 3.5em; width: 100%; border:none; }
    .download-btn { background: #10b981 !important; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 3. 初始化 API 客户端
api_key_val = st.secrets.get("GEMINI_API_KEY", "")
@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None
client = get_client(api_key_val)

# 4. 初始化 Session State
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "scores" not in st.session_state: st.session_state.scores = {"Content": 0, "Organization": 0, "Language": 0}
if "last_report" not in st.session_state: st.session_state.last_report = ""
if "extracted_text" not in st.session_state: st.session_state.extracted_text = ""

# --- 工具函数：PDF 生成 ---
def generate_pdf(report_text, scores):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('Arial', '', 'Arial.ttf', uni=True) # 注意：部署时需确保有字体文件，此处暂用标准字体
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, "DSE AI English Writing Report", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, f"Scores: Content: {scores['Content']} | Org: {scores['Organization']} | Lang: {scores['Language']}", ln=True)
    pdf.set_font("Helvetica", '', 10)
    pdf.multi_cell(0, 10, report_text.replace('**', ''))
    return pdf.output()

# 5. 侧边栏
with st.sidebar:
    st.title("🔐 成员准入")
    access_code = st.text_input("请输入邀请码", type="password")
    if access_code != "DSE2026":
        st.warning("验证口令")
        st.stop()
    st.success("验证通过")
    st.markdown("---")
    st.title("📂 文件处理中心")
    uploaded_file = st.file_uploader("支持 图片(手写)、PDF、Word", type=['png', 'jpg', 'jpeg', 'pdf', 'docx'])
    
    if uploaded_file:
        if uploaded_file.type in ["image/png", "image/jpeg"]:
            image = Image.open(uploaded_file)
            st.image(image, caption="已上传图片", use_container_width=True)
        else:
            st.write(f"已加载: {uploaded_file.name}")

# 6. 主界面
st.title("🤖 DSE AI 超级导师 Pro")

col1, col2 = st.columns([1.2, 0.8], gap="large")

with col1:
    st.markdown("### 📥 批改输入")
    task_type = st.selectbox("选择题型", ["Part A", "Part B", "Argumentative", "Letter to Editor"])
    target_lv = st.select_slider("目标等级", options=["3", "4", "5", "5*", "5**"])
    
    # 逻辑：如果上传了文件，优先处理文件
    user_text = st.text_area("或者在此手动粘贴作文...", height=150, value=st.session_state.extracted_text)
    
    if st.button("🚀 开始深度批改"):
        with st.spinner("AI 正在解析并评阅（包括多模态识别）..."):
            inputs = [f"你是一位DSE考官。请分析这篇{task_type}作文。最后输出: SCORES: C:数字, O:数字, L:数字"]
            
            if uploaded_file:
                if uploaded_file.type in ["image/png", "image/jpeg"]:
                    img = Image.open(uploaded_file)
                    inputs.append(img)
                elif uploaded_file.type == "application/pdf":
                    # 简单演示：PDF作为文件处理（Gemini支持直接传PDF）
                    inputs.append(uploaded_file.getvalue()) 
                elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    doc = Document(uploaded_file)
                    inputs.append("\n".join([p.text for p in doc.paragraphs]))
            else:
                inputs.append(user_text)

            response = client.models.generate_content(model="gemini-2.0-flash", contents=inputs)
            full_text = response.text
            
            score_match = re.search(r"SCORES: C:(\d), O:(\d), L:(\d)", full_text)
            if score_match:
                st.session_state.scores = {"Content": int(score_match.group(1)), "Organization": int(score_match.group(2)), "Language": int(score_match.group(3))}
            st.session_state.last_report = full_text.split("SCORES:")[0]

    # --- 仪表盘展现 ---
    if st.session_state.last_report:
        d1, d2 = st.columns([1, 1.2])
        with d1:
            total = sum(st.session_state.scores.values())
            st.markdown(f'<div class="score-card"><h2 style="text-align:center;">{total}/21</h2><hr>C: {st.session_state.scores["Content"]} | O: {st.session_state.scores["Organization"]} | L: {st.session_state.scores["Language"]}</div>', unsafe_allow_html=True)
            
            # PDF 生成与下载按钮
            pdf_bytes = generate_pdf(st.session_state.last_report, st.session_state.scores)
            st.download_button(label="📥 下载 PDF 诊断报告", data=pdf_bytes, file_name="DSE_Report.pdf", mime="application/pdf")
            
        with d2:
            fig = go.Figure(data=go.Scatterpolar(r=list(st.session_state.scores.values())+[list(st.session_state.scores.values())[0]], theta=['Content','Organization','Language','Content'], fill='toself', line_color='#fbbf24'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), showlegend=False, height=250, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(f'<div class="report-container">{st.session_state.last_report}</div>', unsafe_allow_html=True)

with col2:
    st.markdown("### 💬 导师互动")
    chat_box = st.container(height=500)
    with chat_box:
        for r, t in st.session_state.chat_history:
            with st.chat_message(r): st.write(t)
    if p_input := st.chat_input("追问导师..."):
        st.session_state.chat_history.append(("User", p_input))
        ans = client.models.generate_content(model="gemini-2.0-flash", contents=f"报告:{st.session_state.last_report}\n问题:{p_input}")
        st.session_state.chat_history.append(("AI", ans.text))
        st.rerun()
