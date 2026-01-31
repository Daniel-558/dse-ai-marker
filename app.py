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

# 2. 核心样式 (UI 框架)
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    h1 { color: #1e3a8a !important; font-weight: 800; text-align: center; }
    .score-card { background-color: white; border-radius: 12px; padding: 20px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .report-container { background: white; padding: 25px; border-radius: 15px; border-left: 6px solid #fbbf24; margin-top: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); white-space: pre-wrap; }
    .stButton>button { background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; border-radius: 10px; font-weight: bold; height: 3.5em; width: 100%; border:none; }
    .download-error { color: #ef4444; font-size: 0.8em; text-align: center; margin-top: 5px; }
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

# --- PDF 安全生成逻辑 ---
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
        # 如果没字体，只抓取前300个非中文字符，防止崩溃
        content = "Detailed feedback contains Chinese. Please view on web dashboard.\n\nScore Summary:\n" + "".join(re.findall(r'[a-zA-Z0-9\s.,!?:-]', report_text[:300]))
    
    pdf.cell(0, 10, "DSE English Writing Diagnosis Report", ln=True, align='C')
    pdf.ln(5)
    pdf.cell(0, 10, f"Scores -> Content: {scores['Content']} | Org: {scores['Organization']} | Lang: {scores['Language']}", ln=True)
    pdf.multi_cell(0, 8, content)
    return pdf.output()

# 4. 侧边栏
with st.sidebar:
    st.title("🔐 成员准入")
    access_code = st.text_input("请输入邀请码", type="password")
    if access_code != "DSE2026":
        st.warning("验证口令以解锁全功能")
        st.stop()
    st.success("DSE 模式已激活")
    
    st.markdown("---")
    st.title("📂 多模态提交")
    uploaded_file = st.file_uploader("支持照片识图 / PDF / Word", type=['png', 'jpg', 'jpeg', 'pdf', 'docx'])

# 5. 主界面
st.title("🤖 DSE AI 超级导师 Pro")

col1, col2 = st.columns([1.2, 0.8], gap="large")

with col1:
    st.markdown("### 📥 批改输入")
    # 题型更新为 DSE 完整版
    task_type = st.selectbox("选择题型", [
        "Part A (Short Exercise)", 
        "Part B (Argumentative)", 
        "Part B (Letter to Editor)", 
        "Part B (Report/Proposal)", 
        "Part B (Story/Feature Article)",
        "Part B (Formal Letter)"
    ])
    target_lv = st.select_slider("目标等级", options=["3", "4", "5", "5*", "5**"])
    user_text = st.text_area("手动输入作文或在左侧上传文件...", height=150)
    
    if st.button("🚀 开始 AI 识图与深度批改"):
        with st.spinner("AI 考官正在深度评阅并撰写 5** 范文..."):
            # 强化 Prompt，确保范文输出
            prompt_content = [f"""
            你是一位DSE英文科閱卷主席。請對這篇{task_type}作文進行批改。
            
            報告必須嚴格包含以下模塊：
            1. [評分分析]：詳細解釋 C/O/L 得分。
            2. [優缺點診斷]：使用 Markdown 列表形式。
            3. [針對本題題目的 Level 5** 範文示範]：請親自撰寫一段約 150-200 字的 5** 範文示範，展示高級句式和詞彙。
            4. [金句加持]：列出 3 個可直接應用的 5** 萬用金句。

            最後一行必須嚴格輸出: SCORES: C:數字, O:數字, L:數字
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

            # 使用 Gemini 2.0 Flash 提升速度和识图精度
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt_content)
            full_text = response.text
            
            score_match = re.search(r"SCORES: C:(\d), O:(\d), L:(\d)", full_text)
            if score_match:
                st.session_state.scores = {"Content": int(score_match.group(1)), "Organization": int(score_match.group(2)), "Language": int(score_match.group(3))}
            st.session_state.last_report = full_text.split("SCORES:")[0]

    # --- 仪表盘展现 ---
    if st.session_state.last_report:
        st.markdown("---")
        d1, d2 = st.columns([1, 1.2])
        with d1:
            total = sum(st.session_state.scores.values())
            st.markdown(f"""
            <div class="score-card">
                <h3 style="text-align:center; color:#1e3a8a; margin:0;">总分 {total}/21</h3>
                <hr style="margin:10px 0;">
                <p style="text-align:center;">C:{st.session_state.scores['Content']} | O:{st.session_state.scores['Organization']} | L:{st.session_state.scores['Language']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # PDF 下载逻辑
            try:
                pdf_data = generate_pdf(st.session_state.last_report, st.session_state.scores)
                st.download_button("📥 导出 PDF 诊断报告", data=pdf_data, file_name="DSE_AI_Report.pdf", mime="application/pdf")
            except:
                st.markdown('<p class="download-error">PDF 导出受限 (请在网页查看繁体详情)</p>', unsafe_allow_html=True)
                
        with d2:
            fig = go.Figure(data=go.Scatterpolar(r=list(st.session_state.scores.values())+[list(st.session_state.scores.values())[0]], theta=['Content','Organization','Language','Content'], fill='toself', line_color='#fbbf24', fillcolor='rgba(251, 191, 36, 0.3)'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), showlegend=False, height=220, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(f'<div class="report-container">{st.session_state.last_report}</div>', unsafe_allow_html=True)

with col2:
    st.markdown("### 💬 1-on-1 导师答疑")
    chat_box = st.container(height=550)
    with chat_box:
        if not st.session_state.last_report:
            st.info("生成批改报告后，可针对 5** 范文细节向导师追问。")
        for role, text in st.session_state.chat_history:
            with st.chat_message(role): st.write(text)
            
    if p_input := st.chat_input("针对评分或范文提问..."):
        st.session_state.chat_history.append(("User", p_input))
        with st.chat_message("User"): st.write(p_input)
        with st.chat_message("AI"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"报告内容:{st.session_state.last_report}\n问题:{p_input}")
            st.write(res.text)
            st.session_state.chat_history.append(("AI", res.text))
            st.rerun()
