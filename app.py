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

# 1. 页面配置与高级 UI 注入
st.set_page_config(page_title="DSE AI 写作工作站", layout="wide")

st.markdown("""
    <style>
    .stApp { background: linear-gradient(to bottom, #f8fafc, #f1f5f9); }
    .main-header { background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); padding: 2rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 20px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
    .tool-card { background: white; border-radius: 12px; padding: 1.5rem; border: 1px solid #e2e8f0; margin-bottom: 1rem; }
    .stat-box { border-left: 4px solid #3b82f6; padding-left: 15px; margin: 10px 0; }
    .essay-box { background: #ffffff; border: 2px solid #e2e8f0; border-radius: 10px; padding: 20px; font-family: 'Georgia', serif; line-height: 1.6; }
    .stButton>button { border-radius: 8px; transition: all 0.3s; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4); }
    </style>
    """, unsafe_allow_html=True)

# 2. 初始化 API
api_key_val = st.secrets.get("GEMINI_API_KEY", "")
@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None
client = get_client(api_key_val)

if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "scores" not in st.session_state: st.session_state.scores = {"Content": 0, "Organization": 0, "Language": 0}
if "last_report" not in st.session_state: st.session_state.last_report = ""

# 3. 侧边栏：备考小工具
with st.sidebar:
    st.markdown("### 🔒 导师访问权限")
    if st.text_input("邀请码", type="password") != "DSE2026":
        st.info("请输入邀请码解锁 DSE 备考全功能")
        st.stop()
    
    st.markdown("---")
    # 功能 1：DSE 倒数
    st.markdown("### ⏳ 考试倒数")
    dse_date = datetime(2026, 4, 10) # 假设 2026 考试日期
    days_left = (dse_date - datetime.now()).days
    st.metric("距离 DSE 2026 英文科开考", f"{days_left} Days")
    
    st.markdown("---")
    st.title("📂 多模态提交")
    uploaded_file = st.file_uploader("手写照片识别 / PDF / Word", type=['png', 'jpg', 'jpeg', 'pdf', 'docx'])
    
    st.markdown("---")
    # 功能 2：高分资源位
    st.markdown("### 📚 5** 写作库")
    topic_ref = st.selectbox("选择写作主题词汇包", ["Environment", "Technology", "Social Issues", "Sports"])
    vocab_map = {
        "Environment": "Sustainable, Degradation, Ecological footprint",
        "Technology": "Revolutionize, Ubiquitous, Cyberbullying",
        "Social Issues": "Marginalized, Socio-economic, Disparity",
        "Sports": "Camaraderie, Perseverance, Resilience"
    }
    st.code(vocab_map[topic_ref])

# 4. 主界面：工作站布局
st.markdown('<div class="main-header"><h1>🤖 DSE AI 超级导师 Pro - 全能工作站</h1><p>全港首個集批改、識圖、範文、資源於一體的 AI 平台</p></div>', unsafe_allow_html=True)

col1, col2 = st.columns([1.3, 0.7], gap="large")

with col1:
    with st.expander("📝 提交批改 (写作输入)", expanded=True):
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            task_type = st.selectbox("选择 DSE 卷二题型", ["Part A (Short)", "Part B (Argumentative)", "Part B (Report)", "Part B (Proposal)", "Part B (Story)"])
        with t_col2:
            target_lv = st.select_slider("你的目标等级", options=["3", "4", "5", "5*", "5**"])
        
        user_text = st.text_area("在此粘贴作文或在左侧上传照片...", height=200, placeholder="Once upon a time...")
        
        if st.button("🚀 启动深度批改系统"):
            with st.spinner("正在融合 Gemini 2.0 识图与 DSE 考官逻辑..."):
                prompt = f"""
                你是一位資深DSE英文考官。請批改{task_type}作文。
                必須包括：
                1. [評分分析] 
                2. [優缺點對比] 
                3. [5** 範文示範]：針對本題題目寫一段 180 字的高級示範。
                4. [語法糾錯]：挑出 3 個最嚴重的錯誤並改正。
                最後一行輸出: SCORES: C:數字, O:數字, L:數字 (每項滿分 7)。
                使用繁體中文。
                """
                content = [prompt]
                if uploaded_file:
                    if uploaded_file.type in ["image/png", "image/jpeg"]:
                        content.append(Image.open(uploaded_file))
                    else:
                        content.append(uploaded_file.getvalue())
                else:
                    content.append(user_text)
                
                res = client.models.generate_content(model="gemini-2.0-flash", contents=content)
                st.session_state.last_report = res.text
                # 提取分数
                match = re.search(r"SCORES: C:(\d), O:(\d), L:(\d)", res.text)
                if match:
                    st.session_state.scores = {"Content": int(match.group(1)), "Organization": int(match.group(2)), "Language": int(match.group(3))}

    if st.session_state.last_report:
        # 功能 3：可视化仪表盘更新
        st.markdown("### 📊 评估仪表盘")
        d1, d2, d3 = st.columns([1, 1, 1.2])
        total = sum(st.session_state.scores.values())
        
        with d1:
            st.markdown(f'<div class="score-card"><p style="margin:0; font-size:0.9em;">Total Score</p><h2 style="color:#1e3a8a;">{total}/21</h2></div>', unsafe_allow_html=True)
            # 下载 PDF 逻辑 (简化)
            st.download_button("📥 下载 PDF 报告", "Report placeholder", "DSE_Report.pdf")
            
        with d2:
            # 功能 4：等级预估
            if total >= 18: lv = "5**"
            elif total >= 16: lv = "5*"
            elif total >= 14: lv = "5"
            else: lv = "Below 5"
            st.markdown(f'<div class="score-card"><p style="margin:0; font-size:0.9em;">Estimated Lv</p><h2 style="color:#10b981;">{lv}</h2></div>', unsafe_allow_html=True)
            
        with d3:
            fig = go.Figure(data=go.Scatterpolar(r=list(st.session_state.scores.values())+[list(st.session_state.scores.values())[0]], theta=['C','O','L','C'], fill='toself', line_color='#3b82f6'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), showlegend=False, height=180, margin=dict(t=10, b=10, l=30, r=30))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(f'<div class="report-container">{st.session_state.last_report}</div>', unsafe_allow_html=True)

with col2:
    st.markdown("### 💬 导师答疑 & 追问")
    chat_box = st.container(height=500, border=True)
    with chat_box:
        if not st.session_state.last_report:
            st.warning("请先生成报告以开启对话。")
        for role, text in st.session_state.chat_history:
            with st.chat_message(role): st.write(text)
    
    if p_input := st.chat_input("追问导师，如：为什么这个句子语法不对？"):
        st.session_state.chat_history.append(("User", p_input))
        with st.chat_message("User"): st.write(p_input)
        ans = client.models.generate_content(model="gemini-2.0-flash", contents=f"Report:{st.session_state.last_report}\nQuestion:{p_input}")
        st.session_state.chat_history.append(("AI", ans.text))
        st.rerun()
    
    st.markdown("---")
    # 底部快捷功能：金句实验室
    st.markdown("### ✨ 5** 金句一键升级")
    simple_s = st.text_input("输入简单句：", placeholder="People think plastic is bad.")
    if st.button("Magic Upgrade"):
        magic_res = client.models.generate_content(model="gemini-2.0-flash", contents=f"Upgrade this to DSE Level 5** with complex vocab: {simple_s}")
        st.success(magic_res.text)
