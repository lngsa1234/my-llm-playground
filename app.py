"""Agent Engineering Peer Learning labs. Start with: streamlit run app.py

app.py only handles navigation. Each lab is a self-contained folder in labs/
with its own page.py, which can also run alone. Mini Muse, the assistant built
across all the weeks, is in mini_muse/. The shared settings panel is in
labs/shared/ui.py.
"""

import os
import sys
from pathlib import Path

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
from labs.shared.knowledge import available_concepts, render_concept  # noqa: E402
from labs.shared.quizzes import QUIZZES, render_quiz  # noqa: E402
from labs.week1_llm_api import page as week1  # noqa: E402
from labs.week2_context_engineering import page as week2  # noqa: E402
from labs.week3_rag import page as week3  # noqa: E402
from labs.week4_tool_calling import page as week4  # noqa: E402
from labs.week5_agent_workflow import page as week5  # noqa: E402
from labs.week6_agent_eval import page as week6  # noqa: E402
from labs.week7_production import page as week7  # noqa: E402
from mini_muse import page as mini_muse  # noqa: E402
from mini_muse.connectors import google_calendar  # noqa: E402

load_dotenv()

PAGES = {
    "Week 1 · Single API call": week1.render,
    "Week 2 · Context engineering": week2.render,
    "Week 3 · RAG": week3.render,
    "Week 4 · Tool calling": week4.render,
    "Week 5 · Agent workflow": week5.render,
    "Week 6 · Evaluation": week6.render,
    "Week 7 · Reliability": week7.render,
    "Week 8 · Demo Day": mini_muse.render,
}

st.set_page_config(page_title="Agent Engineering Peer Learning", page_icon="🧭", layout="wide")

# Finish a Google Calendar OAuth redirect the moment it returns to the app, on any page.
# Google sends the browser back to the site root in a fresh session, so complete the
# exchange here (not only inside the connector panel) and mark the connector connected.
# Each authorization code is processed once; handle_callback clears it on success.
_oauth_code = st.query_params.get("code")
if _oauth_code and st.session_state.get("_google_oauth_code") != _oauth_code:
    _oauth_status = google_calendar.handle_callback()
    if _oauth_status is not None:
        st.session_state["_google_oauth_code"] = _oauth_code
        st.session_state["connectors_calendar_status"] = _oauth_status
        if _oauth_status.ready:
            st.session_state["connectors_calendar_enabled"] = True
        st.toast(_oauth_status.detail, icon="✅" if _oauth_status.ready else "⚠️")

apply_page_style()
st.markdown(
    """
    <style>
        /* Keep each week's label on a single line in the sidebar. */
        [data-testid="stSidebar"] [role="radiogroup"] label p {
            font-size: 0.8rem;
            white-space: nowrap;
        }
        [data-testid="stSidebar"] .stButton > button {
            justify-content: flex-start;
            text-align: left;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

CONCEPTS = available_concepts()
KB_OFF = "— Hide —"
QUIZ_OFF = "— Hide —"
PROGRAM_GUIDE = Path(__file__).resolve().parent / "knowledge_base" / "program-guide.md"


def _show_labs() -> None:
    """Picking a week in the lab nav leaves the Knowledge Base view."""
    st.session_state.nav_concept = KB_OFF
    st.session_state.nav_quiz = QUIZ_OFF
    st.session_state.show_program_guide = False


def _show_concept() -> None:
    """Opening Knowledge Base hides the quiz view."""
    st.session_state.nav_quiz = QUIZ_OFF
    st.session_state.show_program_guide = False


def _show_quiz() -> None:
    """Opening a quiz hides the Knowledge Base view."""
    st.session_state.nav_concept = KB_OFF
    st.session_state.show_program_guide = False


def _show_guide() -> None:
    """Opening the Program Guide hides other document views."""
    st.session_state.nav_concept = KB_OFF
    st.session_state.nav_quiz = QUIZ_OFF
    st.session_state.show_program_guide = True


with st.sidebar:
    st.subheader("🧭 Agent Engineering Peer Learning")
    selected = st.radio("Choose a week", list(PAGES), label_visibility="collapsed",
                        key="nav_week", on_change=_show_labs)
    st.divider()
    st.button("🗺️ Program Guide", width="stretch", on_click=_show_guide)
    with st.expander("📚 Knowledge Base"):
        concept = st.radio("Concept", [KB_OFF, *CONCEPTS], label_visibility="collapsed",
                           key="nav_concept", on_change=_show_concept)
    with st.expander("🧠 Quizzes"):
        quiz = st.radio("Quiz", [QUIZ_OFF, *QUIZZES], label_visibility="collapsed",
                        key="nav_quiz", on_change=_show_quiz)
    st.divider()
    api_key_notice()

if st.session_state.get("show_program_guide", False):
    st.markdown(PROGRAM_GUIDE.read_text(encoding="utf-8"))
    st.caption("Source: `knowledge_base/program-guide.md` · pick **— Hide —** in the sidebar to return to the labs.")
elif quiz != QUIZ_OFF:
    render_quiz(quiz)
elif concept != KB_OFF:
    render_concept(CONCEPTS[concept])
else:
    PAGES[selected]()
