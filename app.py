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

# 2. 核心样式
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    h1 { color: #1e3a8a !important; font-weight: 800; text-align: center; }
    .score-card { background-color: white; border-radius: 12px; padding: 20px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
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

# --- 核心更新：安全的 PDF 生成函数 ---
def generate_pdf(report_text, scores):
    pdf = FPDF()
    pdf.add_page()
    
    # 检查根目录下是否有中文字体文件
    font_path = "simhei.ttf" # 确保你上传了此文件到 GitHub
    if os.path.exists(font_path):
        pdf.add_font('SourceHan', '', font_path, uni=True)
        pdf.set_font('SourceHan', '', 14)
        has_font = True
    else:
        pdf.set_font("Helvetica", 'B', 14)
        has_font = False

    pdf.cell(0, 10, "DSE English Writing Report", ln=True, align='C')
    pdf.ln(10)
    
    score_line = f"Scores -> Content: {scores['Content']} | Org: {scores['Organization']} | Lang: {scores['Language']}"
    pdf.cell(0, 10, score_line, ln=True)
    pdf.ln(5)
    
    # 如果没字体，PDF 只显示英文提示，防止报错
    if not has_font:
        pdf.set_font("Helvetica", '', 10)
        content = "Please upload simhei.ttf to GitHub to enable Chinese PDF export.\n\nSummary:\n" + report_text[:300].encode('ascii', 'ignore').decode()
    else:
        content = report_text
        
    pdf.multi_cell(0, 8, content)
    return pdf.output()

# 4. 侧边栏
with st.sidebar:
    st.title("🔐 成员准入")
    access_code = st.text_input("请输入邀请码", type="password")
    if access_code != "DSE2026":
        st.warning("验证口令")
        st.stop()
    st.success("验证通过")
    st.markdown("---")
    st.title("📂 多模态提交")
    uploaded_file = st.file_uploader("上传图片(识图)或文档(PDF/Word)", type=['png', 'jpg', 'jpeg', 'pdf', 'docx'])

# 5. 主界面
st.title("🤖 DSE AI 超级导师 Pro")

col1, col2 = st.columns([1.2, 0.8], gap="large")

with col1:
    st.markdown("### 📥 批改输入")
    task_type = st.selectbox("选择题型", ["Part A", "Part B", "Argumentative", "Letter to Editor"])
    target_lv = st.select_slider("目标等级", options=["3", "4", "5", "5*", "5**"])
    user_text = st.text_area("或者在此手动输入内容...", height=150)
    
    if st.button("🚀 开始 AI 识图与深度批改"):
        with st.spinner("AI 考官正在分析图片及文字..."):
            prompt_content = [f"你是一位DSE考官。请分析作文。必须严格在最后一行输出: SCORES: C:数字, O:数字, L:数字。使用繁体中文。"]
            
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

    if st.session_state.last_report:
        st.markdown("---")
        d1, d2 = st.columns([1, 1.2])
        with d1:
            total = sum(st.session_state.scores.values())
            st.markdown(f'<div class="score-card"><h3 style="text-align:center;">总分 {total}/21</h3><p>Content: {st.session_state.scores["Content"]}<br>Org: {st.session_state.scores["Organization"]}<br>Lang: {st.session_state.scores["Language"]}</p></div>', unsafe_allow_html=True)
            
            # PDF 按钮：带异常捕获
            try:
                pdf_data = generate_pdf(st.session_state.last_report, st.session_state.scores)
                st.download_button("📥 导出诊断报告 (PDF)", data=pdf_data, file_name="DSE_Report.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"PDF生成暂时受限（缺少中文字体文件）")

        with d2:
            cat = list(st.session_state.scores.keys())
            val = list(st.session_state.scores.values())
            fig = go.Figure(data=go.Scatterpolar(r=val+[val[0]], theta=cat+[cat[0]], fill='toself', line_color='#fbbf24', fillcolor='rgba(251, 191, 36, 0.3)'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), showlegend=False, height=280, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(f'<div class="report-container">{st.session_state.last_report}</div>', unsafe_allow_html=True)

with col2:
    st.markdown("### 💬 导师答疑")
    chat_box = st.container(height=550)
    with chat_box:
        for role, text in st.session_state.chat_history:
            with st.chat_message(role): st.write(text)
            
    if p_input := st.chat_input("针对报告提问..."):
        st.session_state.chat_history.append(("User", p_input))
        with st.chat_message("User"): st.write(p_input)
        with st.chat_message("AI"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"报告内容:{st.session_state.last_report}\n问题:{p_input}")
            st.write(res.text)
            st.session_state.chat_history.append(("AI", res.text))
            st.rerun()
