import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import re

# 1. 页面配置
st.set_page_config(page_title="DSE AI 超级导师 Pro", layout="wide")

# 2. CSS 框架增强（加入分数表样式）
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    h1 { color: #1e3a8a !important; font-weight: 800; text-align: center; }
    
    /* 分数表卡片样式 */
    .score-table {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .score-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #edf2f7;
    }
    .score-label { font-weight: 600; color: #4a5568; }
    .score-value { color: #1e3a8a; font-weight: 700; }
    
    /* 报告卡片 */
    .report-card {
        background-color: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border-left: 5px solid #fbbf24;
        margin-top: 20px;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white; border-radius: 10px; font-weight: bold; height: 3em;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 初始化 API
api_key_val = st.secrets.get("GEMINI_API_KEY", "")
@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None
client = get_client(api_key_val)

if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "scores" not in st.session_state: st.session_state.scores = {"Content": 0, "Organization": 0, "Language": 0}
if "last_report" not in st.session_state: st.session_state.last_report = ""

# 4. 侧边栏
with st.sidebar:
    st.title("🔐 成员准入")
    access_code = st.text_input("请输入邀请码", type="password")
    if access_code != "DSE2026":
        st.warning("验证口令")
        st.stop()
    st.success("验证通过")
    st.markdown("---")
    st.title("📚 写作金句库")
    st.info("💡 句子升级后可直接复制使用")

# 5. 主界面
st.title("🤖 DSE AI 超级导师 Pro")

col1, col2 = st.columns([1.2, 0.8], gap="large")

with col1:
    st.markdown("### 📥 提交作文")
    t_type = st.selectbox("题型", ["Part A", "Part B", "Argumentative", "Letter to Editor"])
    t_lv = st.select_slider("目标等级", options=["3", "4", "5", "5*", "5**"])
    u_text = st.text_area("在此输入...", height=200)
    
    if st.button("🚀 生成可视化评估报告"):
        if u_text:
            with st.spinner("DSE 考官评分中..."):
                prompt = f"""
                你是一位DSE考官。请分析这篇{t_type}作文。
                最后一行必须输出: SCORES: C:数字, O:数字, L:数字 (满分7)
                使用繁体中文。作文：{u_text}
                """
                res = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
                score_match = re.search(r"SCORES: C:(\d), O:(\d), L:(\d)", res.text)
                if score_match:
                    st.session_state.scores = {"Content": int(score_match.group(1)), "Organization": int(score_match.group(2)), "Language": int(score_match.group(3))}
                st.session_state.last_report = res.text.split("SCORES:")[0]
        else:
            st.warning("请输入作文内容")

    # --- 核心更新：数据仪表盘 ---
    if st.session_state.last_report:
        st.markdown("---")
        st.markdown("### 📊 评估仪表盘")
        
        d1, d2 = st.columns([1, 1.2]) # 分数表比例稍小，雷达图比例稍大
        
        with d1:
            # 左侧：分数表框架
            total = sum(st.session_state.scores.values())
            st.markdown(f"""
            <div class="score-table">
                <div style="text-align:center; margin-bottom:15px;">
                    <span style="font-size:0.9em; color:#666;">总分预估</span><br>
                    <span style="font-size:2em; font-weight:800; color:#1e3a8a;">{total}</span>
                    <span style="color:#666;">/ 21</span>
                </div>
                <div class="score-row"><span class="score-label">Content</span><span class="score-value">{st.session_state.scores['Content']}/7</span></div>
                <div class="score-row"><span class="score-label">Organization</span><span class="score-value">{st.session_state.scores['Organization']}/7</span></div>
                <div class="score-row"><span class="score-label">Language</span><span class="score-value">{st.session_state.scores['Language']}/7</span></div>
                <div style="margin-top:10px;">
                    <p style="font-size:0.8em; color:#999;">*评分参考 DSE 官方 Marking Scheme</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with d2:
            # 右侧：雷达图
            cat = list(st.session_state.scores.keys())
            val = list(st.session_state.scores.values())
            fig_radar = go.Figure(data=go.Scatterpolar(r=val+[val[0]], theta=cat+[cat[0]], fill='toself', line_color='#fbbf24', fillcolor='rgba(251, 191, 36, 0.3)'))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), showlegend=False, height=280, margin=dict(t=20, b=20, l=40, r=40))
            st.plotly_chart(fig_radar, use_container_width=True)

        # 详细报告卡片
        st.markdown(f'<div class="report-card">{st.session_state.last_report}</div>', unsafe_allow_html=True)

with col2:
    st.markdown("### 💬 导师互动记录")
    chat_box = st.container(height=500)
    with chat_box:
        for r, t in st.session_state.chat_history:
            with st.chat_message(r): st.write(t)
            
    if p_input := st.chat_input("针对分数向导师提问..."):
        st.session_state.chat_history.append(("User", p_input))
        with st.chat_message("User"): st.write(p_input)
        with st.chat_message("AI"):
            ans = client.models.generate_content(model="gemini-3-flash-preview", contents=f"作文:{u_text}\n报告:{st.session_state.last_report}\n问题:{p_input}")
            st.write(ans.text)
            st.session_state.chat_history.append(("AI", ans.text))
            st.rerun()
