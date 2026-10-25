"""Agent Engineering Peer Learning labs. Start with: streamlit run app.py

app.py only handles navigation. Each lab is a self-contained folder in labs/
with its own page.py, which can also run alone. Mini Muse, the assistant built
across all the weeks, is in mini_muse/. The shared settings panel is in
labs/shared/ui.py.
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
    if _name.split(".")[0] in {"core", "ui", "labs", "mini_muse"}:
        _file = getattr(_module, "__file__", None)
        if _file and not os.path.exists(_file):
            del sys.modules[_name]

from labs.shared.ui import api_key_notice, apply_page_style  # noqa: E402
from labs.week1_llm_api import page as week1  # noqa: E402
from labs.week2_context_engineering import page as week2  # noqa: E402
from labs.week3_rag import page as week3  # noqa: E402
from labs.week4_tool_calling import page as week4  # noqa: E402
from labs.week5_agent_workflow import page as week5  # noqa: E402
from labs.week6_agent_eval import page as week6  # noqa: E402
from labs.week7_production import page as week7  # noqa: E402
from mini_muse import page as mini_muse  # noqa: E402

load_dotenv()

PAGES = {
    "Week 1 · Single API call": week1.render,
    "Week 2 · Context engineering": week2.render,
    "Week 3 · RAG": week3.render,
    "Week 4 · Tool calling": week4.render,
    "Week 5 · Agent workflow": week5.render,
    "Week 6 · Evaluation": week6.render,
    "Week 7 · Reliability": week7.render,
    "Mini Muse · all weeks": mini_muse.render,
}

st.set_page_config(page_title="Agent Engineering Peer Learning", page_icon="🧭", layout="wide")
apply_page_style()

with st.sidebar:
    st.subheader("🧭 Agent Engineering Peer Learning")
    selected = st.radio("Choose a week", list(PAGES), label_visibility="collapsed", key="nav_week")
    st.divider()
    api_key_notice()

PAGES[selected]()
