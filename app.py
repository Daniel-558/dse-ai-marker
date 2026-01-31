import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import re

# 1. 页面配置
st.set_page_config(page_title="DSE AI 超级导师 Pro", layout="wide")

# 2. 核心 CSS 框架（定义专业 UI 样式）
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    h1 { color: #1e3a8a !important; font-weight: 800; text-align: center; }
    
    /* 分数表卡片样式 */
    .score-card {
        background-color: white;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        height: 100%;
    }
    
    /* 报告卡片样式 */
    .report-container {
        background: white;
        padding: 25px;
        border-radius: 15px;
        border-left: 6px solid #fbbf24;
        margin-top: 25px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    
    /* 按钮美化 */
    .stButton>button {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white; border-radius: 10px; font-weight: bold; height: 3.5em; width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 初始化 API 客户端
api_key_val = st.secrets.get("GEMINI_API_KEY", "")
@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None
client = get_client(api_key_val)

# 4. 初始化 Session State
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "scores" not in st.session_state: st.session_state.scores = {"Content": 0, "Organization": 0, "Language": 0}
if "last_report" not in st.session_state: st.session_state.last_report = ""

# 5. 侧边栏：入场门槛与导航
with st.sidebar:
    st.title("🔐 成员准入")
    access_code = st.text_input("请输入邀请码解锁", type="password")
    if access_code != "DSE2026":
        st.warning("请输入正确邀请码以使用导师功能。")
        st.stop()
    st.success("验证成功")
    st.markdown("---")
    st.title("📚 DSE 提分工具")
    st.info("💡 批改后如有疑问，可在右侧答疑区追问导师。")

# 6. 主界面布局
st.title("🤖 DSE AI 超级导师 Pro")

col1, col2 = st.columns([1.2, 0.8], gap="large")

with col1:
    st.markdown("### 📥 提交作文片段")
    task_type = st.selectbox("选择题型", ["Part A", "Part B", "Argumentative", "Letter to Editor", "Report"])
    target_lv = st.select_slider("目标等级", options=["3", "4", "5", "5*", "5**"])
    user_text = st.text_area("在此粘贴作文内容...", height=250)
    
    if st.button("🚀 生成可视化评估报告"):
        if user_text:
            with st.spinner("DSE 考官正在深度评阅..."):
                prompt = f"""
                你是一位精通DSE评分标准的考官。请分析这篇{task_type}作文。
                最后一行必须严格输出: SCORES: C:数字, O:数字, L:数字 (每项满分7分)
                请使用繁体中文，提供评分、改进建议、Level 5** 示范。
                """
                response = client.models.generate_content(model="gemini-3-flash-preview", contents=[prompt, user_text])
                full_text = response.text
                
                # 提取分数
                score_match = re.search(r"SCORES: C:(\d), O:(\d), L:(\d)", full_text)
                if score_match:
                    st.session_state.scores = {
                        "Content": int(score_match.group(1)),
                        "Organization": int(score_match.group(2)),
                        "Language": int(score_match.group(3))
                    }
                st.session_state.last_report = full_text.split("SCORES:")[0]
        else:
            st.warning("请先输入作文内容")

    # --- 核心更新：左分数表 + 右雷达图 框架 ---
    if st.session_state.last_report:
        st.markdown("---")
        st.markdown("### 📊 评估仪表盘 (Assessment Dashboard)")
        
        # 创建左右并排布局
        d1, d2 = st.columns([1, 1.2]) 
        
        with d1:
            # 左侧：专业分数表
            total = sum(st.session_state.scores.values())
            st.markdown(f"""
            <div class="score-card">
                <div style="text-align:center; margin-bottom:15px;">
                    <p style="margin:0; font-size:0.9em; color:#666;">总分预估 (Total)</p>
                    <h2 style="margin:0; color:#1e3a8a;">{total} <span style="font-size:0.5em; color:#999;">/ 21</span></h2>
                </div>
                <hr style="border:0; border-top:1px solid #eee; margin:10px 0;">
                <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                    <span style="color:#4a5568;">Content (内容)</span>
                    <b style="color:#1e3a8a;">{st.session_state.scores['Content']}/7</b>
                </div>
                <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                    <span style="color:#4a5568;">Organization (结构)</span>
                    <b style="color:#1e3a8a;">{st.session_state.scores['Organization']}/7</b>
                </div>
                <div style="display:flex; justify-content:space-between;">
                    <span style="color:#4a5568;">Language (语言)</span>
                    <b style="color:#1e3a8a;">{st.session_state.scores['Language']}/7</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with d2:
            # 右侧：雷达图
            categories = list(st.session_state.scores.keys())
            values = list(st.session_state.scores.values())
            fig = go.Figure(data=go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill='toself',
                line_color='#fbbf24',
                fillcolor='rgba(251, 191, 36, 0.3)'
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 7])),
                showlegend=False,
                height=280,
                margin=dict(t=20, b=20, l=40, r=40)
            )
            st.plotly_chart(fig, use_container_width=True)

        # 详细报告卡片
        st.markdown(f"""
        <div class="report-container">
            {st.session_state.last_report}
        </div>
        """, unsafe_allow_html=True)

with col2:
    st.markdown("### 💬 1-on-1 导师答疑")
    chat_container = st.container(height=550)
    with chat_container:
        if not st.session_state.last_report:
            st.info("生成报告后即可开启追问模式。")
        for role, text in st.session_state.chat_history:
            with st.chat_message(role):
                st.write(text)
            
    if prompt_input := st.chat_input("问导师：为什么这里得分不高？"):
        st.session_state.chat_history.append(("User", prompt_input))
        with st.chat_message("User"):
            st.write(prompt_input)
        
        with st.chat_message("AI"):
            context = f"原文: {user_text}\n报告: {st.session_state.last_report}\n追问: {prompt_input}"
            ans = client.models.generate_content(model="gemini-3-flash-preview", contents=context)
            st.write(ans.text)
            st.session_state.chat_history.append(("AI", ans.text))
            st.rerun()
