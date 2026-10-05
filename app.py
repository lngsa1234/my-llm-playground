"""Context Engineering Lab demos. Start with: streamlit run app.py."""

import streamlit as st
from dotenv import load_dotenv

from core.week1 import render_week1
from core.week2 import render_week2
from core.week3 import render_week3

load_dotenv()

st.set_page_config(page_title="Agent Engineering Peer Learning", page_icon="🧭", layout="wide")
st.markdown(
    """
    <style>
        .block-container { padding-top: 2rem; }
        [data-testid="stSidebar"] {
            min-width: 200px;
            max-width: 200px;
        }
        [data-testid="stSidebar"] > div:first-child {
            width: 200px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("🧭 Agent Engineering Peer Learning")

with st.sidebar:
    st.header("Lab navigation")
    selected_week = st.radio("Choose a week", ["Week 1", "Week 2", "Week 3 · RAG"], label_visibility="collapsed")

if selected_week == "Week 1":
    render_week1()
elif selected_week == "Week 2":
    render_week2()
else:
    render_week3()
