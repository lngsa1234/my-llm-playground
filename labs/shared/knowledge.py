"""Render each week's core concept straight from the knowledge_base/ folder.

The markdown in knowledge_base/week-NN-*/concepts*.md is the single source of
truth; this module just discovers those files and shows them in the app. A week
can have a main `concepts.md` plus extra `concepts-*.md` notes (e.g.
`concepts-benchmarks.md`), each listed as its own entry.
"""

from __future__ import annotations

import html
import re
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
    # The glossary holds short definitions for every week, so it is listed first.
    glossary = KNOWLEDGE_BASE / "glossary.md"
    if glossary.exists():
        concepts["Glossary"] = glossary
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


TOC_CSS = """
<style>
    /* The right-hand outline column stays in view while the page scrolls. */
    [data-testid="stColumn"]:has(.st-key-kb_toc) {
        position: sticky;
        top: 4.5rem;
        align-self: flex-start;
    }
    /* The outline scrolls on its own only when it is taller than the window. */
    .kb-toc {
        max-height: calc(100vh - 6rem);
        overflow-y: auto;
        padding-right: 0.25rem;
    }
    .kb-toc ul { list-style: none; margin: 0; padding: 0 0 0 0.75rem;
                 border-left: 1px solid var(--st-border-color, #D6DEE6); }
    .kb-toc li { margin: 0 0 0.35rem 0; padding: 0; line-height: 1.3; }
    .kb-toc li.kb-toc-h3 { padding-left: 0.85rem; font-size: 0.8rem; }
    .kb-toc a { font-size: 0.875rem; text-decoration: none; color: inherit; opacity: 0.8; }
    .kb-toc li.kb-toc-h3 a { font-size: 0.8rem; opacity: 0.7; }
    .kb-toc a:hover { opacity: 1; color: var(--st-primary-color, #1F5E8C); }
    /* A table cell that lists one item per line (<br>) keeps each item on one line. */
    [data-testid="stMarkdownContainer"] td:has(br) { white-space: nowrap; }
    /* Columns stack on narrow screens; the outline would end up below the page, so hide it. */
    @media (max-width: 768px) {
        [data-testid="stColumn"]:has(.st-key-kb_toc) { display: none; }
    }
</style>
"""

_FENCE = re.compile(r"^\s*(```|~~~)")
_HEADING = re.compile(r"^(#{2,3})\s+(.+?)\s*#*\s*$")


def _plain(text: str) -> str:
    """Strip inline markdown (links, code, emphasis) so a heading reads as plain text."""
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[`*_]", "", text)
    return text.strip()


def heading_anchor(text: str) -> str:
    """The id Streamlit gives a markdown heading, so outline links land on it.

    Streamlit lowercases the heading text, drops apostrophes ("can't" -> "cant")
    and joins the remaining runs of letters and digits with single hyphens;
    everything else (punctuation, ·, —, ?) is dropped.
    """
    words = re.findall(r"[^\W_]+", re.sub(r"['’]", "", _plain(text).lower()))
    return "-".join(words)


def headings(content: str) -> list[tuple[int, str, str]]:
    """Return (level, title, anchor) for each ## and ### heading outside code blocks."""
    found: list[tuple[int, str, str]] = []
    in_fence = False
    for line in content.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _HEADING.match(line)
        if match:
            title = _plain(match.group(2))
            found.append((len(match.group(1)), title, heading_anchor(match.group(2))))
    return found


def _render_toc(content: str) -> None:
    """The section outline shown in the right-hand column."""
    items = headings(content)
    if not items:
        return
    links = "".join(
        f'<li class="kb-toc-h{level}"><a href="#{anchor}">{html.escape(title)}</a></li>'
        for level, title, anchor in items
    )
    with st.container(key="kb_toc"):
        st.markdown(
            f'<nav class="kb-toc"><ul>{links}</ul></nav>',
            unsafe_allow_html=True,
        )


def render_document(path: Path, caption: str) -> None:
    """Show a knowledge-base page with its table of contents in a right-hand column."""
    content = path.read_text(encoding="utf-8")
    st.markdown(TOC_CSS, unsafe_allow_html=True)
    main, toc = st.columns([3, 1], gap="large")
    with main:
        _render_body(content)
        st.caption(caption)
    with toc:
        _render_toc(content)


def render_concept(path: Path) -> None:
    """Show one week's concept markdown with its outline on the right."""
    render_document(
        path,
        "Source: `knowledge_base/" + path.relative_to(KNOWLEDGE_BASE).as_posix()
        + "` · pick **— Hide —** in the sidebar to return to the labs.",
    )


def _render_body(content: str) -> None:
    """Render markdown, drawing ``graphviz`` fenced blocks as native diagrams.

    A ``graphviz`` fenced block is deliberately rendered as a chart rather than
    as source code.  That keeps the knowledge-base export readable in the app
    without making the markdown depend on a private Notion attachment.
    """
    pieces = re.split(r"```graphviz\s*\n(.*?)```", content, flags=re.DOTALL)
    for index, piece in enumerate(pieces):
        if index % 2:
            # A diagram may opt into a smaller fixed display width and centered
            # placement with leading Graphviz comments.
            width_match = re.match(r"\s*//\s*width:\s*(\d+)\s*\n", piece)
            width = int(width_match.group(1)) if width_match else "content"
            dot = piece[width_match.end():] if width_match else piece
            centered = dot.startswith("// center\n")
            if centered:
                dot = dot.removeprefix("// center\n")
                with st.columns(3)[1]:
                    st.graphviz_chart(dot, width=width)
            else:
                st.graphviz_chart(dot, width=width)
        elif piece.strip():
            # The knowledge base is our own trusted markdown; allowing HTML lets a
            # table cell use <br> to put each item on its own line.
            st.markdown(piece, unsafe_allow_html=True)
