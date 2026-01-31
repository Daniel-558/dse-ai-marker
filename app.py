import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import re
from fpdf import FPDF
import io
import os
from datetime import datetime
from docx import Document
from PIL import Image

# 1. 页面配置
st.set_page_config(page_title="DSE AI 写作工作站 Pro", layout="wide")

# 2. 深度定制 UI 样式
st.markdown("""
    <style>
    .stApp { background: #f8fafc; }
    .main-header { background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); padding: 1.5rem; border-radius: 12px; color: white; text-align: center; margin-bottom: 20px; }
    .score-card { background: white; border-radius: 12px; padding: 15px; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; }
    .report-container { background: white; padding: 25px; border-radius: 15px; border-left: 6px solid #fbbf24; margin-top: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); white-space: pre-wrap; }
    .stButton>button { border-radius: 8px; font-weight: bold; height: 3em; }
    .timer-box { background: #fee2e2; padding: 10px; border-radius: 8px; text-align: center; color: #dc2626; font-weight: bold; border: 1px solid #fca5a5; }
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

# 4. 侧边栏：核心控制台
with st.sidebar:
    st.markdown("### 🔐 权限验证")
    if st.text_input("邀请码", type="password") != "DSE2026":
        st.info("请输入邀请码解锁")
        st.stop()
    
    st.markdown("---")
    # 功能升级：实战计时器
    st.markdown("### ⏱️ 模拟计时")
    target_time = st.selectbox("设定制卷时间 (分钟)", [20, 45, 60, 120])
    if st.button("开始计时"):
        st.toast(f"计时开始！请在 {target_time} 分钟内完成写作。")
    st.markdown(f'<div class="timer-box">目标时长: {target_time} Mins</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📂 文件提交")
    uploaded_file = st.file_uploader("支持识图/PDF/Word", type=['png', 'jpg', 'jpeg', 'pdf', 'docx'])
    
    st.markdown("---")
    # 功能升级：5** 灵感库
    st.markdown("### 💡 考点联想")
    exam_topic = st.selectbox("联想历年主题", ["Social Issues", "Tech & Future", "Environment", "Campus Life"])
    tips = {
        "Social Issues": "关键词: Disparity, Marginalized, Stigmatization",
        "Tech & Future": "关键词: Double-edged sword, Revolutionize, Algorithm",
        "Environment": "关键词: Irreversible, Sustainability, Eco-conscious",
        "Campus Life": "关键词: Holistic, Peer pressure, Pedagogy"
    }
    st.info(tips[exam_topic])

# 5. 主界面布局
st.markdown('<div class="main-header"><h1>🤖 DSE AI 超级导师 Pro</h1><p>专注 Paper 2 写作升等 · 识图 & 范文 & 诊断一体化</p></div>', unsafe_allow_html=True)

col1, col2 = st.columns([1.2, 0.8], gap="large")

with col1:
    st.markdown("### ✍️ 写作任务")
    # 按要求精简：仅保留 Part A / Part B
    part_type = st.radio("选择考部分", ["Part A (Short - 10%)", "Part B (Long - 15%)"], horizontal=True)
    target_lv = st.select_slider("目标等级 (Target Level)", options=["3", "4", "5", "5*", "5**"])
    
    user_text = st.text_area("在此输入或粘贴作文...", height=200, placeholder="Start your masterpiece here...")
    
    if st.button("🚀 提交批改并生成 5** 范文"):
        with st.spinner("考官正在结合 DSE 评分标准进行深度分析..."):
            prompt = f"""
            你是一位資深DSE英文科考官。請批改這篇{part_type}作文，目標等級為{target_lv}。
            報告必須包含：
            1. [等級評估]：給出預估等級並解釋理由。
            2. [亮點與盲點]：分別列出加分句式與扣分錯誤。
            3. [5** 範文示範]：根據題目撰寫一段約 180 字的高級示範（使用 5** 詞彙）。
            4. [建議行動]：給出 3 個具體的提分建議。
            最後一行輸出: SCORES: C:數字, O:數字, L:數字 (每項滿分 7)。
            請使用繁體中文。
            """
            inputs = [prompt]
            if uploaded_file:
                if uploaded_file.type in ["image/png", "image/jpeg"]:
                    inputs.append(Image.open(uploaded_file))
                else:
                    inputs.append(uploaded_file.getvalue())
            else:
                inputs.append(user_text)
            
            res = client.models.generate_content(model="gemini-2.0-flash", contents=inputs)
            st.session_state.last_report = res.text
            match = re.search(r"SCORES: C:(\d), O:(\d), L:(\d)", res.text)
            if match:
                st.session_state.scores = {"Content": int(match.group(1)), "Organization": int(match.group(2)), "Language": int(match.group(3))}

    if st.session_state.last_report:
        # 可视化评估区
        st.markdown("---")
        v1, v2, v3 = st.columns([1, 1, 1.2])
        total = sum(st.session_state.scores.values())
        
        with v1:
            st.markdown(f'<div class="score-card"><p style="color:#64748b; margin:0;">Total Score</p><h3>{total}/21</h3></div>', unsafe_allow_html=True)
        with v2:
            # 自动等级推算
            est_lv = "5**" if total >= 19 else "5*" if total >= 17 else "5" if total >= 15 else "4" if total >= 13 else "3"
            st.markdown(f'<div class="score-card"><p style="color:#64748b; margin:0;">Est. Grade</p><h3 style="color:#3b82f6;">{est_lv}</h3></div>', unsafe_allow_html=True)
        with v3:
            fig = go.Figure(data=go.Scatterpolar(r=list(st.session_state.scores.values())+[list(st.session_state.scores.values())[0]], 
                                              theta=['Content','Org','Lang','Content'], fill='toself', line_color='#3b82f6'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), showlegend=False, height=150, margin=dict(t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(f'<div class="report-container">{st.session_state.last_report}</div>', unsafe_allow_html=True)

with col2:
    st.markdown("### 💬 导师互动答疑")
    chat_box = st.container(height=450, border=True)
    with chat_box:
        if not st.session_state.last_report:
            st.info("生成报告后可向导师追问 5** 范文中的词汇用法。")
        for r, t in st.session_state.chat_history:
            with st.chat_message(r): st.write(t)
            
    if p_input := st.chat_input("针对报告提问..."):
        st.session_state.chat_history.append(("User", p_input))
        with st.chat_message("User"): st.write(p_input)
        ans = client.models.generate_content(model="gemini-2.0-flash", contents=f"Report:{st.session_state.last_report}\nQuestion:{p_input}")
        st.session_state.chat_history.append(("AI", ans.text))
        st.rerun()

    st.markdown("---")
    # 功能升级：5** 金句一键生成
    st.markdown("### ✨ 金句实验室 (Sentence Lab)")
    simple_s = st.text_input("输入普通句子，导师为你升华：", placeholder="It is good for our environment.")
    if st.button("瞬间升华 (Upgrade)"):
        upgrade_res = client.models.generate_content(model="gemini-2.0-flash", contents=f"Upgrade this sentence to DSE Level 5** with elite vocabulary: {simple_s}")
        st.success(upgrade_res.text)
