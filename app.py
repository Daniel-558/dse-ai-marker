import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import re

# 1. 配置
st.set_page_config(page_title="DSE 超级导师 AI", layout="wide")
api_key_val = st.secrets.get("GEMINI_API_KEY", "")

@st.cache_resource
def get_client(key):
    return Client(api_key=key) if key else None

client = get_client(api_key_val)

# 初始化状态
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "scores" not in st.session_state:
    st.session_state.scores = {"Content": 0, "Organization": 0, "Language": 0}

st.title("🤖 DSE AI 超级导师 (Pro版)")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### ✍️ 第一步：提交作文")
    task_type = st.selectbox("选择题型", ["Part A", "Part B", "Argumentative", "Letter to Editor"])
    target_lv = st.select_slider("目标等级", options=["3", "4", "5", "5*", "5**"])
    user_text = st.text_area("粘贴你的作文内容...", height=250)
    
    if st.button("🚀 深度批改报告", use_container_width=True):
        if user_text:
            with st.spinner("阅卷官正在打分并绘图..."):
                # 强化版 Prompt：强制要求输出分数标签
                prompt = f"""
                你是一位精通DSE评分标准的考官。请对这篇{task_type}作文给Level {target_lv}目标的同学写批改报告。
                
                必须严格遵守以下两个要求：
                1. 在回复的最后一行，必须按照此格式输出分数（每项满分7分）：SCORES: C:数字, O:数字, L:数字
                2. 使用繁体中文，提供评分、建议、范文和Killer词汇。
                
                作文内容：{user_text}
                """
                response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
                full_text = response.text
                
                # 提取分数
                score_match = re.search(r"SCORES: C:(\d), O:(\d), L:(\d)", full_text)
                if score_match:
                    st.session_state.scores = {
                        "Content": int(score_match.group(1)),
                        "Organization": int(score_match.group(2)),
                        "Language": int(score_match.group(3))
                    }
                
                st.session_state.last_report = full_text.split("SCORES:")[0] # 隐藏原始分数行
                st.session_state.chat_history = [("AI", "报告已生成！你可以根据雷达图查看弱项，并向我追问。")]
        else:
            st.warning("请输入内容")

    if "last_report" in st.session_state:
        # 绘制雷达图
        categories = list(st.session_state.scores.keys())
        values = list(st.session_state.scores.values())
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=values + [values[0]], theta=categories + [categories[0]], fill='toself', name='你的表现'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 7])), showlegend=False, height=350)
        
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(st.session_state.last_report)

with col2:
    st.markdown("### 💬 第二步：1-on-1 追问模式")
    if "last_report" not in st.session_state:
        st.info("完成左侧批改后开启对话。")
    else:
        for role, text in st.session_state.chat_history:
            with st.chat_message(role):
                st.write(text)
        
        if prompt_input := st.chat_input("针对批改结果追问..."):
            st.session_state.chat_history.append(("User", prompt_input))
            with st.chat_message("User"):
                st.write(prompt_input)
            
            with st.chat_message("AI"):
                context = f"作文: {user_text}\n报告: {st.session_state.last_report}\n问题: {prompt_input}"
                response = client.models.generate_content(model="gemini-3-flash-preview", contents=context)
                st.write(response.text)
                st.session_state.chat_history.append(("AI", response.text))
                # 在原有代码的 col1 部分，增加一个新的功能块
with col1:
    st.markdown("---")
    st.markdown("### 💡 金句实验室 (Sentence Booster)")
    target_sentence = st.text_input("输入一个普通句子，我帮你升级成 5** 句式：", placeholder="例如: Plastic bags are bad for the environment.")
    
    if st.button("✨ 瞬间升级", use_container_width=True):
        if target_sentence:
            with st.spinner("正在注入 5** 灵魂..."):
                boost_prompt = f"你是一位 DSE 补习名师。请将以下句子升级为 Level 5** 水平。要求：使用更高级的词汇（Killer Vocab）、复杂的从句结构，并解释改写后的加分点。句子：{target_sentence}"
                boost_response = client.models.generate_content(model="gemini-3-flash-preview", contents=boost_prompt)
                st.success("升级成功！")
                st.markdown(boost_response.text)

