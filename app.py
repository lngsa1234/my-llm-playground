"""Context Engineering Lab demos. Start with: streamlit run app.py."""

import streamlit as st

from core.week1 import render_week1
from core.week2 import render_week2

st.set_page_config(page_title="Agent Engineering Peer Learning", page_icon="🧭", layout="wide")
st.markdown(
    """
    <style>
        .block-container { padding-top: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("🧭 Agent Engineering Peer Learning")

week1, week2 = st.tabs(["Week 1", "Week 2"])
with week1:
    render_week1()
with week2:
    render_week2()
