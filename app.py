import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import re
import os
from datetime import datetime, date
from PIL import Image
from fpdf import FPDF
import random

# --- 1. 配置與樣式 (Cyberpunk Style) ---
st.set_page_config(page_title="DSE AI 狀元工廠", layout="wide", page_icon="🎓")

st.markdown("""
    <style>
    /* 全局深色模式優化 */
    .stApp { background-color: #0e1117; color: #ffffff; }
    
    /* 標題特效 */
    .hero-title {
        background: linear-gradient(90deg, #FF4B4B 0%, #FF914D 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 10px;
    }
    
    /* 卡片樣式 */
    .feature-card {
        background: #1f2937;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #374151;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 20px;
    }
    
    /* 分數展示 */
    .score-badge {
        background-color: #059669;
        color: white;
        padding: 5px 10px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9em;
    }
    
    /* 提醒框 */
    .alert-box {
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 5px solid;
    }
    .alert-trap { background: #451a1a; border-color: #ef4444; }
    .alert-tip { background: #1a3c45; border-color: #06b6d4; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 系統狀態初始化 ---
if "history" not in st.session_state: st.session_state.history = []
if "xp" not in st.session_state: st.session_state.xp = 1250  # 初始經驗值
if "user_level" not in st.session_state: st.session_state.user_level = "Lv.3 備考新星"
if "exam_date" not in st.session_state: st.session_state.exam_date = date(2026, 4, 21) # 假設 DSE 日期

# API Setup
api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
@st.cache_resource
def get_ai():
    return Client(api_key=api_key) if api_key else None
client = get_ai()

# --- 3. 核心功能函數 ---

def level_up_check():
    """簡單的遊戲化系統"""
    st.session_state.xp += 50
    if st.session_state.xp > 2000: st.session_state.user_level = "Lv.5 摘星者"
    elif st.session_state.xp > 1500: st.session_state.user_level = "Lv.4 衝刺學霸"
    st.toast(f"✨ 經驗值 +50! 當前: {st.session_state.user_level}")

def generate_pdf(content, title="DSE Report"):
    """生成 PDF 報告 (含字體處理)"""
    pdf = FPDF()
    pdf.add_page()
    # 嘗試加載中文字體，否則使用默認
    font_path = "fonts/NotoSansTC-Regular.ttf" 
    if os.path.exists(font_path):
        pdf.add_font('NotoSansTC', '', font_path)
        pdf.set_font('NotoSansTC', '', 12)
    else:
        pdf.set_font("Arial", size=12)
        content = "Error: Chinese font not found. Please add 'fonts/NotoSansTC-Regular.ttf'.\n\n" + \
                  "".join([c if ord(c) < 128 else '?' for c in content])
    
    pdf.set_font(style='B', size=16)
    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln(10)
    pdf.set_font(style='', size=12)
    pdf.multi_cell(0, 8, content)
    return pdf.output(dest='S').encode('latin-1')

# --- 4. 側邊欄與導航 ---
with st.sidebar:
    st.markdown("### 👤 考生檔案")
    st.write(f"**等級:** {st.session_state.user_level}")
    st.progress(min(100, (st.session_state.xp % 1000) / 10), text=f"XP: {st.session_state.xp}")
    
    # DSE 倒計時
    days_left = (st.session_state.exam_date - date.today()).days
    st.metric("⏳ 距離 DSE 開考", f"{days_left} 天")
    
    st.markdown("---")
    selected_subject = st.radio("📚 選擇科目", 
        ["🧮 數學 (Mathematics)", 
         "🇬🇧 英文 (English)", 
         "🏮 中文 (Chinese)", 
         "💡 通識/公社 (CSD)"],
        index=0)
    
    st.markdown("---")
    st.info("💡 Tip: 上傳題目照片可獲得更精準解析")
    up_file = st.file_uploader("文件/圖片上傳", type=['png', 'jpg', 'jpeg', 'pdf'])

# --- 5. 主界面邏輯 ---
st.markdown(f'<div class="hero-title">{selected_subject.split("(")[0]} AI 導師</div>', unsafe_allow_html=True)

if not client:
    st.error("⚠️ 請配置 GEMINI_API_KEY")
    st.stop()

# ==========================================
# 🧮 數學科 (Mathematics) - 深度復原與增強
# ==========================================
if "數學" in selected_subject:
    tab1, tab2, tab3, tab4 = st.tabs(["⚡ 智能解題", "🔄 舉一反三 (克隆)", "💣 陷阱預警", "📊 函數繪圖"])
    
    with tab1:
        st.markdown("### Step-by-Step 題目拆解")
        q_math = st.text_area("輸入題目 (或上傳圖片):", placeholder="例如: Solve 2x^2 + 5x - 3 = 0")
        
        if st.button("🚀 開始解題", key="btn_math_solve"):
            with st.spinner("AI 正在運算中..."):
                prompt = "你是一位 DSE 數學科 5** 導師。請對這道題進行：1. 考點識別 (Topic) 2. 詳細步驟 (LaTeX) 3. 最終答案。請用繁體中文。"
                inputs = [prompt]
                if q_math: inputs.append(q_math)
                if up_file: inputs.append(Image.open(up_file))
                
                res = client.models.generate_content(model="gemini-2.0-flash", contents=inputs)
                st.session_state.history.append({"role": "Math Bot", "content": res.text})
                level_up_check()
                st.markdown(res.text)

    with tab2:
        st.markdown("### 🔄 題目克隆工廠 (Weakness Driller)")
        st.caption("AI 根據你的錯題，自動生成 3 條類似題型，讓你刷到會為止。")
        source_q = st.text_area("粘貼你的錯題/原題：", height=100)
        
        if st.button("🎰 生成訓練題組"):
            with st.spinner("正在構造變式題..."):
                prompt = f"基於這道題：'{source_q}'，請模仿 DSE 出題風格，生成 3 道類似的題目（更換數字或場景），並附帶簡略答案。目標是訓練學生的舉一反三能力。"
                res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.success("訓練題組已生成！")
                with st.expander("查看題組", expanded=True):
                    st.write(res.text)

    with tab3:
        st.markdown("### 💣 歷屆試題陷阱庫")
        topic_trap = st.selectbox("選擇課題", ["Quadratic Equations", "Mensuration (幾何)", "Probability", "Logarithm"])
        if st.button("🔍 掃描常見錯誤"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"列出 DSE 數學科 {topic_trap} 課題中，考生最容易犯的 3 個 'Common Mistakes' 或 'Traps'，並給出正確做法。")
            st.markdown(f'<div class="alert-trap">{res.text}</div>', unsafe_allow_html=True)

    with tab4:
        st.markdown("### 📊 圖形計算機")
        c1, c2, c3 = st.columns(3)
        a = c1.number_input("a", value=1.0)
        b = c2.number_input("b", value=0.0)
        c = c3.number_input("c", value=-1.0)
        x = np.linspace(-10, 10, 100)
        y = a*x**2 + b*x + c
        fig = px.line(x=x, y=y, title=f'y = {a}x² + {b}x + {c}')
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 🇬🇧 英文科 (English) - 語言能力特化
# ==========================================
elif "英文" in selected_subject:
    tab1, tab2, tab3 = st.tabs(["✍️ 作文精批", "🚫 Chinglish 掃毒", "🗣️ 口語 Speaking"])
    
    with tab1:
        st.subheader("Writing 5** 批改器")
        txt_eng = st.text_area("輸入你的作文 (Part A/B):", height=200)
        if st.button("📝 批改與評分"):
            with st.spinner("閱卷員正在評分..."):
                prompt = "Act as a DSE English marker. Mark this essay based on Content, Language, and Organization. Give a score /21 and provide a rewritten 5** paragraph for the weakest part."
                res = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, txt_eng])
                level_up_check()
                st.markdown(res.text)
                
                # 下載報告
                pdf_bytes = generate_pdf(res.text, "English Writing Report")
                st.download_button("📥 下載 PDF 報告", pdf_bytes, "writing_report.pdf", "application/pdf")

    with tab2:
        st.subheader("🚫 Chinglish Detector (中式英文修正)")
        bad_sent = st.text_input("輸入你不確定的句子:", "I very like eat apple.")
        if st.button("🚑 診斷"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"Identify if this is Chinglish: '{bad_sent}'. If yes, correct it to natural, native English suitable for DSE writing. Explain the grammar rule.")
            st.info(res.text)

    with tab3:
        st.subheader("Individual Response 模擬")
        topic = st.text_input("輸入口語題目:", "Should homework be abolished?")
        if st.button("🎤 生成論點"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"For DSE Paper 4 Speaking, topic: '{topic}'. Give 2 strong arguments and 1 counter-argument. Include interaction phrases like 'I see your point, but...'.")
            st.markdown(res.text)

# ==========================================
# 🏮 中文科 (Chinese) - 新增模塊
# ==========================================
elif "中文" in selected_subject:
    tab1, tab2, tab3 = st.tabs(["📜 文言文解碼", "🖋️ 寫作昇華", "📚 範文速查"])
    
    with tab1:
        st.markdown("### 文言文翻譯機 (DSE 關鍵字版)")
        wyw = st.text_area("輸入文言句子:", "先帝不以臣卑鄙，猥自枉屈。")
        if st.button("🔍 逐字解釋"):
            prompt = f"針對 DSE 中文科文言文閱讀理解，解釋這句：'{wyw}'。1. 重點實詞解釋 (字詞解釋分)。2. 語譯。3. 句式分析 (如倒裝、通假)。"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.markdown(f'<div class="alert-tip">{res.text}</div>', unsafe_allow_html=True)
            
    with tab2:
        st.markdown("### 作文立意升華器")
        topic_chi = st.text_input("作文題目:", "足印")
        idea = st.text_area("你現在的構思 (簡略):", "寫我小時候和爸爸在沙灘走，看到腳印。")
        if st.button("✨ 升華立意"):
            prompt = f"DSE 中文作文題 '{topic_chi}'。學生構思：'{idea}'。請提供三個不同層次的立意升華建議：1. 文化反思層面 2. 人生成長層面 3. 社會現象層面。並提供可用的名言警句。"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.write(res.text)

    with tab3:
        st.markdown("### 指定篇章速查")
        book = st.selectbox("選擇篇章", ["師說", "始得西山宴遊記", "六國論", "岳陽樓記"])
        if st.button("📖 獲取懶人包"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"總結 DSE 範文《{book}》的：1. 主旨 2. 三個必背金句 3. 歷屆常考問答題方向。")
            st.markdown(res.text)

# ==========================================
# 💡 通識/公社 (CSD)
# ==========================================
else:
    st.markdown("### 🌏 公民與社會發展科助手")
    st.info("AI 協助整理概念與事實查核")
    concept = st.text_input("輸入概念/課題:", "粵港澳大灣區")
    if st.button("📊 生成筆記"):
        res = client.models.generate_content(model="gemini-2.0-flash", contents=f"針對 DSE 公社科，精簡介紹 '{concept}'。包括：1. 定義 2. 對香港機遇 3. 潛在挑戰。")
        st.markdown(res.text)

# --- 6. 全局聊天機器人 (右下角) ---
with st.expander("💬 DSE 隨身軍師 (Chatbot)", expanded=False):
    st.caption("無論你在哪個科目，都可以問我任何問題！")
    user_q = st.text_input("輸入問題...", key="global_chat")
    if user_q:
        res = client.models.generate_content(model="gemini-2.0-flash", contents=f"你是一個幽默且專業的 DSE 導師。回答：{user_q}")
        st.markdown(f"**AI:** {res.text}")
