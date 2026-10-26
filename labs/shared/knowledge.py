"""Render each week's core concept straight from the knowledge_base/ folder.

The markdown in knowledge_base/week-NN-*/concepts.md is the single source of
truth; this module just discovers those files and shows them in the app.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_BASE = ROOT / "knowledge_base"


def available_concepts() -> dict[str, Path]:
    """Map a sidebar label to each week's concepts.md, ordered by week number.

    Folders look like `week-06-evals`; the label becomes `Week 6 · Evals`. Only
    weeks that actually have a concepts.md appear, so adding a new week needs no
    code change here.
    """
    concepts: dict[str, Path] = {}
    for folder in sorted(KNOWLEDGE_BASE.glob("week-*")):
        path = folder / "concepts.md"
        if not path.exists():
            continue
        parts = folder.name.split("-", 2)  # ["week", "06", "evals"]
        number = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        topic = parts[2].replace("-", " ").title() if len(parts) > 2 else ""
        for word, fixed in {"Llm": "LLM", "Rag": "RAG", "Mcp": "MCP", "Api": "API"}.items():
            topic = topic.replace(word, fixed)
        concepts[f"Week {number} · {topic}".strip(" ·")] = path
    return concepts


def render_concept(path: Path) -> None:
    """Show one week's concept markdown full width."""
    st.markdown(path.read_text(encoding="utf-8"))
    st.caption("Source: `knowledge_base/" + path.relative_to(KNOWLEDGE_BASE).as_posix()
               + "` · pick **— Hide —** in the sidebar to return to the labs.")
