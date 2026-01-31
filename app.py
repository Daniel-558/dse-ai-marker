import streamlit as st
from google.genai import Client
import plotly.graph_objects as go
import numpy as np
import sympy as sp
import os
from datetime import date
from PIL import Image
from fpdf import FPDF

# --- 1. 頁面配置 ---
st.set_page_config(page_title="DSE AI 伴學夥伴", layout="wide", page_icon="📐")

st.markdown("""
    <style>
    /* 清新晨曦漸變背景 */
    .stApp {
        background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);
        color: #333333;
    }
    .hero-title {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 900;
        text-align: center;
        margin-bottom: 20px;
    }
    .feature-card {
        background: rgba(255, 255, 255, 0.95);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid rgba(0,0,0,0.05);
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    /* 數學符號按鈕樣式 */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        background-color: white;
        font-weight: bold;
        color: #444;
    }
    .stButton>button:hover {
        background-color: #f0fdf4;
        color: #059669;
        border-color: #059669;
    }
    /* 隱藏 Plotly Modebar 中不必要的按鈕，讓界面更像 Desmos */
    .modebar-btn { color: #888 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 狀態管理 ---
if "xp" not in st.session_state: st.session_state.xp = 1250
if "user_level" not in st.session_state: st.session_state.user_level = "Lv.3 備考新星"
if "exam_date" not in st.session_state: st.session_state.exam_date = date(2026, 4, 21)
if "math_eq" not in st.session_state: st.session_state.math_eq = "x * sin(x)" # 默認函數

# API Setup
api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
@st.cache_resource
def get_ai():
    return Client(api_key=api_key) if api_key else None
client = get_ai()

# --- 3. 輔助函數 ---
# 默认模型设置（可改为你希望的模型）
DEFAULT_MODEL = "gpt-5-mini"

# 为方便统一管理模型参数，包装原始 generate_content，使未显式传入 model 时使用 DEFAULT_MODEL
try:
    _orig_generate = client.models.generate_content
    def _generate_content_wrapper(*, model=None, contents=None, **kwargs):
        use_model = model or DEFAULT_MODEL
        return _orig_generate(model=use_model, contents=contents, **kwargs)
    client.models.generate_content = _generate_content_wrapper
except Exception:
    # 如果 client 未正确初始化（例如无 API key），忽略包装，后续调用会在运行时报错并提示配置 API Key
    pass

def level_up_check():
    st.session_state.xp += 50
    st.toast(f"🌟 經驗值 +50!", icon="🎉")

def add_symbol(sym):
    """將符號追加到當前方程"""
    st.session_state.math_eq += sym

def parse_equation(eq_str):
    """使用 SymPy 解析用戶輸入的字符串為數學函數"""
    try:
        x = sp.symbols('x')
        # 預處理：將 ^ 替換為 ** (Python 語法)
        eq_str = eq_str.replace('^', '**')
        # 解析表達式
        expr = sp.sympify(eq_str)
        # 轉換為 numpy 可計算的函數
        f = sp.lambdify(x, expr, 'numpy')
        return f, str(expr).replace('**', '^')
    except Exception as e:
        return None, str(e)

# --- 4. 側邊欄 ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2936/2936735.png", width=70)
    st.title("DSE 狀元中樞")
    
    st.progress(int((st.session_state.xp % 1000) / 10), text=f"XP: {st.session_state.xp}")
    days_left = (st.session_state.exam_date - date.today()).days
    st.caption(f"📅 距離開考: {days_left} 天")
    
    st.markdown("---")
    selected_subject = st.radio("📚 選擇科目", ["🧮 數學 (Maths)", "🇬🇧 英文 (English)", "🏮 中文 (Chinese)", "🌏 公社科 (CSD)"])
    st.markdown("---")
    up_file = st.file_uploader("📷 上傳題目/試卷", type=['png', 'jpg', 'jpeg'])

# --- 5. 主界面 ---
st.markdown(f'<div class="hero-title">{selected_subject.split("(")[0]} AI 導師</div>', unsafe_allow_html=True)

if not client:
    st.warning("⚠️ 請配置 API Key")
    st.stop()

# ==========================================
# 🧮 數學科 (Maths) - Desmos 風格繪圖器
# ==========================================
if "數學" in selected_subject:
    math_features = [
        "📊 函数绘图 (Grapher)",
        "⚡ 步骤拆解",
        "💣 陷阱扫描",
        "📝 智能批改作业",
        "📈 数据分析与统计",
        "🔢 方程求解器",
        "📚 题库训练营",
        "🧩 数学小游戏",
        "🕒 历年真题演练",
        "📋 错题本管理",
        "🎯 知识点自测"
    ]
    math_features = [
        ("📊 函数绘图 (Grapher)", "math_grapher"),
        ("⚡ 步骤拆解", "math_step"),
        ("💣 陷阱扫描", "math_trap"),
        ("📝 智能批改作业", "math_hw"),
        ("📈 数据分析与统计", "math_stats"),
        ("🔢 方程求解器", "math_eq"),
        ("📚 题库训练营", "math_qbank"),
        ("🧩 数学小游戏", "math_game"),
        ("🕒 历年真题演练", "math_past"),
        ("📋 错题本管理", "math_wrong"),
        ("🎯 知识点自测", "math_quiz"),
        ("📖 知识库（公式&计算器）", "math_know")
    ]
    st.markdown("#### 请选择功能：")
    cols = st.columns(3)
    for idx, (label, key) in enumerate(math_features):
        if cols[idx % 3].button(label, key=f"btn_{key}"):
            st.session_state["math_selected"] = key
    selected = st.session_state.get("math_selected", "math_grapher")
    st.markdown("---")
    # 动态内容区
    if selected == "math_grapher":
        st.markdown("#### 输入函数表达式 (如 x*sin(x), x**2+3*x-5):")
        eq_input = st.text_input("y =", value=st.session_state.get("math_eq", "x*sin(x)"), key="math_eq_grapher")
        func, display_eq = parse_equation(eq_input)
        if func:
            x_vals = np.linspace(-10, 10, 1000)
            try:
                y_vals = func(x_vals)
                if isinstance(y_vals, (int, float)):
                    y_vals = np.full_like(x_vals, y_vals)
                y_vals = np.where(np.abs(y_vals) > 1000, np.nan, y_vals)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines', name=f'y={display_eq}'))
                fig.update_layout(title=f"y = {display_eq}", xaxis_title="x", yaxis_title="y", height=400)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"无法绘图: {e}")
        else:
            st.info("请输入有效的数学表达式，如 x**2+3*x-5")
    elif selected == "math_step":
        st.markdown("#### 智能分步解题")
        q_math = st.text_area("输入数学题目:")
        if st.button("AI 生成分步解答", key="math_step_solve"):
            with st.spinner("AI 正在分析..."):
                prompt = "你是一位DSE数学名师，请分步详细解答下列题目，使用LaTeX格式：" + q_math
                res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.markdown(res.text)
    elif selected == "math_trap":
        st.markdown("#### 常见陷阱扫描")
        topic = st.selectbox("选择课题", ["Quadratic Equations", "Trigonometry", "Coordinate Geometry", "Calculus", "Statistics"])
        if st.button("扫描常犯错误", key="math_trap_scan"):
            prompt = f"DSE Maths Topic: {topic}. List 3 common traps/mistakes students make."
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.warning(res.text)
    elif selected == "math_hw":
        st.markdown("#### 上传作业图片或输入答案，AI 批改")
        up_file = st.file_uploader("上传作业图片 (jpg/png)", type=["jpg", "png"], key="math_hw_img")
        hw_text = st.text_area("或直接输入你的解答:", key="math_hw_text")
        if st.button("AI 批改作业", key="math_hw_check"):
            with st.spinner("AI 正在批改..."):
                prompt = "你是一位DSE数学老师，请批改下列作业并给出分数与建议："
                if hw_text:
                    prompt += hw_text
                if up_file:
                    prompt += "（附图片）"
                res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.success(res.text)
    elif selected == "math_stats":
        st.markdown("#### 数据分析与统计工具")
        st.info("输入一组数据，自动分析均值、方差、最大最小值等")
        data_input = st.text_area("输入数据（用逗号分隔）:", key="math_stats_data")
        if st.button("分析数据", key="math_stats_btn"):
            try:
                data = np.array([float(x) for x in data_input.split(",") if x.strip()])
                st.write(f"均值: {np.mean(data):.2f}")
                st.write(f"方差: {np.var(data):.2f}")
                st.write(f"最大值: {np.max(data)}")
                st.write(f"最小值: {np.min(data)}")
            except Exception as e:
                st.error(f"数据格式有误: {e}")
    elif selected == "math_eq":
        st.markdown("#### 方程求解器 (支持一元/二元)")
        eq = st.text_input("输入方程 (如 x**2-4=0 或 x+y=5, x-y=1):", key="math_eq_solver")
        if st.button("求解方程", key="math_eq_solve_btn"):
            try:
                if "," in eq or "\n" in eq:
                    eqs = [e.replace("=", "-") for e in eq.replace("\n", ",").split(",") if e.strip()]
                    syms = sp.symbols('x y')
                    sol = sp.solve([sp.sympify(e) for e in eqs], syms)
                else:
                    syms = sp.symbols('x')
                    sol = sp.solve(sp.sympify(eq.replace("=", "-")), syms)
                st.write(f"解: {sol}")
            except Exception as e:
                st.error(f"无法求解: {e}")
    elif selected == "math_qbank":
        st.markdown("#### DSE 数学知识库（内容暂未上线，敬请期待）")
        st.info("本区块将集成数学公式大全等权威内容，后续上线。")



# ==========================================
# 🇬🇧 英文科 (English) - AI 学习助手
# ==========================================
elif "英文" in selected_subject:
    eng_features = [
        ("✍️ 作文批改", "eng_essay"),
        ("📚 范文与建议", "eng_sample"),
        ("📝 词汇语法练习", "eng_vocab"),
        ("🎤 口语模拟面试", "eng_speak"),
        ("🔍 阅读理解训练", "eng_read"),
        ("🧠 词汇记忆卡片", "eng_word"),
        ("📖 听力练习", "eng_listen"),
        ("🗣️ 句型变换训练", "eng_sent"),
        ("📋 错题本管理", "eng_wrong"),
        ("🕒 历年真题演练", "eng_past"),
        ("🎯 知识点自测", "eng_quiz")
    ]
    st.markdown("#### 请选择功能：")
    cols = st.columns(3)
    for idx, (label, key) in enumerate(eng_features):
        if cols[idx % 3].button(label, key=f"btn_{key}"):
            st.session_state["eng_selected"] = key
    selected = st.session_state.get("eng_selected", "eng_essay")
    st.markdown("---")
    # 动态内容区
    if selected == "eng_essay":
        st.markdown("#### 英文作文批改与反馈")
        user_essay = st.text_area("请粘贴你的英文作文：", height=200, key="eng_essay_text")
        if st.button("AI 批改并反馈", key="eng_correct"):
            with st.spinner("AI 正在批改中..."):
                prompt = [
                    "你是一位DSE英文写作专家，请严格按照DSE评分标准（内容、结构、语言）批改下文作文，给出：1. 预估等级（Level 1-5*），2. 优缺点分析，3. 具体修改建议，4. 润色后的句子，5. 针对弱项的微型范文。",
                    user_essay
                ]
                res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.markdown(res.text)
    elif selected == "eng_sample":
        st.markdown("#### 高分范文与写作建议")
        if st.button("获取高分范文与建议", key="eng_sample_btn"):
            with st.spinner("AI 正在生成范文..."):
                prompt = "请给出一篇DSE英文写作高分范文，并总结写作技巧与常见失分点。"
                res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.markdown(res.text)
    elif selected == "eng_vocab":
        st.markdown("#### 词汇与语法专项练习")
        quiz = {"Choose the correct word:": ["affect/effect", "accept/except", "advice/advise"]}
        for q, opts in quiz.items():
            st.write(q)
            for opt in opts:
                st.write(f"- {opt}")
        st.info("更多练习题即将上线！")
    elif selected == "eng_speak":
        st.markdown("#### 口语模拟面试")
        topic = st.text_input("输入口语话题:", key="eng_speak_topic")
        if st.button("AI 生成口语答案", key="eng_speak_btn"):
            prompt = f"请以DSE英文口语考试标准，针对话题'{topic}'生成一段高分口语答案。"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.success(res.text)
    elif selected == "eng_read":
        st.markdown("#### 阅读理解训练")
        passage = st.text_area("输入英文短文:", key="eng_read_passage")
        if st.button("AI 生成阅读理解题", key="eng_read_btn"):
            prompt = f"请根据下文生成3道DSE英文阅读理解题及答案：{passage}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.info(res.text)
    elif selected == "eng_word":
        st.markdown("#### 词汇记忆卡片")
        word = st.text_input("输入要记忆的单词:", key="eng_word_card")
        if st.button("生成记忆卡片", key="eng_word_btn"):
            prompt = f"请为单词'{word}'生成英文释义、例句和记忆法。"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.info(res.text)
    elif selected == "eng_listen":
        st.markdown("#### 听力练习（文本模拟）")
        st.info("请使用外部音频资源，后续将支持音频上传与AI批改。")
    elif selected == "eng_sent":
        st.markdown("#### 句型变换训练")
        sentence = st.text_input("输入句子:", key="eng_sent_trans")
        if st.button("AI 句型变换", key="eng_sent_btn"):
            prompt = f"请将下列句子变换为另一种表达方式：{sentence}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.info(res.text)
    elif selected == "eng_wrong":
        st.markdown("#### 英文错题本管理")
        if 'eng_wrongbook' not in st.session_state:
            st.session_state.eng_wrongbook = []
        add_wrong = st.text_area("添加错题（描述或粘贴题目）:", key="eng_wrong_add")
        if st.button("添加到错题本", key="eng_wrong_add_btn"):
            if add_wrong:
                st.session_state.eng_wrongbook.append(add_wrong)
                st.success("已添加到错题本！")
        st.write("##### 我的错题本：")
        for i, q in enumerate(st.session_state.eng_wrongbook):
            st.write(f"{i+1}. {q}")
    elif selected == "eng_past":
        st.markdown("#### DSE 英文历年真题演练 (示例)")
        st.write("2022 Q1: Write an essay about the importance of teamwork.")
        user_ans = st.text_area("你的答案:", key="eng_past_ans")
        if st.button("提交答案", key="eng_past_submit"):
            prompt = f"请为下列DSE历年真题评分并给出详细解析：Write an essay about the importance of teamwork.\n学生答案：{user_ans}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.success(res.text)
    elif selected == "eng_quiz":
        st.markdown("#### 英语知识点自测 (选择题)")
        quiz = {
            "Which is correct?": ["A. their", "B. there", "C. they're", "D. thier"],
            "What is the synonym of 'happy'?": ["A. sad", "B. joyful", "C. angry", "D. tired"]
        }
        q_list = list(quiz.keys())
        q_idx = st.number_input("选择题号", min_value=0, max_value=len(q_list)-1, value=0, step=1, key="eng_quiz_idx")
        st.write(q_list[q_idx])
        options = quiz[q_list[q_idx]]
        user_choice = st.radio("你的选择:", options, key="eng_quiz_choice")
        if st.button("提交自测", key="eng_quiz_submit"):
            answer = ["B. there", "B. joyful"]
            if user_choice == answer[q_idx]:
                st.success("答对了！")
            else:
                st.error("答错了，继续努力！")

# ==========================================
# 🏮 中文科 (Chinese)
# ==========================================
elif "中文" in selected_subject:
    chi_features = [
        ("📜 文言文翻译", "chi_wyw"),
        ("📚 阅读理解训练", "chi_read"),
        ("✍️ 作文批改", "chi_essay"),
        ("📝 现代文写作", "chi_write"),
        ("🔍 词语注释", "chi_word"),
        ("🧠 成语与修辞训练", "chi_idiom"),
        ("📖 听力练习", "chi_listen"),
        ("📋 错题本管理", "chi_wrong"),
        ("🕒 历年真题演练", "chi_past"),
        ("🎯 知识点自测", "chi_quiz"),
        ("📑 诗词鉴赏", "chi_poem"),
        ("📖 12篇必读", "chi_12")
    ]
    st.markdown("#### 请选择功能：")
    cols = st.columns(3)
    for idx, (label, key) in enumerate(chi_features):
        if cols[idx % 3].button(label, key=f"btn_{key}"):
            st.session_state["chi_selected"] = key
    selected = st.session_state.get("chi_selected", "chi_wyw")
    st.markdown("---")
    # 动态内容区
    if selected == "chi_wyw":
        st.markdown("#### 文言文智能翻译")
        wyw = st.text_area("输入古文句子:", key="chi_wyw_text")
        if st.button("AI 翻译", key="chi_wyw_btn"):
            prompt = f"请将下列文言文翻译为现代白话文：{wyw}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.success(res.text)
    elif selected == "chi_read":
        st.markdown("#### 阅读理解训练")
        passage = st.text_area("输入现代文或古文:", key="chi_read_passage")
        if st.button("AI 生成阅读理解题", key="chi_read_btn"):
            prompt = f"请根据下文生成3道DSE中文阅读理解题及答案：{passage}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.info(res.text)
    elif selected == "chi_essay":
        st.markdown("#### 作文批改与反馈")
        user_essay = st.text_area("请粘贴你的作文：", height=200, key="chi_essay_text")
        if st.button("AI 批改并反馈", key="chi_correct"):
            prompt = [
                "你是一位DSE中文写作专家，请严格按照DSE评分标准批改下文作文，给出等级、优缺点、修改建议和范文。",
                user_essay
            ]
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.markdown(res.text)
    elif selected == "chi_write":
        st.markdown("#### 现代文写作训练")
        topic = st.text_input("输入写作主题:", key="chi_write_topic")
        if st.button("AI 生成范文", key="chi_write_btn"):
            prompt = f"请以'{topic}'为题写一篇DSE中文现代文范文。"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.info(res.text)
    elif selected == "chi_word":
        st.markdown("#### 词语注释")
        word = st.text_input("输入词语:", key="chi_word_note")
        if st.button("AI 注释", key="chi_word_btn"):
            prompt = f"请为词语'{word}'做注释和用法说明。"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.info(res.text)
    elif selected == "chi_idiom":
        st.markdown("#### 成语与修辞训练")
        idiom = st.text_input("输入成语:", key="chi_idiom_text")
        if st.button("AI 释义与造句", key="chi_idiom_btn"):
            prompt = f"请为成语'{idiom}'做释义并造句。"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.info(res.text)
    elif selected == "chi_listen":
        st.markdown("#### 听力练习（文本模拟）")
        st.info("请使用外部音频资源，后续将支持音频上传与AI批改。")
    elif selected == "chi_wrong":
        st.markdown("#### 中文错题本管理")
        if 'chi_wrongbook' not in st.session_state:
            st.session_state.chi_wrongbook = []
        add_wrong = st.text_area("添加错题（描述或粘贴题目）:", key="chi_wrong_add")
        if st.button("添加到错题本", key="chi_wrong_add_btn"):
            if add_wrong:
                st.session_state.chi_wrongbook.append(add_wrong)
                st.success("已添加到错题本！")
        st.write("##### 我的错题本：")
        for i, q in enumerate(st.session_state.chi_wrongbook):
            st.write(f"{i+1}. {q}")
    elif selected == "chi_past":
        st.markdown("#### DSE 中文历年真题演练 (示例)")
        st.write("2022 Q1: 请写一篇关于‘诚信’的议论文。")
        user_ans = st.text_area("你的答案:", key="chi_past_ans")
        if st.button("提交答案", key="chi_past_submit"):
            prompt = f"请为下列DSE历年真题评分并给出详细解析：请写一篇关于‘诚信’的议论文。\n学生答案：{user_ans}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.success(res.text)
    elif selected == "chi_quiz":
        st.markdown("#### 中文知识点自测 (选择题)")
        quiz = {
            "‘诚’的本义是？": ["A. 真实", "B. 虚假", "C. 快乐", "D. 伤心"],
            "‘修辞’的作用是？": ["A. 美化语言", "B. 增加字数", "C. 减少内容", "D. 无作用"]
        }
        q_list = list(quiz.keys())
        q_idx = st.number_input("选择题号", min_value=0, max_value=len(q_list)-1, value=0, step=1, key="chi_quiz_idx")
        st.write(q_list[q_idx])
        options = quiz[q_list[q_idx]]
        user_choice = st.radio("你的选择:", options, key="chi_quiz_choice")
        if st.button("提交自测", key="chi_quiz_submit"):
            answer = ["A. 真实", "A. 美化语言"]
            if user_choice == answer[q_idx]:
                st.success("答对了！")
            else:
                st.error("答错了，继续努力！")
    elif selected == "chi_poem":
        st.markdown("#### 诗词鉴赏")
        poem = st.text_area("输入诗词:", key="chi_poem_text")
        if st.button("AI 赏析", key="chi_poem_btn"):
            prompt = f"请对下列诗词进行赏析：{poem}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.info(res.text)

    elif selected == "chi_12":
        st.markdown("#### DSE 语文12篇必读课文（摘要、节选、白话译与考试提示）")
        # 为避免版权问题，本模块提供：原文节选、白话译文、要点与考试提示
        dse_12 = [
            {
                "篇名": "岳阳楼记",
                "作者": "范仲淹",
                "出处": "范文正公集",
                "excerpt": "先天下之忧而忧，后天下之乐而乐。",
                "baihua": "应当先为天下的人担忧，后享受天下的快乐。",
                "analysis": ["怀古寓志","情景交融","政治理想的表述"],
                "exam_tips": "分析作者的政治情怀与修辞（排比、对偶），联系文章结构论证主旨。"
            },
            {
                "篇名": "始得西山宴游记",
                "作者": "柳宗元",
                "出处": "柳河东集",
                "excerpt": "始得西山宴遊記，聊以忘憂。",
                "baihua": "初次在西山宴游，暂且忘却了心中的烦忧。",
                "analysis": ["山水描写的抒情功能","主客觀描寫的轉換"],
                "exam_tips": "注意作者如何借景抒情，段落轉折處的語氣與意境。"
            },
            {
                "篇名": "师说",
                "作者": "韩愈",
                "出处": "昌黎先生集",
                "excerpt": "古之学者必有师。师者，所以传道受业解惑也。",
                "baihua": "古代的學習者一定有老師；老師就是傳授道理、講授學業、解決疑惑的人。",
                "analysis": ["論說文的論證模式","尊師觀念的文化意義"],
                "exam_tips": "可分析論證技巧（例證、比喻）及作者立場，並結合作文題目延展。"
            },
            {
                "篇名": "鱼我所欲也",
                "作者": "孟子",
                "出处": "孟子·告子上",
                "excerpt": "魚，我所欲也；熊掌，亦我所欲也。",
                "baihua": "魚是我想要的，熊掌也是我想要的。",
                "analysis": ["排比論證","道德與利益的抉擇"],
                "exam_tips": "梳理論證流程，指出作者用例證支持倫理主張的方式。"
            },
            {
                "篇名": "逍遥游",
                "作者": "庄子",
                "出处": "庄子·逍遥游",
                "excerpt": "北冥有魚，其名為鯤。",
                "baihua": "北方大海有一種魚，名叫鯤。",
                "analysis": ["寓言與比喻","哲理思辨的表現手法"],
                "exam_tips": "重點分析寓言意象與作者提出的逍遙思想，避免逐句直譯。"
            },
            {
                "篇名": "廉颇蔺相如列传",
                "作者": "司马迁",
                "出处": "史记·廉颇蔺相如列传",
                "excerpt": "廉颇蔺相如，皆赵之良将也。",
                "baihua": "廉颇和蔺相如，都是趙國的名將。",
                "analysis": ["人物性格刻畫","衝突與化解的敘事技巧"],
                "exam_tips": "分析人物對話與行動，從衝突中揭示性格及主題。"
            },
            {
                "篇名": "出师表",
                "作者": "诸葛亮",
                "出处": "三国",
                "excerpt": "先帝创业未半而中道崩殂。",
                "baihua": "先帝創業還未完成就去世了。",
                "analysis": ["表文的情感與忠誠表達","修辭（恳切語氣）的運用"],
                "exam_tips": "注意表文的語氣與結構，以及作者如何以誠懇打動讀者。"
            },
            {
                "篇名": "六国论",
                "作者": "苏洵",
                "出处": "嘉祐集",
                "excerpt": "六國者，周之餘命也。",
                "baihua": "六国，是周朝遗留下來的命運。",
                "analysis": ["議論文的邏輯結構","歷史事例的借鑒作用"],
                "exam_tips": "理清論證順序，指出作者如何用史實支持觀點。"
            },
            {
                "篇名": "登高（节选）",
                "作者": "杜甫",
                "出处": "唐代",
                "excerpt": "無邊落木蕭蕭下，不盡長江滾滾來。",
                "baihua": "無邊的落葉在飄落，長江滾滾不息地流來。",
                "analysis": ["意象與情感的融合","時局感的表達"],
                "exam_tips": "結合時代背景分析詩中意象的表現力與情感深度。"
            },
            {
                "篇名": "捕蛇者说",
                "author": "柳宗元",
                "era": "唐代",
                "excerpt": "夫以天下之無道，罕有以供小利。",
                "baihua": "因為天下不太平，很少有人願意為了小利而冒險。",
                "analysis": ["寓言式敘事","社會批判立場"],
                "exam_tips": "把握敘事者立場與寓意，注意細節描寫如何服務主旨。"
            },
            {
                "篇名": "论仁（节选）",
                "author": "孔子",
                "era": "春秋",
                "excerpt": "仁者，愛人。",
                "baihua": "有仁德的人，愛護他人。",
                "analysis": ["語錄體的簡潔性","倫理思想的表述"],
                "exam_tips": "可將孔子的倫理觀與現代道德問題結合論述。"
            }
        ]

        # 展示增强信息：标题按钮列
        for idx, it in enumerate(dse_12):
            if st.button(f"{idx+1}. {it['篇名']} — {it.get('作者', it.get('author',''))}", key=f"chi12_{idx}"):
                st.markdown(f"### {it['篇名']} — {it.get('作者', it.get('author',''))}")
                if 'excerpt' in it:
                    st.markdown("**原文节选：**")
                    st.write(it['excerpt'])
                if 'baihua' in it:
                    st.markdown("**白话译文：**")
                    st.write(it['baihua'])
                if 'analysis' in it:
                    st.markdown("**要点分析：**")
                    for a in it['analysis']:
                        st.write(f"- {a}")
                if 'exam_tips' in it:
                    st.markdown("**考试提示：**")
                    st.write(it['exam_tips'])
                st.markdown("---")

# ==========================================
# 🌏 公社科 (CSD)
# ==========================================
else:
    csd_features = [
        ("📖 概念查询", "csd_kw"),
        ("📝 时事分析", "csd_event"),
        ("📊 数据解读", "csd_data"),
        ("🗞️ 新闻速读", "csd_news"),
        ("🧩 观点论证训练", "csd_view"),
        ("📚 题库训练营", "csd_qbank"),
        ("📋 错题本管理", "csd_wrong"),
        ("🕒 历年真题演练", "csd_past"),
        ("🎯 知识点自测", "csd_quiz"),
        ("🧠 关键术语记忆卡", "csd_term"),
        ("🌏 国际视野拓展", "csd_world")
    ]
    st.markdown("#### 请选择功能：")
    cols = st.columns(3)
    for idx, (label, key) in enumerate(csd_features):
        if cols[idx % 3].button(label, key=f"btn_{key}"):
            st.session_state["csd_selected"] = key
    selected = st.session_state.get("csd_selected", "csd_kw")
    st.markdown("---")
    # 动态内容区
    if selected == "csd_kw":
        st.markdown("#### 公社科概念查询")
        kw = st.text_input("输入要查询的概念:", key="csd_kw_text")
        if st.button("AI 查询", key="csd_kw_btn"):
            prompt = f"请简明解释DSE公社科概念：{kw}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.info(res.text)
    elif selected == "csd_event":
        st.markdown("#### 时事分析")
        event = st.text_area("输入时事或社会热点:", key="csd_event_text")
        if st.button("AI 分析", key="csd_event_btn"):
            prompt = f"请用DSE公社科视角分析下列时事：{event}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.info(res.text)
    elif selected == "csd_data":
        st.markdown("#### 数据解读")
        data = st.text_area("输入数据描述或表格内容:", key="csd_data_text")
        if st.button("AI 解读", key="csd_data_btn"):
            prompt = f"请对下列数据进行解读和分析：{data}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.info(res.text)
    elif selected == "csd_news":
        st.markdown("#### 新闻速读")
        news = st.text_area("输入新闻内容:", key="csd_news_text")
        if st.button("AI 摘要", key="csd_news_btn"):
            prompt = f"请用简明扼要的语言总结下列新闻：{news}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.info(res.text)
    elif selected == "csd_view":
        st.markdown("#### 观点论证训练")
        view = st.text_area("输入你的观点:", key="csd_view_text")
        if st.button("AI 论证", key="csd_view_btn"):
            prompt = f"请对下列观点进行论证和完善：{view}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.info(res.text)
    elif selected == "csd_qbank":
        st.markdown("#### 公社科题库训练")
        sample_questions = [
            "简述全球化的影响。",
            "什么是可持续发展？",
            "举例说明社会分层。"
        ]
        q_idx = st.number_input("选择题号", min_value=0, max_value=len(sample_questions)-1, value=0, step=1, key="csd_qbank_idx")
        st.write(f"题目: {sample_questions[q_idx]}")
        user_ans = st.text_area("你的答案:", key="csd_qbank_ans")
        if st.button("提交答案", key="csd_qbank_submit"):
            prompt = f"请为下列DSE公社科题目评分并给出详细解析：{sample_questions[q_idx]}\n学生答案：{user_ans}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.success(res.text)
    elif selected == "csd_wrong":
        st.markdown("#### 公社科错题本管理")
        if 'csd_wrongbook' not in st.session_state:
            st.session_state.csd_wrongbook = []
        add_wrong = st.text_area("添加错题（描述或粘贴题目）:", key="csd_wrong_add")
        if st.button("添加到错题本", key="csd_wrong_add_btn"):
            if add_wrong:
                st.session_state.csd_wrongbook.append(add_wrong)
                st.success("已添加到错题本！")
        st.write("##### 我的错题本：")
        for i, q in enumerate(st.session_state.csd_wrongbook):
            st.write(f"{i+1}. {q}")
    elif selected == "csd_past":
        st.markdown("#### DSE 公社科历年真题演练 (示例)")
        st.write("2022 Q1: 简述香港社会的多元文化现象。")
        user_ans = st.text_area("你的答案:", key="csd_past_ans")
        if st.button("提交答案", key="csd_past_submit"):
            prompt = f"请为下列DSE历年真题评分并给出详细解析：简述香港社会的多元文化现象。\n学生答案：{user_ans}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.success(res.text)
    elif selected == "csd_quiz":
        st.markdown("#### 公社科知识点自测 (选择题)")
        quiz = {
            "全球化的主要特征是？": ["A. 经济一体化", "B. 文化单一", "C. 资源枯竭", "D. 贫富均等"],
            "可持续发展的核心是？": ["A. 只重经济", "B. 只重环境", "C. 协调发展", "D. 只重社会"]
        }
        q_list = list(quiz.keys())
        q_idx = st.number_input("选择题号", min_value=0, max_value=len(q_list)-1, value=0, step=1, key="csd_quiz_idx")
        st.write(q_list[q_idx])
        options = quiz[q_list[q_idx]]
        user_choice = st.radio("你的选择:", options, key="csd_quiz_choice")
        if st.button("提交自测", key="csd_quiz_submit"):
            answer = ["A. 经济一体化", "C. 协调发展"]
            if user_choice == answer[q_idx]:
                st.success("答对了！")
            else:
                st.error("答错了，继续努力！")
    elif selected == "csd_term":
        st.markdown("#### 关键术语记忆卡")
        term = st.text_input("输入术语:", key="csd_term_text")
        if st.button("AI 生成记忆卡", key="csd_term_btn"):
            prompt = f"请为术语'{term}'生成简明解释和记忆法。"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.info(res.text)
    elif selected == "csd_world":
        st.markdown("#### 国际视野拓展")
        topic = st.text_input("输入国际话题:", key="csd_world_text")
        if st.button("AI 拓展", key="csd_world_btn"):
            prompt = f"请用DSE公社科视角介绍下列国际话题：{topic}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.info(res.text)

# --- Chatbot ---
with st.expander("💬 AI 助手"):
    q = st.text_input("Ask anything:")
    if q: st.write(client.models.generate_content(model="gemini-2.0-flash", contents=q).text)


