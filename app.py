import streamlit as st
import os
from google.genai import Client

# 页面配置
st.set_page_config(page_title="DSE AI 精批助手", layout="wide")

# --- 关键修改：从 Streamlit Secrets 读取 API Key ---
# 这会让代码自动去云端后台找你填写的那个 GEMINI_API_KEY
if "GEMINI_API_KEY" in st.secrets:
    api_key_val = st.secrets["GEMINI_API_KEY"]
else:
    # 如果云端没找到，再看本地环境变量（兼容本地测试）
    api_key_val = os.getenv("GEMINI_API_KEY", "")

# 初始化客户端
try:
    client = Client(api_key=api_key_val)
except Exception as e:
    st.error("初始化 Gemini 失败，请检查 API Key 配置")
