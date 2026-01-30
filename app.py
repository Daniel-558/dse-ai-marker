import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import re

# 1. 頁面配置
st.set_page_config(page_title="DSE AI 超級導師 Pro", layout="wide", initial_sidebar_state="expanded")

# 2. 注入自定義 CSS (增強補習社品牌感)
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    h1 { color: #1e3a8a !important; font-family: 'Helvetica Neue', sans-serif; }
    .report-card { 
        background-color: white; 
        padding: 2rem; 
        border-radius: 15px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-top: 5px solid #fbbf24;
    }
    .stChatFloatingInputContainer { background-color: rgba(255,255,255,0); }
    </style>
    """, unsafe_allow_html=True)

# 3. 初始化 API
api_key_val = st.secrets.get("GEMINI_API_KEY", "")
@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None

client = get_client(api_key_val)

# 4. 狀態管理 (Session State)
if "messages" not in st.session_state:
    st.session_state.messages = [] 
if "scores" not in st.session_state:
    st.session_state.scores = {"Content": 0, "Organization": 0, "Language": 0}
if "full_report" not in st.session_state:
    st.session_state.full_report = ""

# 5. 側邊欄工具箱
with st.sidebar:
    st.title("🛡️ 導師安全接入")
    access_code = st.text_input("輸入邀請碼", type="password")
    if access_code != "DSE2026":
        st.warning("請輸入正確口令")
        st.stop()
    
    st.success("導師已就緒")
    st.divider()
    st.title("📚 DSE 提分資源")
    with st.expander("5** 必背連接詞"):
        st.code("In tandem with...\nParadoxically...\nNotwithstanding...")

# 6. 主頁面佈局
st.title("🤖 DSE AI 超級導師 Pro")
st.caption("全港首個基於 2026 DSE 考官邏輯的寫作訓練平台")

tab1, tab2 = st.tabs(["📝 作文深度批改", "✨ 金句實驗室"])

with tab1:
    col_input, col_display = st.columns([1, 1], gap="large")
    
    with col_input:
        st.markdown("### 📥 提交區")
        task_type = st.selectbox("作文題型", ["Part A (Short)", "Part B (Essay)", "Argumentative", "Letter to Editor"])
        target_lv = st.select_slider("目標等級", options=["3", "4", "5", "5*", "5**"])
        user_text = st.text_area("在此貼上你的文章 (建議 200-500 字)...", height=350)
        
        if st.button("🚀 獲取專家報告"):
            if not user_text:
                st.error("請輸入作文內容")
            else:
                with st.spinner("閱卷官正在掃描您的語法、結構與內容..."):
                    # 強化 Prompt 設計
                    prompt = f"""
                    你是一位資深香港 DSE 英文科閱卷官。請針對這篇 {task_type} 作文進行 Level {target_lv} 標準的評分。
                    請使用繁體中文撰寫一份結構清晰的報告：
                    1. 【綜合評級】：預測等級及一兩句話總結。
                    2. 【COL 診斷】：具體分析內容 (Content)、結構 (Organization)、語言 (Language) 的表現。
                    3. 【5** 大師改寫】：選取原文中最平凡的一段，將其改寫為最高等級水平，並解釋加分點。
                    最後一行必須輸出：SCORES: C:數字, O:數字, L:數字 (滿分7)
                    """
                    response = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, user_text])
                    st.session_state.full_report = response.text
                    
                    # 提取分數
                    score_match = re.search(r"SCORES:\s*C:(\d),\s*O:(\d),\s*L:(\d)", response.text)
                    if score_match:
                        st.session_state.scores = {
                            "Content": int(score_match.group(1)),
                            "Organization": int(score_match.group(2)),
                            "Language": int(score_match.group(3))
                        }
                    
                    # 重置對話並注入當前背景
                    st.session_state.messages = [{"role": "assistant", "content": "報告已生成！我是你的專屬導師，你可以問我關於這份報告的任何細節，或讓我教你如何改善特定句子。"}]

    with col_display:
        st.markdown("### 📊 評分指標")
        if st.session_state.full_report:
            # 繪製雷達圖
            categories = list(st.session_state.scores.keys())
            values = list(st.session_state.scores.values())
            fig = go.Figure(data=go.Scatterpolar(
                r=values + [values[0]], 
                theta=categories + [categories[0]], 
                fill='toself', 
                line_color='#1e3a8a',
                fillcolor='rgba(251, 191, 36, 0.5)'
            ))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), showlegend=False, height=300, margin=dict(t=30, b=30))
            st.plotly_chart(fig, use_container_width=True)
            
            # 顯示報告
            st.markdown('<div class="report-card">', unsafe_allow_html=True)
            st.markdown(st.session_state.full_report.split("SCORES:")[0])
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("完成左側提交後，這裡將顯示分析數據。")

    st.divider()
    
    # 1-on-1 對話區 (放在下方或右側皆可)
    st.markdown("### 💬 1-on-1 導師答疑")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if chat_input := st.chat_input("老師，這段改寫用了什麼語法？"):
        st.session_state.messages.append({"role": "user", "content": chat_input})
        with st.chat_message("user"):
            st.markdown(chat_input)
        
        with st.chat_message("assistant"):
            # 這裡就是關鍵：把上下文餵給 AI
            context = f"學生原文: {user_text}\n批改報告: {st.session_state.full_report}\n學生提問: {chat_input}"
            ai_res = client.models.generate_content(model="gemini-2.0-flash", contents=context)
            st.markdown(ai_res.text)
            st.session_state.messages.append({"role": "assistant", "content": ai_res.text})

with tab2:
    st.markdown("### ✨ Level 5** 金句升級實驗室")
    st.info("輸入一個平淡的句子，讓我們把它變成 5** 考官最愛的「殺手級」句子。")
    sentence_input = st.text_input("輸入句子 (例如: Many people think education is important.)")
    if st.button("瞬間升級") and sentence_input:
        with st.spinner("正在煉金..."):
            lab_prompt = f"請將以下句子改寫為 DSE Level 5** 英文水平，使用高級詞彙和多樣化句式（如 Inversion, Clause），並簡短解釋加分點：{sentence_input}"
            lab_res = client.models.generate_content(model="gemini-2.0-flash", contents=lab_prompt)
            st.success(lab_res.text)
