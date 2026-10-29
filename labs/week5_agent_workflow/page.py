"""Week 5 page: the Mini Muse agent step (state, tools, bounded loop, approval).

Run alone:   streamlit run labs/week5_agent_workflow/page.py
In the site: streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Lets this page run on its own (streamlit run labs/<lab>/page.py) as well as inside app.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from labs.shared.ui import get_model_settings, page_layout, run_standalone


def render() -> None:
    main, panel = page_layout("Week 5 · Agent Workflow")
    from mini_muse.page import render_step  # the project's screens live with its code, in mini_muse/

    render_step(5, main, panel, get_model_settings())


if __name__ == "__main__":
    run_standalone(render, "Week 5 · Agent Workflow")
