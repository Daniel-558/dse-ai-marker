import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import re

# ==========================================
# 1. 頁面配置與專業 UI 樣式
# ==========================================
st.set_page_config(page_title="DSE AI 超級導師 Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    h1 { color: #1e3a8a !important; font-weight: 800; border-bottom: 3px solid #fbbf24; padding-bottom: 10px; }
    .stButton>button { 
        background-color: #1e3a8a; color: white; border-radius: 8px; 
        font-weight: bold; width: 100%; transition: 0.3s;
    }
    .stButton>button:hover { background-color: #fbbf24; color: #1e3a8a; }
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    .report-card { 
        background-color: white; padding: 20px; border-radius: 12px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 5px solid #fbbf24;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 初始化 API 客户端
# ==========================================
# 請確保在 Streamlit 的 Secrets 中設定了 GEMINI_API_KEY
api_key_val = st.secrets.get("GEMINI_API_KEY", "")

@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None

client = get_client(api_key_val)

# ==========================================
# 3. 初始化狀態變量 (防止刷新丟失數據)
# ==========================================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # 存儲對話紀錄
if "scores" not in st.session_state:
    st.session_state.scores = {"Content": 0, "Organization": 0, "Language": 0}
if "last_report" not in st.session_state:
    st.session_state.last_report = ""
if "essay_text" not in st.session_state:
    st.session_state.essay_text = ""

# ==========================================
# 4. 側邊欄：密碼驗證與工具箱
# ==========================================
with st.sidebar:
    st.title("🔐 導師接入面板")
    # 你的登入密碼就在這裡設定
    access_code = st.text_input("請輸入邀請碼解鎖", type="password")
    
    if access_code != "DSE2026":
        st.warning("🔒 請輸入正確邀請碼以使用 AI 功能。")
        st.info("💡 提示：邀請碼為 DSE2026")
        st.stop()
    
    st.success("✅ 驗證成功！")
    st.divider()
    st.title("📚 DSE 提分工具")
    with st.expander("5** 必背連詞"):
        st.markdown("- **Paradoxically** (矛盾地)\n- **Notwithstanding** (儘管)\n- **In tandem with** (與...同時)")
    with st.expander("詞彙升級表"):
        st.table({"普通": ["Think", "Help", "Big"], "5**級別": ["Advocate", "Facilitate", "Substantial"]})

# ==========================================
# 5. 主界面佈局
# ==========================================
st.title("🤖 DSE AI 超級導師 Pro")
st.caption("基於考官邏輯的 1-on-1 深度批改與互動平台")

tab_marker, tab_lab = st.tabs(["📝 作文深度批改", "✨ 金句實驗室"])

# --- Tab 1: 作文批改 ---
with tab_marker:
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("### 📥 第一步：提交作文")
        task_type = st.selectbox("選擇題型", ["Part A", "Part B", "Argumentative", "Letter to Editor"])
        target_lv = st.select_slider("目標等級", options=["3", "4", "5", "5*", "5**"])
        user_text = st.text_area("在此粘貼你的作文...", height=300, value=st.session_state.essay_text)
        
        if st.button("🚀 生成考官級批改報告"):
            if user_text:
                st.session_state.essay_text = user_text # 保存文章內容
                with st.spinner("閱卷官正在精確打分並撰寫報告..."):
                    prompt = f"""
                    你是一位精通香港 DSE 評分標準的英文科閱卷官。
                    請對這篇 {task_type} 作文給予 Level {target_lv} 目標的同學寫一份詳盡報告。
                    要求：
                    1. 指出 Content, Organization, Language 三方面的具體加分點與扣分點。
                    2. 提供一段 Level 5** 水平的範文改寫。
                    3. 最後一行必須嚴格按照此格式輸出分數：SCORES: C:數字, O:數字, L:數字 (每項滿分 7 分)
                    請使用繁體中文。
                    """
                    response = client.models.generate_content(
                        model="gemini-2.0-flash", 
                        contents=[prompt, user_text]
                    )
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
                    # 重置對話框並讓 AI 導師主動引導
                    st.session_state.chat_history = [
                        {"role": "assistant", "content": "我是你的專屬導師。報告已生成，你可以查看左側的雷達圖了解弱項，不明白的地方在右側隨時問我！"}
                    ]
            else:
                st.warning("請先輸入作文內容。")

        # 顯示報告結果
        if st.session_state.last_report:
            st.markdown("---")
            st.markdown("### 📊 評分分析")
            categories = list(st.session_state.scores.keys())
            values = list(st.session_state.scores.values())
            fig = go.Figure(data=go.Scatterpolar(r=values + [values[0]], theta=categories + [categories[0]], fill='toself', line_color='#1e3a8a'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("### 📋 批改報告內容")
            st.markdown(f'<div class="report-card">{st.session_state.last_report}</div>', unsafe_allow_html=True)

    with col2:
        st.markdown("### 💬 第二步：導師 1-on-1 追問")
        if not st.session_state.last_report:
            st.info("完成左側批改後，導師將在此為你解答疑問。")
        else:
            # 渲染對話紀錄
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
            
            # 使用 chat_input 組件
            if prompt_input := st.chat_input("老師，為什麼這裡建議這樣改？"):
                st.session_state.chat_history.append({"role": "user", "content": prompt_input})
                with st.chat_message("user"):
                    st.write(prompt_input)
                
                with st.chat_message("assistant"):
                    with st.spinner("導師思考中..."):
                        # 將上下文（原文+報告+提問）完整發送
                        context = f"""
                        學生原文: {st.session_state.essay_text}
                        你的批改報告: {st.session_state.last_report}
                        學生現在問你: {prompt_input}
                        請作為專業導師給予回答。
                        """
                        response = client.models.generate_content(model="gemini-2.0-flash", contents=context)
                        st.write(response.text)
                        st.session_state.chat_history.append({"role": "assistant", "content": response.text})

# --- Tab 2: 金句實驗室 ---
with tab_lab:
    st.markdown("### ✨ Level 5** 金句升級實驗室")
    st.info("輸入一個平凡的句子，讓 AI 將其轉化為 DSE 高分句式。")
    s_input = st.text_input("輸入你想升級的句子：", placeholder="Education is very important for our future.")
    if st.button("✨ 瞬間升級"):
        if s_input:
            with st.spinner("正在煉金..."):
                lab_prompt = f"將此句子升級為香港 DSE Level 5** 水平，並用繁體中文解釋使用了什麼高級句式或詞彙：{s_input}"
                res = client.models.generate_content(model="gemini-2.0-flash", contents=lab_prompt)
                st.success(res.text)
        else:
            st.warning("請先輸入句子。")
