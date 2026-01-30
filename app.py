import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import re

# 1. 頁面配置
st.set_page_config(page_title="DSE AI 超級導師 Pro", layout="wide")

# 2. 自定義樣式
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    h1 { color: #1e3a8a !important; font-weight: 800; border-bottom: 3px solid #fbbf24; padding-bottom: 10px; }
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 3. 邀請碼驗證 (直接寫死在代碼中，確保本地一定能進去)
with st.sidebar:
    st.title("🔐 成員准入")
    
    # 這裡直接設定你的密碼
    target_code = "DSE2026" 
    
    user_input = st.text_input("請輸入邀請碼解鎖功能", type="password")
    
    if not user_input:
        st.info("請輸入邀請碼以開始。")
        st.stop()
        
    if user_input != target_code:
        st.error("❌ 邀請碼錯誤！請檢查大小寫。")
        st.stop()

    st.success("✅ 驗證成功")
    st.divider()
    st.write("📚 專屬導師已就緒")

# =========================================================
# 4. 主畫面 (只有驗證通過才會顯示)
# =========================================================

st.title("🤖 DSE AI 超級導師 Pro")

# 初始化狀態
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_report" not in st.session_state:
    st.session_state.last_report = ""

# API 客戶端 (API Key 仍建議放 Secrets，若本地測試報錯，請檢查 Secrets 設定)
api_key = st.secrets.get("GEMINI_API_KEY", "YOUR_KEY_HERE")
client = Client(api_key=api_key) if api_key != "YOUR_KEY_HERE" else None

if not client:
    st.error("⚠️ 偵測不到 API Key。請確保 Secrets 中有 GEMINI_API_KEY。")
    st.stop()

tab1, tab2 = st.tabs(["📝 作文深度批改", "✨ 金句實驗室"])

with tab1:
    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.markdown("### 📥 提交作文")
        user_text = st.text_area("在此粘貼你的作文...", height=300)
        if st.button("🚀 生成報告"):
            if user_text:
                with st.spinner("閱卷官批改中..."):
                    prompt = "你是一位DSE閱卷官，請用繁體中文批改並給出等級。最後一行輸出 SCORES: C:5, O:5, L:5"
                    response = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, user_text])
                    st.session_state.last_report = response.text
                    st.session_state.chat_history = [{"role": "assistant", "content": "報告已生成！"}]
        
        if st.session_state.last_report:
            st.markdown(st.session_state.last_report)

    with col2:
        st.markdown("### 💬 導師答疑")
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]): st.write(msg["content"])
        
        if p_in := st.chat_input("詢問導師..."):
            st.session_state.chat_history.append({"role": "user", "content": p_in})
            # 這裡執行 AI 回覆邏輯...
            st.rerun()
