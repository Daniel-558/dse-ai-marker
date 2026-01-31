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

# 2. 核心样式（优化范文显示块）
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    h1 { color: #1e3a8a !important; font-weight: 800; text-align: center; }
    .score-card { background-color: white; border-radius: 12px; padding: 20px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .report-container { background: white; padding: 25px; border-radius: 15px; border-left: 6px solid #fbbf24; margin-top: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); white-space: pre-wrap; }
    .model-essay { background-color: #f0fdf4; border: 1px solid #16a34a; padding: 20px; border-radius: 10px; margin-top: 15px; }
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

# 4. 侧边栏
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

# 5. 主界面
st.title("🤖 DSE AI 超级导师 Pro")

col1, col2 = st.columns([1.2, 0.8], gap="large")

with col1:
    st.markdown("### 📥 批改输入")
    task_type = st.selectbox("题型", ["Part A", "Part B", "Argumentative", "Letter to Editor"])
    target_lv = st.select_slider("目标等级", options=["3", "4", "5", "5*", "5**"])
    user_text = st.text_area("手动输入内容...", height=150)
    
    if st.button("🚀 开始 AI 识图与深度批改"):
        with st.spinner("AI 考官正在撰写 5** 示范范文..."):
            # 【核心改进】强化 Prompt，使用强制性指令和结构化要求
            prompt_content = [f"""
            你是一位DSE英文科資深閱卷員。請對這篇{task_type}作文進行深度批改。
            
            你的報告必須嚴格遵守以下結構：
            1. [評分分析]：簡述得分理由。
            2. [優缺點診斷]：列出具體的加分位與失分位。
            3. [5** 範文改寫]：這是最重要的部分。請針對本題題目，撰寫一段約 150 字的高級示範範文。要求使用 5** 級別的詞彙（如: ubiquitous, exacerbate, multifaceted）和複雜句式（如: Inversion, Relative Clauses）。
            4. [金句加持]：從範文中提取 3 個萬用金句。

            最後一行必須嚴格輸出: SCORES: C:數字, O:數字, L:數字 (每項滿分7)。
            請全部使用繁體中文。
            """]
            
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

        # 显示报告
        st.markdown(f'<div class="report-container">{st.session_state.last_report}</div>', unsafe_allow_html=True)

    # 金句实验室
    st.markdown("### ✨ 5** 金句实验室")
    s_input = st.text_input("输入普通句子进行 5** 升级：")
    if st.button("瞬间升华") and s_input:
        res = client.models.generate_content(model="gemini-2.0-flash", contents=f"将此句子升级为DSE Level 5**水平并解释加分点：{s_input}")
        st.info(res.text)

with col2:
    st.markdown("### 💬 导师答疑")
    chat_box = st.container(height=550)
    with chat_box:
        for role, text in st.session_state.chat_history:
            with st.chat_message(role): st.write(text)
    if p_input := st.chat_input("针对报告提问..."):
        st.session_state.chat_history.append(("User", p_input))
        with st.chat_message("User"): st.write(p_input)
        res = client.models.generate_content(model="gemini-2.0-flash", contents=f"针对作文报告回答问题: {p_input}\n相关上下文: {st.session_state.last_report}")
        st.session_state.chat_history.append(("AI", res.text))
        st.rerun()
