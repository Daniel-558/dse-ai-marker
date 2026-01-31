import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import os
from datetime import date
from PIL import Image
from fpdf import FPDF

# --- 1. 頁面配置與全新 UI (清新晨曦風格) ---
st.set_page_config(page_title="DSE AI 伴學夥伴", layout="wide", page_icon="🌱")

st.markdown("""
    <style>
    /* 全局背景：柔和的晨曦漸變 */
    .stApp {
        background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);
        color: #333333;
    }
    
    /* 標題特效：充滿活力的漸變色 */
    .hero-title {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.5rem;
        font-weight: 900;
        text-align: center;
        margin-bottom: 20px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    /* 卡片樣式：毛玻璃 + 懸浮感 */
    .feature-card {
        background: rgba(255, 255, 255, 0.9);
        padding: 25px;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.5);
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        margin-bottom: 25px;
        transition: transform 0.2s;
    }
    .feature-card:hover {
        transform: translateY(-5px);
    }
    
    /* 側邊欄優化 */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #f0f0f0;
    }
    
    /* 提示框美化 */
    .stAlert {
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    
    /* 按鈕美化 */
    .stButton>button {
        border-radius: 25px;
        background: linear-gradient(90deg, #a1c4fd 0%, #c2e9fb 100%);
        color: #2c3e50;
        font-weight: bold;
        border: none;
        padding: 10px 25px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        box-shadow: 0 5px 15px rgba(161, 196, 253, 0.4);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 系統狀態初始化 ---
if "history" not in st.session_state: st.session_state.history = []
if "xp" not in st.session_state: st.session_state.xp = 1250
if "user_level" not in st.session_state: st.session_state.user_level = "Lv.3 備考新星"
if "exam_date" not in st.session_state: st.session_state.exam_date = date(2026, 4, 21)

# API Setup
api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
@st.cache_resource
def get_ai():
    return Client(api_key=api_key) if api_key else None
client = get_ai()

# --- 3. 核心功能函數 ---

def level_up_check():
    """遊戲化升級"""
    st.session_state.xp += 50
    if st.session_state.xp > 2000: st.session_state.user_level = "Lv.5 摘星者"
    elif st.session_state.xp > 1500: st.session_state.user_level = "Lv.4 衝刺學霸"
    st.toast(f"🌟 經驗值 +50! 離 5** 更近一步!", icon="🎉")

def generate_pdf(content, title="DSE Report"):
    """生成 PDF"""
    pdf = FPDF()
    pdf.add_page()
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
    st.image("https://cdn-icons-png.flaticon.com/512/3426/3426653.png", width=80)
    st.title("考生檔案")
    st.write(f"🏷️ **{st.session_state.user_level}**")
    
    # 這裡修復了進度條報錯的問題
    st.progress(int((st.session_state.xp % 1000) / 10), text=f"XP: {st.session_state.xp}")
    
    days_left = (st.session_state.exam_date - date.today()).days
    st.caption(f"📅 距離 DSE 還有 {days_left} 天，加油！")
    
    st.markdown("---")
    selected_subject = st.radio("📚 選擇你的戰場", 
        ["🧮 數學 (Maths)", 
         "🇬🇧 英文 (English)", 
         "🏮 中文 (Chinese)", 
         "🌏 公民與社會發展 (CSD)"], # 修正了名稱
        index=0)
    
    st.markdown("---")
    st.markdown("### 📤 智能識別")
    up_file = st.file_uploader("上傳試卷/作文/圖表", type=['png', 'jpg', 'jpeg', 'pdf'])

# --- 5. 主界面邏輯 ---
st.markdown(f'<div class="hero-title">{selected_subject.split("(")[0]} AI 導師</div>', unsafe_allow_html=True)

if not client:
    st.warning("⚠️ 尚未配置 API Key，AI 大腦暫時離線。請在 .streamlit/secrets.toml 中配置。")
    st.stop()

# ==========================================
# 🧮 數學科 (Maths) - 全新繪圖引擎
# ==========================================
if "數學" in selected_subject:
    tab1, tab2, tab3, tab4 = st.tabs(["⚡ 步驟拆解", "🔄 變式訓練", "💣 陷阱掃描", "📊 全能繪圖"])
    
    with tab1:
        st.markdown("<div class='feature-card'><h4>📝 難題秒解</h4><p>不知道怎麼寫步驟？AI 教你拿滿 'M' 分和 'A' 分。</p></div>", unsafe_allow_html=True)
        q_math = st.text_area("輸入題目:", height=100, placeholder="例: Find the coordinates of the vertex of y = 2x^2 - 4x + 1")
        
        if st.button("🚀 生成滿分步驟", key="math_solve"):
            with st.spinner("正在運算最佳路徑..."):
                prompt = "你是一位 DSE 數學科閱卷員。請對這道題進行：1. 考點識別 2. 詳細步驟 (LaTeX) 3. 奪星提示 (如何避免扣分)。請用繁體中文。"
                inputs = [prompt]
                if q_math: inputs.append(q_math)
                if up_file: inputs.append(Image.open(up_file))
                
                res = client.models.generate_content(model="gemini-2.0-flash", contents=inputs)
                st.session_state.history.append({"role": "Math Bot", "content": res.text})
                level_up_check()
                st.markdown(res.text)

    with tab2:
        st.info("💡 錯題是最好的老師。輸入一道錯題，我給你生成三道類似的讓你練手。")
        source_q = st.text_area("輸入錯題:", height=80)
        if st.button("🎰 生成訓練題組"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"基於題目 '{source_q}'，生成 3 道類似的 DSE 數學題目，難度遞增，附帶答案。")
            st.success("✅ 訓練題組已就緒！")
            st.write(res.text)

    with tab3:
        st.markdown("### 💣 課題陷阱預警")
        col1, col2 = st.columns(2)
        with col1:
            topic_trap = st.selectbox("選擇課題", ["Quadratic Equations", "Mensuration (幾何)", "Probability", "Circle Geometry"])
        with col2:
            if st.button("🔍 掃描陷阱"):
                res = client.models.generate_content(model="gemini-2.0-flash", contents=f"DSE 數學科 {topic_trap} 有什麼常犯錯誤 (Common Mistakes)？請列出3點並解釋如何避免。")
                st.error(res.text)

    with tab4:
        st.markdown("### 📊 函數可視化 (全象限)")
        st.caption("輸入係數，查看拋物線在四個象限的分佈與交點。")
        
        c1, c2, c3 = st.columns(3)
        a = c1.number_input("a (x²)", value=1.0, step=0.1)
        b = c2.number_input("b (x)", value=0.0, step=0.1)
        c = c3.number_input("c (const)", value=-4.0, step=0.1)
        
        # 繪圖邏輯優化
        x = np.linspace(-10, 10, 400)
        y = a*x**2 + b*x + c
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=y, mode='lines', name=f'y={a}x²+{b}x+{c}', line=dict(color='#667eea', width=3)))
        
        # 設置十字坐標軸
        fig.update_layout(
            title="Function Plotter",
            xaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='black', showgrid=True, gridcolor='lightgray'),
            yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='black', showgrid=True, gridcolor='lightgray'),
            plot_bgcolor='white',
            hovermode="x unified",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 🇬🇧 英文科 (English)
# ==========================================
elif "英文" in selected_subject:
    tab1, tab2 = st.tabs(["✍️ 作文批改", "🗣️ Speaking 模擬"])
    with tab1:
        st.markdown("<div class='feature-card'><h4>Writing Coach</h4><p>不僅改語法，更教你如何升級句式 (Sentence Variety)。</p></div>", unsafe_allow_html=True)
        txt_eng = st.text_area("Paste your essay here:", height=200)
        if st.button("✨ 深度批改"):
            with st.spinner("Evaluating..."):
                prompt = "Mark this DSE essay. 1. Grade (Level 1-5**). 2. Fix Grammar. 3. Upgrade Vocabulary (give examples). 4. Rewrite one paragraph to 5** standard."
                res = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, txt_eng])
                level_up_check()
                st.markdown(res.text)
                
    with tab2:
        topic = st.text_input("Group Discussion Topic:", "AI in Education")
        if st.button("🎤 生成觀點"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"DSE Paper 4 Speaking Topic: {topic}. Give 2 sound arguments and 1 interaction phrase to agree/disagree.")
            st.info(res.text)

# ==========================================
# 🏮 中文科 (Chinese)
# ==========================================
elif "中文" in selected_subject:
    tab1, tab2 = st.tabs(["📜 文言解碼", "🖋️ 寫作升華"])
    with tab1:
        st.markdown("<div class='feature-card'><h4>文言文翻譯機</h4><p>輸入看不懂的句子，AI 幫你逐字對譯，就像老師在旁邊。</p></div>", unsafe_allow_html=True)
        wyw = st.text_area("輸入古文:", "於是飲酒樂甚，扣舷而歌之。")
        if st.button("🔍 解析"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"解釋DSE文言句：'{wyw}'。1.字詞解釋 2.語譯 3.修辭/句式。")
            st.success(res.text)

    with tab2:
        topic_chi = st.text_input("作文題目:", "重遊舊地有感")
        if st.button("✨ 獲取靈感"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"DSE 作文題 '{topic_chi}'。請提供：1. 立意升華方向 2. 可用的名言警句 3. 開頭第一段示範。")
            st.markdown(res.text)

# ==========================================
# 🌏 公民與社會發展 (CSD) - 修正版
# ==========================================
else:
    st.markdown(f'<div class="hero-title" style="font-size: 2.5rem;">公民與社會發展科</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("<div class='feature-card'><h4>📚 概念庫</h4><p>輸入關鍵詞，快速獲取定義與相關背景。</p></div>", unsafe_allow_html=True)
        concept = st.text_input("輸入關鍵詞 (例: 粵港澳大灣區):")
        if st.button("📖 生成筆記"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"DSE 公社科概念解析：'{concept}'。請包含：1. 定義 2. 對香港/國家的意義 3. 相關例子。")
            st.markdown(res.text)
            
    with col2:
        st.markdown("<div class='feature-card'><h4>⚖️ 多角度思考</h4><p>針對議題，提供正反雙方或持份者觀點。</p></div>", unsafe_allow_html=True)
        issue = st.text_input("輸入議題 (例: 應否推行垃圾徵費):")
        if st.button("🧠 分析議題"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"DSE 公社科議題分析：'{issue}'。請列出不同持份者(Stakeholders)的觀點與理據。")
            st.markdown(res.text)

# --- 6. 底部 AI 助手 ---
st.markdown("---")
with st.expander("💬 隨身導師 (Ask Me Anything)", expanded=True):
    user_q = st.text_input("有些沒看懂？隨時問我：", placeholder="例如：這條數為什麼要這樣做？")
    if user_q:
        res = client.models.generate_content(model="gemini-2.0-flash", contents=f"用繁體中文回答學生問題，語氣親切：{user_q}")
        st.write(res.text)
