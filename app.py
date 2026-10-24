"""Agent Engineering Peer Learning labs. Start with: streamlit run app.py

app.py only handles navigation. Each lab is a self-contained folder in labs/
with its own page.py, which can also run alone. The shared settings panel is
in labs/shared/ui.py.
"""

import os
import sys

import streamlit as st
from dotenv import load_dotenv

# A long-running Streamlit server (e.g. Streamlit Cloud) keeps modules from the
# previous deploy in memory. If files were moved or renamed (core/week1.py became
# core/week1/), those stale modules break the new imports. Drop any of our modules
# whose source file no longer exists so they are re-imported from the new layout.
for _name, _module in list(sys.modules.items()):
    if _name.split(".")[0] in {"core", "ui", "labs"}:
        _file = getattr(_module, "__file__", None)
        if _file and not os.path.exists(_file):
            del sys.modules[_name]

from labs.shared.ui import apply_page_style  # noqa: E402
from labs.week1_llm_api import page as week1  # noqa: E402
from labs.week2_context_engineering import page as week2  # noqa: E402
from labs.week3_rag import page as week3  # noqa: E402
from labs.week4_tool_calling import page as week4  # noqa: E402
from labs.week6_agent_eval import page as week6  # noqa: E402

load_dotenv()

PAGES = {
    "Week 1 · Single API Call": week1.render,
    "Week 2 · Context Engineering": week2.render,
    "Week 3 · RAG": week3.render,
    "Week 4 · Weather Assistant": week4.render,
    "Week 6 · Agent Evaluation": week6.render,
}

st.set_page_config(page_title="Agent Engineering Peer Learning", page_icon="🧭", layout="wide")
apply_page_style()

with st.sidebar:
    st.subheader("🧭 Agent Engineering Peer Learning")
    selected = st.radio("Choose a week", list(PAGES), label_visibility="collapsed", key="nav_week")
    st.divider()

PAGES[selected]()
