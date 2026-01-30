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
    .report-card { 
        background-color: white; padding: 20px; border-radius: 12px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 5px solid #fbbf24;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 邀請碼驗證 (本地直通版)
with st.sidebar:
    st.title("🔐 成員准入")
    target_code = "DSE2026"  # 你的預設邀請碼
    user_input = st.text_input("請輸入邀請碼解鎖功能", type="password")
    
    if not user_input:
        st.info("請輸入邀請碼以開始。")
        st.stop()
        
    if user_input != target_code:
        st.error("❌ 邀請碼錯誤！")
        st.stop()

    st.success("✅ 驗證成功")
    st.divider()
    st.title("📚 DSE 工具箱")
    with st.expander("5** 必背連詞"):
        st.markdown("- Paradoxically\n- Notwithstanding\n- In tandem with")

# =========================================================
# 4. 主畫面邏輯 (驗證通過後顯示)
# =========================================================

# 初始化 API 客戶端
# 提醒：請確保你的 .streamlit/secrets.toml 有 GEMINI_API_KEY
api_key = st.secrets.get("GEMINI_API_KEY", "")

@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None

client = get_client(api_key)

if not client:
    st.error("⚠️ 找不到 API Key。請檢查 .streamlit/secrets.toml 檔案。")
    st.stop()

# 初始化狀態變量
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "scores" not in st.session_state:
    st.session_state.scores = {"Content": 0, "Organization": 0, "Language": 0}
if "last_report" not in st.session_state:
    st.session_state.last_report = ""

st.title("🤖 DSE AI 超級導師 Pro")

tab1, tab2 = st.tabs(["📝 作文深度批改", "✨ 金句實驗室"])

# --- Tab 1: 作文批改 ---
with tab1:
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("### 📥 提交作文")
        task_type = st.selectbox("選擇題型", ["Part A", "Part B", "Argumentative", "Letter to Editor"])
        target_lv = st.select_slider("目標等級", options=["3", "4", "5", "5*", "5**"])
        user_text = st.text_area("在此粘貼你的作文...", height=300)
        
        if st.button("🚀 生成深度批改報告"):
            if user_text:
                with st.spinner("閱卷官正在精確打分..."):
                    prompt = f"你是一位精通香港 DSE 評分標準的閱卷官。請對這篇 {task_type} 作文給予 Level {target_lv} 的繁體中文報告。最後一行必須輸出：SCORES: C:數字, O:數字, L:數字 (每項滿分 7)"
                    response = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, user_text])
                    
                    full_text = response.text
                    # 提取分數並更新雷達圖
                    score_match = re.search(r"SCORES:\s*C:(\d),\s*O:(\d),\s*L:(\d)", full_text)
                    if score_match:
                        st.session_state.scores = {
                            "Content": int(score_match.group(1)),
                            "Organization": int(score_match.group(2)),
                            "Language": int(score_match.group(3))
                        }
                    st.session_state.last_report = full_text.split("SCORES:")[0]
                    st.session_state.chat_history = [{"role": "assistant", "content": "報告已生成！你可以查看分析，有不明白的地方在右側問我。"}]
            else:
                st.warning("請先輸入作文內容。")

        if st.session_state.last_report:
            st.markdown("---")
            # 雷達圖
            categories = list(st.session_state.scores.keys())
            values = list(st.session_state.scores.values())
            fig = go.Figure(data=go.Scatterpolar(r=values + [values[0]], theta=categories + [categories[0]], fill='toself', line_color='#1e3a8a'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(f'<div class="report-card">{st.session_state.last_report}</div>', unsafe_allow_html=True)

    with col2:
        st.markdown("### 💬 1-on-1 導師答疑")
        if not st.session_state.last_report:
            st.info("批改完成後，導師會在此為你解答。")
        else:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            if prompt_input := st.chat_input("老師，這段點解咁改？"):
                st.session_state.chat_history.append({"role": "user", "content": prompt_input})
                with st.chat_message("user"): st.write(prompt_input)
                
                with st.chat_message("assistant"):
                    context = f"報告: {st.session_state.last_report}\n提問: {prompt_input}"
                    res = client.models.generate_content(model="gemini-2.0-flash", contents=context)
                    st.write(res.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": res.text})

# --- Tab 2: 金句實驗室 ---
with tab2:
    st.markdown("### ✨ Level 5** 金句升級實驗室")
    st.write("輸入一個普通的句子，讓 AI 幫你升級成 5** 水平的高級表達。")
    
    s_input = st.text_input("輸入你想升級的句子（例如：I think this is good）：")
    
    if st.button("✨ 瞬間升級"):
        if s_input:
            with st.spinner("正在優化語言結構..."):
                lab_prompt = f"請將以下句子改寫為 DSE Level 5** 水平的高級英語，使用更深層的詞彙和複雜句式，並用繁體中文解釋加分點：{s_input}"
                res = client.models.generate_content(model="gemini-2.0-flash", contents=lab_prompt)
                st.success("升級成功！")
                st.markdown(f'<div class="report-card">{res.text}</div>', unsafe_allow_html=True)
        else:
            st.warning("請輸入內容。")
