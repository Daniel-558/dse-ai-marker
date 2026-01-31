import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import re
from fpdf import FPDF
import io
from docx import Document
from PIL import Image

# 1. 页面配置
st.set_page_config(page_title="DSE AI 超级导师 Pro", layout="wide")

# 2. 核心 CSS
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    h1 { color: #1e3a8a !important; font-weight: 800; text-align: center; }
    .score-card { background-color: white; border-radius: 12px; padding: 20px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); height: 100%; }
    .report-container { background: white; padding: 25px; border-radius: 15px; border-left: 6px solid #fbbf24; margin-top: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); white-space: pre-wrap; }
    .stButton>button { background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; border-radius: 10px; font-weight: bold; height: 3.5em; width: 100%; border:none; }
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

# --- 增强工具：PDF 生成 (适配中文字符) ---
def generate_pdf(report_text, scores):
    pdf = FPDF()
    pdf.add_page()
    # 使用自带的核心字体，如果需要完美显示中文，需在项目下放一个 .ttf 字体文件
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, "DSE English Writing Diagnosis Report", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, f"Scores -> Content: {scores['Content']} | Org: {scores['Organization']} | Lang: {scores['Language']}", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", '', 10)
    # PDF 暂不支持复杂中文渲染，此处主要导出报告架构，详细内容建议网页查看
    pdf.multi_cell(0, 8, "Note: Full detailed feedback is available in the web portal.\n\nSummary Content:\n" + report_text[:500] + "...")
    return pdf.output()

# 4. 侧边栏
with st.sidebar:
    st.title("🔐 成员准入")
    access_code = st.text_input("请输入邀请码", type="password")
    if access_code != "DSE2026":
        st.warning("口令错误")
        st.stop()
    st.success("验证成功")
    st.markdown("---")
    st.title("📂 多模态提交")
    uploaded_file = st.file_uploader("上传图片(识图)或文档(PDF/Word)", type=['png', 'jpg', 'jpeg', 'pdf', 'docx'])

# 5. 主界面
st.title("🤖 DSE AI 超级导师 Pro")

col1, col2 = st.columns([1.2, 0.8], gap="large")

with col1:
    st.markdown("### 📥 批改输入区")
    task_type = st.selectbox("选择题型", ["Part A", "Part B", "Argumentative", "Letter to Editor"])
    target_lv = st.select_slider("目标等级", options=["3", "4", "5", "5*", "5**"])
    user_text = st.text_area("手动输入或在左侧上传文件...", height=150)
    
    if st.button("🚀 开始 AI 识图与深度批改"):
        with st.spinner("AI 正在解析内容（包括识图）并评分..."):
            # 准备多模态输入
            prompt_content = [f"你是一位DSE考官。请分析作文。必须输出: SCORES: C:数字, O:数字, L:数字。使用繁体中文。"]
            
            if uploaded_file:
                if uploaded_file.type in ["image/png", "image/jpeg"]:
                    prompt_content.append(Image.open(uploaded_file))
                elif uploaded_file.type == "application/pdf":
                    prompt_content.append(uploaded_file.getvalue()) # Gemini 2.0 支持原生 PDF 字节流
                elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    doc = Document(uploaded_file)
                    text = "\n".join([p.text for p in doc.paragraphs])
                    prompt_content.append(text)
            else:
                prompt_content.append(user_text)

            # 使用支持识图的最新模型
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt_content)
            full_text = response.text
            
            # 提取分数
            score_match = re.search(r"SCORES: C:(\d), O:(\d), L:(\d)", full_text)
            if score_match:
                st.session_state.scores = {"Content": int(score_match.group(1)), "Organization": int(score_match.group(2)), "Language": int(score_match.group(3))}
            st.session_state.last_report = full_text.split("SCORES:")[0]

    if st.session_state.last_report:
        st.markdown("---")
        d1, d2 = st.columns([1, 1.2])
        with d1:
            total = sum(st.session_state.scores.values())
            st.markdown(f'<div class="score-card"><h3 style="text-align:center;">总分 {total}/21</h3><p>Content: {st.session_state.scores["Content"]}<br>Org: {st.session_state.scores["Organization"]}<br>Lang: {st.session_state.scores["Language"]}</p></div>', unsafe_allow_html=True)
            
            # PDF 导出按钮
            pdf_data = generate_pdf(st.session_state.last_report, st.session_state.scores)
            st.download_button("📥 导出 PDF 诊断书", data=pdf_data, file_name="DSE_AI_Report.pdf", mime="application/pdf")

        with d2:
            fig = go.Figure(data=go.Scatterpolar(r=list(st.session_state.scores.values())+[list(st.session_state.scores.values())[0]], theta=['Content','Organization','Language','Content'], fill='toself', line_color='#fbbf24'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), showlegend=False, height=250, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(f'<div class="report-container">{st.session_state.last_report}</div>', unsafe_allow_html=True)

with col2:
    st.markdown("### 💬 导师答疑")
    chat_container = st.container(height=500)
    with chat_container:
        for role, text in st.session_state.chat_history:
            with st.chat_message(role): st.write(text)
            
    if p_input := st.chat_input("问问导师..."):
        st.session_state.chat_history.append(("User", p_input))
        with st.chat_message("User"): st.write(p_input)
        with st.chat_message("AI"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"报告内容:{st.session_state.last_report}\n问题:{p_input}")
            st.write(res.text)
            st.session_state.chat_history.append(("AI", res.text))
            st.rerun()
