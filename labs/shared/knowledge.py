"""Render each week's core concept straight from the knowledge_base/ folder.

The markdown in knowledge_base/week-NN-*/concepts*.md is the single source of
truth; this module just discovers those files and shows them in the app. A week
can have a main `concepts.md` plus extra `concepts-*.md` notes (e.g.
`concepts-benchmarks.md`), each listed as its own entry.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_BASE = ROOT / "knowledge_base"
ACRONYMS = {"Llm": "LLM", "Rag": "RAG", "Mcp": "MCP", "Api": "API", "Bfcl": "BFCL"}


def _titleize(text: str) -> str:
    """`context-engineering` -> `Context Engineering`, keeping known acronyms uppercase."""
    title = text.replace("-", " ").title()
    for word, fixed in ACRONYMS.items():
        title = title.replace(word, fixed)
    return title


def available_concepts() -> dict[str, Path]:
    """Map a sidebar label to each week's concept files, ordered by week number.

    Folders look like `week-06-evals`; `concepts.md` becomes `Week 6 · Evals` and
    an extra note like `concepts-benchmarks.md` becomes `Week 6 · Evals · Benchmarks`.
    The main concept is listed first. Adding a week or a note needs no code change.
    """
    concepts: dict[str, Path] = {}
    for folder in sorted(KNOWLEDGE_BASE.glob("week-*")):
        parts = folder.name.split("-", 2)  # ["week", "06", "evals"]
        number = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        topic = _titleize(parts[2]) if len(parts) > 2 else ""
        base = f"Week {number} · {topic}".strip(" ·")
        # Main concepts.md first, then the extra concepts-*.md notes alphabetically.
        files = sorted(folder.glob("concepts*.md"), key=lambda p: (p.stem != "concepts", p.stem))
        for path in files:
            if path.stem == "concepts":
                concepts[base] = path
            else:
                note = _titleize(path.stem.removeprefix("concepts-"))
                concepts[f"{base} · {note}"] = path
    return concepts


def render_concept(path: Path) -> None:
    """Show one week's concept markdown full width."""
    st.markdown(path.read_text(encoding="utf-8"))
    st.caption("Source: `knowledge_base/" + path.relative_to(KNOWLEDGE_BASE).as_posix()
               + "` · pick **— Hide —** in the sidebar to return to the labs.")
