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
from labs.shared.knowledge import available_concepts, render_concept, render_document  # noqa: E402
from labs.shared.quizzes import QUIZZES, render_quiz  # noqa: E402
from labs.week1_llm_api import page as week1  # noqa: E402
from labs.week2_context_engineering import page as week2  # noqa: E402
from labs.week3_rag import page as week3  # noqa: E402
from labs.week4_tool_calling import page as week4  # noqa: E402
from labs.week5_agent_workflow import page as week5  # noqa: E402
from labs.week6_agent_eval import page as week6  # noqa: E402
from labs.week7_production import page as week7  # noqa: E402
from mini_muse import page as mini_muse  # noqa: E402
from mini_muse.connectors import CONNECTORS  # noqa: E402

load_dotenv()

PAGES = {
    "Week 1 · Your agent can answer": week1.render,
    "Week 2 · Your agent can remember": week2.render,
    "Week 3 · Your agent can learn": week3.render,
    "Week 4 · Your agent can act": week4.render,
    "Week 5 · Your agent can execute": week5.render,
    "Week 6 · Your agent can be tested": week6.render,
    "Week 7 · Your agent becomes reliable": week7.render,
    "Week 8 · Your agent is ready to showcase": mini_muse.render,
}

st.set_page_config(page_title="Agent Engineering Peer Learning", page_icon="🧭", layout="wide")

# Finish a Google OAuth redirect the moment it returns to the app, on any page. Google
# sends the browser back to the site root in a fresh session, so complete the exchange
# here (not only inside the connector panel) and mark the connector connected. Calendar
# and Gmail share one redirect URL, so each connector's handle_callback returns None
# unless the signed state is tagged for it; the first match consumes the code.
_oauth_code = st.query_params.get("code")
if _oauth_code and st.session_state.get("_google_oauth_code") != _oauth_code:
    for _conn in CONNECTORS:
        _handle = getattr(_conn, "handle_callback", None)
        if _handle is None:
            continue
        _oauth_status = _handle({})
        if _oauth_status is None:
            continue
        st.session_state["_google_oauth_code"] = _oauth_code
        st.session_state[f"connectors_{_conn.name}_status"] = _oauth_status
        if _oauth_status.ready:
            st.session_state[f"connectors_{_conn.name}_enabled"] = True
        st.toast(_oauth_status.detail, icon="✅" if _oauth_status.ready else "⚠️")
        break

apply_page_style()
st.markdown(
    """
    <style>
        /* Week labels can wrap: they now describe what the agent can do, not a short topic. */
        [data-testid="stSidebar"] [role="radiogroup"] label p {
            font-size: 0.8rem;
            line-height: 1.3;
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
    render_document(PROGRAM_GUIDE, "Source: `knowledge_base/program-guide.md` · pick **— Hide —** in the sidebar to return to the labs.")
elif quiz != QUIZ_OFF:
    render_quiz(quiz)
elif concept != KB_OFF:
    render_concept(CONCEPTS[concept])
else:
    PAGES[selected]()
