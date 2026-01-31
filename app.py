import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import numpy as np
import sympy as sp
import os
from datetime import date
from PIL import Image
from fpdf import FPDF

# --- 1. 頁面配置 ---
st.set_page_config(page_title="DSE AI 伴學夥伴", layout="wide", page_icon="📐")

st.markdown("""
    <style>
    /* 清新晨曦漸變背景 */
    .stApp {
        background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);
        color: #333333;
    }
    .hero-title {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 900;
        text-align: center;
        margin-bottom: 20px;
    }
    .feature-card {
        background: rgba(255, 255, 255, 0.95);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid rgba(0,0,0,0.05);
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    /* 數學符號按鈕樣式 */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        background-color: white;
        font-weight: bold;
        color: #444;
    }
    .stButton>button:hover {
        background-color: #f0fdf4;
        color: #059669;
        border-color: #059669;
    }
    /* 隱藏 Plotly Modebar 中不必要的按鈕，讓界面更像 Desmos */
    .modebar-btn { color: #888 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 狀態管理 ---
if "xp" not in st.session_state: st.session_state.xp = 1250
if "user_level" not in st.session_state: st.session_state.user_level = "Lv.3 備考新星"
if "exam_date" not in st.session_state: st.session_state.exam_date = date(2026, 4, 21)
if "math_eq" not in st.session_state: st.session_state.math_eq = "x * sin(x)" # 默認函數

# API Setup
api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
@st.cache_resource
def get_ai():
    return Client(api_key=api_key) if api_key else None
client = get_ai()

# --- 3. 輔助函數 ---
def level_up_check():
    st.session_state.xp += 50
    st.toast(f"🌟 經驗值 +50!", icon="🎉")

def add_symbol(sym):
    """將符號追加到當前方程"""
    st.session_state.math_eq += sym

def parse_equation(eq_str):
    """使用 SymPy 解析用戶輸入的字符串為數學函數"""
    try:
        x = sp.symbols('x')
        # 預處理：將 ^ 替換為 ** (Python 語法)
        eq_str = eq_str.replace('^', '**')
        # 解析表達式
        expr = sp.sympify(eq_str)
        # 轉換為 numpy 可計算的函數
        f = sp.lambdify(x, expr, 'numpy')
        return f, str(expr).replace('**', '^')
    except Exception as e:
        return None, str(e)

# --- 4. 側邊欄 ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2936/2936735.png", width=70)
    st.title("DSE 狀元中樞")
    
    st.progress(int((st.session_state.xp % 1000) / 10), text=f"XP: {st.session_state.xp}")
    days_left = (st.session_state.exam_date - date.today()).days
    st.caption(f"📅 距離開考: {days_left} 天")
    
    st.markdown("---")
    selected_subject = st.radio("📚 選擇科目", ["🧮 數學 (Maths)", "🇬🇧 英文 (English)", "🏮 中文 (Chinese)", "🌏 公社科 (CSD)"])
    st.markdown("---")
    up_file = st.file_uploader("📷 上傳題目/試卷", type=['png', 'jpg', 'jpeg'])

# --- 5. 主界面 ---
st.markdown(f'<div class="hero-title">{selected_subject.split("(")[0]} AI 導師</div>', unsafe_allow_html=True)

if not client:
    st.warning("⚠️ 請配置 API Key")
    st.stop()

# ==========================================
# 🧮 數學科 (Maths) - Desmos 風格繪圖器
# ==========================================
if "數學" in selected_subject:
    tab1, tab2, tab3 = st.tabs(["📊 函數繪圖 (Grapher)", "⚡ 步驟拆解", "💣 陷阱掃描"])
    
    with tab1:
        col_main, col_tools = st.columns([3, 1])
        
        with col_tools:
            st.markdown("### 🧮 符號鍵盤")
            # 符號按鈕網格
            k1, k2, k3 = st.columns(3)
            if k1.button("x²"): add_symbol("**2")
            if k2.button("√"): add_symbol("sqrt(")
            if k3.button("π"): add_symbol("pi")
            
            k4, k5, k6 = st.columns(3)
            if k4.button("sin"): add_symbol("sin(")
            if k5.button("cos"): add_symbol("cos(")
            if k6.button("tan"): add_symbol("tan(")
            
            k7, k8, k9 = st.columns(3)
            if k7.button("("): add_symbol("(")
            if k8.button(")"): add_symbol(")")
            if k9.button("÷"): add_symbol("/")
            
            st.info("💡 提示：乘號請用 * (例如 2*x)")
            if st.button("❌ 清空輸入"): st.session_state.math_eq = ""

        with col_main:
            st.markdown("### y = ...")
            # 綁定 session_state 實現按鈕輸入
            eq_input = st.text_input("輸入方程 (支持 x, sin, cos, exp等):", key="math_eq")
            
            # 解析並繪圖
            func, display_eq = parse_equation(eq_input)
            
            if func:
                # 生成數據點
                x_vals = np.linspace(-10, 10, 800)
                try:
                    y_vals = func(x_vals)
                    # 處理無窮大或複數情況
                    if isinstance(y_vals, (int, float)): y_vals = np.full_like(x_vals, y_vals) # 常數函數
                    
                    fig = go.Figure()
                    
                    # 添加主曲線
                    fig.add_trace(go.Scatter(
                        x=x_vals, y=y_vals,
                        mode='lines',
                        name=f'y={display_eq}',
                        line=dict(color='#6b46c1', width=3)
                    ))

                    # 配置 Desmos 風格坐標系
                    fig.update_layout(
                        title=dict(text=f"Function: y = {display_eq}", x=0.5),
                        xaxis=dict(
                            zeroline=True, zerolinewidth=2, zerolinecolor='black',
                            showgrid=True, gridcolor='rgba(0,0,0,0.1)',
                            range=[-10, 10], # 初始範圍
                            constrain='domain'
                        ),
                        yaxis=dict(
                            zeroline=True, zerolinewidth=2, zerolinecolor='black',
                            showgrid=True, gridcolor='rgba(0,0,0,0.1)',
                            range=[-6, 6],
                            scaleanchor="x", scaleratio=1 # 鎖定比例，確保圓形看起來是圓的
                        ),
                        plot_bgcolor='white',
                        dragmode='pan', # 默認拖拽平移
                        hovermode='x unified',
                        height=550,
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    
                    # 啟用滾輪縮放
                    config = {
                        'scrollZoom': True, 
                        'displayModeBar': True,
                        'displaylogo': False,
                        'modeBarButtonsToRemove': ['lasso2d', 'select2d']
                    }
                    
                    st.plotly_chart(fig, use_container_width=True, config=config)
                    
                except Exception as err:
                    st.error(f"無法計算函數值: {err}")
            else:
                st.error(f"公式解析錯誤: {display_eq} (請確保使用 x 作為變量，乘法用 *)")

    with tab2:
        st.markdown("<div class='feature-card'><h4>📝 智能解題</h4></div>", unsafe_allow_html=True)
        q_math = st.text_area("輸入數學題目:", height=100)
        if st.button("🚀 生成步驟"):
            with st.spinner("AI 運算中..."):
                prompt = "你是一位DSE數學名師。請分步解答此題，使用LaTeX，重點標註分數占比(M分/A分)。"
                inputs = [prompt]
                if q_math: inputs.append(q_math)
                if up_file: inputs.append(Image.open(up_file))
                res = client.models.generate_content(model="gemini-2.0-flash", contents=inputs)
                st.markdown(res.text)
                level_up_check()

    with tab3:
        st.markdown("<div class='feature-card'><h4>💣 陷阱掃描器</h4></div>", unsafe_allow_html=True)
        topic = st.selectbox("選擇課題", ["Quadratic Equations", "Trigonometry", "Coordinate Geometry"])
        if st.button("掃描常犯錯誤"):
            res = client.models.generate_content(model="gemini-2.0-flash", contents=f"DSE Maths Topic: {topic}. List 3 common traps/mistakes students make.")
            st.warning(res.text)

# ==========================================
# 🇬🇧 英文科 (English)
# ==========================================
elif "英文" in selected_subject:
    st.subheader("Writing Expert")
    txt_eng = st.text_area("Input Essay:", height=200)
    if st.button("✨ Grade & Correct"):
        res = client.models.generate_content(model="gemini-2.0-flash", contents=["Grade this DSE essay /21 and fix grammar.", txt_eng])
        st.markdown(res.text)

# ==========================================
# 🏮 中文科 (Chinese)
# ==========================================
elif "中文" in selected_subject:
    st.subheader("文言文翻譯機")
    wyw = st.text_area("輸入古文句子:")
    if st.button("🔍 翻譯"):
        res = client.models.generate_content(model="gemini-2.0-flash", contents=f"解釋DSE文言句: {wyw}")
        st.success(res.text)

# ==========================================
# 🌏 公社科 (CSD)
# ==========================================
else:
    st.subheader("概念查詢")
    kw = st.text_input("輸入關鍵詞:")
    if st.button("📖 查詢"):
        res = client.models.generate_content(model="gemini-2.0-flash", contents=f"DSE CSD Concept: {kw}")
        st.info(res.text)

# --- Chatbot ---
with st.expander("💬 AI 助手"):
    q = st.text_input("Ask anything:")
    if q: st.write(client.models.generate_content(model="gemini-2.0-flash", contents=q).text)
