import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import re

# 1. 頁面配置 (必須在程式碼最頂端)
st.set_page_config(page_title="DSE AI 超級導師 Pro", layout="wide")

# 2. 獲取 Secrets (API Key 與 邀請碼)
# 在本地測試時，請確保有 .streamlit/secrets.toml 檔案
api_key_val = st.secrets.get("GEMINI_API_KEY", "")
correct_code = st.secrets.get("ACCESS_CODE", "")

# 3. 初始化 API 客户端
@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None

client = get_client(api_key_val)

# 4. 側邊欄驗證邏輯 (這是進入門檻)
with st.sidebar:
    st.title("🔐 成員准入")
    access_code = st.text_input("請輸入邀請碼解鎖功能", type="password")
    
    if not access_code:
        st.info("請輸入邀請碼以開始。")
        st.stop()  # 強制停止，密碼為空時不執行後續代碼
        
    if access_code != correct_code:
        st.error("❌ 邀請碼錯誤，請重新輸入。")
        st.stop()  # 強制停止，密碼錯誤時不執行後續代碼
    
    # 只有通過驗證，才會看到下面的內容
    st.success("✅ 驗證通過")
    st.divider()
    st.title("📚 DSE 工具箱")
    with st.expander("5** 必背連詞"):
        st.markdown("- Paradoxically\n- Notwithstanding\n- In tandem with")

# =========================================================
# 5. 主畫面 (只有密碼正確才會執行到這裡)
# =========================================================

# 初始化狀態變量
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "scores" not in st.session_state:
    st.session_state.scores = {"Content": 0, "Organization": 0, "Language": 0}
if "last_report" not in st.session_state:
    st.session_state.last_report = ""
if "essay_text" not in st.session_state:
    st.session_state.essay_text = ""

st.title("🤖 DSE AI 超級導師 Pro")
st.caption("全港首個基於考官邏輯的 AI 互動批改平台")

tab1, tab2 = st.tabs(["📝 作文深度批改", "✨ 金句實驗室"])

with tab1:
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("### 📥 第一步：提交作文")
        task_type = st.selectbox("選擇題型", ["Part A", "Part B", "Argumentative", "Letter to Editor"])
        target_lv = st.select_slider("目標等級", options=["3", "4", "5", "5*", "5**"])
        user_text = st.text_area("在此粘貼你的作文...", height=300, value=st.session_state.essay_text)
        
        if st.button("🚀 生成深度批改報告"):
            if user_text:
                st.session_state.essay_text = user_text
                with st.spinner("閱卷官正在精確打分..."):
                    prompt = f"你是一位DSE閱卷官，請對這篇 {task_type} 作文給予 Level {target_lv} 目標的同學寫一份繁體中文報告。最後一行必須輸出：SCORES: C:數字, O:數字, L:數字 (滿分7)"
                    response = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, user_text])
                    
                    # 處理分數
                    full_text = response.text
                    score_match = re.search(r"SCORES:\s*C:(\d),\s*O:(\d),\s*L:(\d)", full_text)
                    if score_match:
                        st.session_state.scores = {
                            "Content": int(score_match.group(1)),
                            "Organization": int(score_match.group(2)),
                            "Language": int(score_match.group(3))
                        }
                    st.session_state.last_report = full_text.split("SCORES:")[0]
                    st.session_state.chat_history = [{"role": "assistant", "content": "報告已生成！有問題隨時問我。"}]
            else:
                st.warning("請先輸入內容。")

        if st.session_state.last_report:
            st.markdown("---")
            # 雷達圖
            categories = list(st.session_state.scores.keys())
            values = list(st.session_state.scores.values())
            fig = go.Figure(data=go.Scatterpolar(r=values + [values[0]], theta=categories + [categories[0]], fill='toself', line_color='#1e3a8a'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(st.session_state.last_report)

    with col2:
        st.markdown("### 💬 第二步：1-on-1 導師答疑")
        if not st.session_state.last_report:
            st.info("批改後這裡會開啟對話。")
        else:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
            if p_input := st.chat_input("老師，這段點解咁改？"):
                st.session_state.chat_history.append({"role": "user", "content": p_input})
                with st.chat_message("user"): st.markdown(p_input)
                with st.chat_message("assistant"):
                    context = f"原文: {st.session_state.essay_text}\n報告: {st.session_state.last_report}\n問: {p_input}"
                    res = client.models.generate_content(model="gemini-2.0-flash", contents=context)
                    st.markdown(res.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": res.text})

with tab2:
    st.markdown("### ✨ Level 5** 金句升級實驗室")
    s_in = st.text_input("輸入句子：")
    if st.button("✨ 升級") and s_in:
        res = client.models.generate_content(model="gemini-2.0-flash", contents=f"將此句升級為DSE Level 5**水平：{s_in}")
        st.success(res.text)
