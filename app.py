import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import re
import numpy as np
from datetime import datetime
from PIL import Image
from fpdf import FPDF
import io

# --- 1. 頁面配置與全局樣式 ---
st.set_page_config(page_title="DSE AI 超級工作站", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #f8fafc; }
    .main-header { padding: 1.5rem; border-radius: 12px; color: white; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    .eng-theme { background: linear-gradient(135deg, #1e293b 0%, #334155 100%); }
    .math-theme { background: linear-gradient(135deg, #064e3b 0%, #059669 100%); }
    .report-card { background: white; padding: 25px; border-radius: 15px; border-left: 6px solid #3b82f6; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-top: 15px; white-space: pre-wrap; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 8px 8px 0 0; padding: 12px 20px; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #3b82f6 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 狀態管理 (確保切換學科不丟失數據) ---
if "eng_data" not in st.session_state:
    st.session_state.eng_data = {"report": "", "scores": {"C": 0, "O": 0, "L": 0}}
if "math_data" not in st.session_state:
    st.session_state.math_data = {"solution": ""}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# API 初始化
api_key_val = st.secrets.get("GEMINI_API_KEY", "")
@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None
client = get_client(api_key_val)

# PDF 導出輔助函數
def generate_pdf_report(report_text, scores):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "DSE English Writing Diagnosis", ln=True, align='C')
    pdf.ln(5)
    pdf.cell(0, 10, f"Scores -> C:{scores['C']} O:{scores['O']} L:{scores['L']}", ln=True)
    safe_text = "".join([i if ord(i) < 128 else ' ' for i in report_text])
    pdf.multi_cell(0, 8, safe_text[:2000])
    return pdf.output()

# --- 3. 側邊欄 ---
with st.sidebar:
    st.title("🛡️ DSE Portal")
    if st.text_input("解鎖碼", type="password") != "DSE2026":
        st.stop()
    
    st.markdown("---")
    subject = st.selectbox("📚 選擇備考科目", ["🇬🇧 English Language", "🔢 Mathematics"])
    
    st.markdown("---")
    st.subheader("📂 檔案上傳 (作文照片/數學題)")
    up_file = st.file_uploader("支援 JPG/PNG/PDF", type=['png', 'jpg', 'jpeg', 'pdf'])
    
    if st.button("🗑️ 徹底清空記錄"):
        for key in ["eng_data", "math_data", "chat_history"]:
            if key in st.session_state: del st.session_state[key]
        st.rerun()

# --- 4. 主界面佈局 ---
theme = "eng-theme" if "English" in subject else "math-theme"
st.markdown(f'<div class="main-header {theme}"><h1>{subject} AI 超級導師 Pro</h1><p>全科一站式備考系統</p></div>', unsafe_allow_html=True)

main_col, chat_col = st.columns([1.3, 0.7], gap="large")

# ==========================================
# 🏠 英文科模塊 (English Language)
# ==========================================
if "English" in subject:
    with main_col:
        tabs = st.tabs(["📖 P1 Reading", "✍️ P2 Writing", "🎧 P3 Integrated", "🗣️ P4 Speaking"])
        
        with tabs[0]:
            st.markdown("### 🔍 Reading 邏輯拆解")
            p1_in = st.text_area("輸入難句：", height=100, key="e_p1")
            if st.button("AI 拆解思路", key="e_p1_btn"):
                res = client.models.generate_content(model="gemini-2.0-flash", contents=f"解析DSE閱讀：1.翻譯 2.句法 3.考點。原文：{p1_in}")
                st.info(res.text)

        with tabs[1]:
            st.markdown("### ✍️ Writing 深度批改")
            p2_part = st.radio("選擇部分", ["Part A", "Part B"], horizontal=True)
            user_p2 = st.text_area("在此粘貼作文...", height=250, key="e_p2_in")
            if st.button("🚀 啟動批改"):
                with st.spinner("閱卷主席評分中..."):
                    prompt = f"你是一位DSE閱卷主席。批改這篇 {p2_part} 作文。提供等級評估、C/O/L細項分、200字5**範文。最後一行輸出: SCORES: C:數字, O:數字, L:數字。"
                    inputs = [prompt, user_p2]
                    if up_file: inputs.append(Image.open(up_file))
                    resp = client.models.generate_content(model="gemini-2.0-flash", contents=inputs)
                    st.session_state.eng_data["report"] = resp.text
                    m = re.search(r"SCORES: C:(\d), O:(\d), L:(\d)", resp.text)
                    if m: st.session_state.eng_data["scores"] = {"C": int(m.group(1)), "O": int(m.group(2)), "L": int(m.group(3))}
            
            if st.session_state.eng_data["report"]:
                st.markdown("---")
                sc = st.session_state.eng_data["scores"]
                c1, c2 = st.columns([1, 1])
                with c1:
                    st.subheader(f"得分: {sum(sc.values())}/21")
                    fig = go.Figure(data=go.Scatterpolar(r=[sc['C'], sc['O'], sc['L'], sc['C']], theta=['Content','Org','Lang','Content'], fill='toself'))
                    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), height=280, margin=dict(t=30, b=30))
                    st.plotly_chart(fig, use_container_width=True)
                with c2:
                    pdf_b = generate_pdf_report(st.session_state.eng_data["report"], sc)
                    st.download_button("📥 下載診斷報告", data=pdf_b, file_name="DSE_English_Report.pdf")
                st.markdown(f'<div class="report-card">{st.session_state.eng_data["report"]}</div>', unsafe_allow_html=True)

        with tabs[2]:
            st.markdown("### 🎧 P3 Integrated 格式庫")
            p3_t = st.selectbox("任務文體", ["Formal Letter", "Report", "Proposal", "Article"])
            if st.button("生成 5** 格式模板"):
                res = client.models.generate_content(model="gemini-2.0-flash", contents=f"給出DSE P3 {p3_t} 的5**格式及常用句式。")
                st.success(res.text)

        with tabs[3]:
            st.markdown("### 🗣️ Speaking 靈感庫")
            s_topic = st.text_input("輸入題目：")
            if st.button("腦暴 5** 論點"):
                res = client.models.generate_content(model="gemini-2.0-flash", contents=f"針對題 '{s_topic}' 提供3個深度論點及轉折句。")
                st.info(res.text)

# ==========================================
# 📐 數學科模塊 (Mathematics)
# ==========================================
else:
    with main_col:
        tabs = st.tabs(["📝 Paper 1 解答", "🎯 Paper 2 MC 技巧", "📊 函數繪圖", "📚 必背公式"])
        
        with tabs[0]:
            st.markdown("### 📝 Step-by-Step 題目拆解")
            m_q = st.text_area("輸入題目或上傳照片：", height=150, key="m_p1")
            if st.button("🚀 生成詳細解題步驟"):
                with st.spinner("AI 正在推算..."):
                    prompt = "你是一位DSE數學名師。請分步解答此題，包含考點分析、詳細步驟(使用LaTeX)及奪星亮點。使用繁體中文。"
                    inputs = [prompt, m_q]
                    if up_file: inputs.append(Image.open(up_file))
                    res = client.models.generate_content(model="gemini-2.0-flash", contents=inputs)
                    st.session_state.math_data["solution"] = res.text
            if st.session_state.math_data["solution"]:
                st.markdown(f'<div class="report-card">{st.session_state.math_data["solution"]}</div>', unsafe_allow_html=True)

        with tabs[1]:
            st.markdown("### 🎯 MC 秒殺技巧庫")
            mc_cat = st.selectbox("技巧類型", ["代入法 (Substitution)", "估算法 (Estimation)", "計數機程序 (Calculator)"])
            if st.button("獲取秒殺範例"):
                res = client.models.generate_content(model="gemini-2.0-flash", contents=f"解釋DSE數學MC中 '{mc_cat}' 的應用及經典題型。")
                st.success(res.text)

        with tabs[2]:
            st.markdown("### 📊 二次函數繪圖器")
            ca, cb, cc = st.columns(3)
            a = ca.number_input("a (二次項)", value=1.0)
            b = cb.number_input("b (一次項)", value=0.0)
            c = cc.number_input("c (常數項)", value=0.0)
            x_vals = np.linspace(-10, 10, 400)
            y_vals = a*x_vals**2 + b*x_vals + c
            fig = go.Figure(data=go.Scatter(x=x_vals, y=y_vals, name="f(x)"))
            fig.update_layout(title=f"y = {a}x² + {b}x + {c}", height=350)
            st.plotly_chart(fig, use_container_width=True)
            st.latex(rf"y = {a}x^2 + {b}x + {c}")

        with tabs[3]:
            st.subheader("📚 核心公式卡")
            st.latex(r"\text{Quadratic Formula: } x = \frac{-b \pm \sqrt{b^2-4ac}}{2a}")
            st.latex(r"\text{Cosine Law: } c^2 = a^2 + b^2 - 2ab\cos C")

# ==========================================
# 💬 右側：全卷通用導師答疑
# ==========================================
with chat_col:
    st.markdown(f"### 💬 {subject} 導師在線")
    st.caption("您可以隨時追問上述內容。")
    chat_box = st.container(height=550, border=True)
    with chat_box:
        for r, t in st.session_state.chat_history:
            with st.chat_message(r): st.write(t)
            
    if q := st.chat_input("輸入您的問題..."):
        st.session_state.chat_history.append(("user", q))
        with st.chat_message("user"): st.write(q)
        
        # 根據科目獲取上下文
        ctx = st.session_state.eng_data["report"] if "English" in subject else st.session_state.math_data["solution"]
        prompt = f"你是DSE {subject}專家。參考內容：{ctx}\n\n學生問題：{q}"
        
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        st.session_state.chat_history.append(("assistant", response.text))
        st.rerun()
