"""Week 3 · Knowledge: answer questions from your own notes (RAG).

The model has never seen your notes, so Mini Muse looks them up first:

    notes/*.md → split into sections (chunks) → index
    question  → search the index → top-K sections → put them in the prompt → grounded answer

Three ways to search, so you can compare them:
    keyword    BM25: matches the exact words (offline, free)
    semantic   embeddings: matches meaning, even with different words (needs the API)
    hybrid     both, merged by reciprocal-rank fusion (the Week 3 takeaway)

Week 8 turns `search` into the agent's `search_notes` tool.

Try it:  python -m mini_muse.week3_knowledge "What did Jordan say about the offsite budget?"
"""

from __future__ import annotations

import math
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from mini_muse.world import NOTES_DIR

MODES = ["keyword", "semantic", "hybrid"]
NOT_FOUND = "I don't see that in your notes."


@dataclass
class Chunk:
    note: str      # note title, e.g. "Team offsite planning"
    section: str   # section heading, e.g. "Budget"
    text: str
    file: str

    @property
    def label(self) -> str:
        return f"{self.note} › {self.section}"


@dataclass
class NotesIndex:
    chunks: list[Chunk]
    vectors: list[list[float]] = field(default_factory=list)  # one per chunk when semantic search is on

    @property
    def semantic(self) -> bool:
        return bool(self.vectors)


def load_chunks_from_texts(notes: list[tuple[str, str]]) -> list[Chunk]:
    """Split uploaded or pasted Markdown/text notes into one chunk per `## ` section."""
    chunks = []
    for filename, content in notes:
        lines = content.splitlines()
        title = next((line[2:].strip() for line in lines if line.startswith("# ")), Path(filename).stem)
        section, body = "Overview", []

        def flush():
            text = "\n".join(body).strip()
            if text:
                chunks.append(Chunk(title, section, text, filename))

        for line in lines:
            if line.startswith("## "):
                flush()
                section, body = line[3:].strip(), []
            elif not line.startswith("# "):
                body.append(line)
        flush()
    return chunks


def load_chunks(directory: Path = NOTES_DIR) -> list[Chunk]:
    """Load the bundled command-line sample notes."""
    notes = [(path.name, path.read_text(encoding="utf-8")) for path in sorted(directory.glob("*.md"))]
    return load_chunks_from_texts(notes)


def build_index(llm=None, directory: Path = NOTES_DIR, chunks: list[Chunk] | None = None) -> NotesIndex:
    """Keyword search works without a model. Pass `llm` to embed chunks for semantic search."""
    chunks = chunks if chunks is not None else load_chunks(directory)
    vectors = llm.embed([f"{c.label}\n{c.text}" for c in chunks]) if llm is not None else []
    return NotesIndex(chunks, vectors)


def _terms(text: str) -> list[str]:
    return re.findall(r"[a-z0-9$]+", text.lower())


def keyword_scores(index: NotesIndex, query: str, k1: float = 1.5, b: float = 0.75) -> list[float]:
    docs = [_terms(f"{c.label} {c.text}") for c in index.chunks]
    avg = sum(map(len, docs)) / len(docs)
    df = Counter(term for doc in docs for term in set(doc))
    scores = []
    for doc in docs:
        counts, score = Counter(doc), 0.0
        for term in set(_terms(query)):
            if term in counts:
                idf = math.log(1 + (len(docs) - df[term] + 0.5) / (df[term] + 0.5))
                tf = counts[term]
                score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(doc) / avg))
        scores.append(score)
    return scores


def semantic_scores(index: NotesIndex, llm, query: str) -> list[float]:
    q = llm.embed([query])[0]
    q_norm = math.sqrt(sum(x * x for x in q)) or 1.0
    scores = []
    for v in index.vectors:
        v_norm = math.sqrt(sum(x * x for x in v)) or 1.0
        scores.append(sum(a * b for a, b in zip(q, v)) / (q_norm * v_norm))
    return scores


def _ranking(scores: list[float]) -> list[int]:
    return sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)


def search(index: NotesIndex, query: str, k: int = 3, mode: str = "keyword", llm=None) -> list[dict]:
    """Top-k sections for the query. Semantic and hybrid need an index built with `llm`."""
    if mode != "keyword" and not (index.semantic and llm is not None):
        mode = "keyword"
    keyword = keyword_scores(index, query)
    if mode == "keyword":
        order, shown = [i for i in _ranking(keyword) if keyword[i] > 0], keyword
    else:
        semantic = semantic_scores(index, llm, query)
        if mode == "semantic":
            order, shown = _ranking(semantic), semantic
        else:  # reciprocal-rank fusion: reward chunks that rank well in either list
            fused = [0.0] * len(index.chunks)
            for ranking in (_ranking(semantic), [i for i in _ranking(keyword) if keyword[i] > 0]):
                for rank, i in enumerate(ranking):
                    fused[i] += 1 / (60 + rank + 1)
            order, shown = _ranking(fused), fused
    return [{"rank": r + 1, "source": index.chunks[i].label, "file": index.chunks[i].file,
             "score": round(shown[i], 4), "text": index.chunks[i].text, "mode": mode}
            for r, i in enumerate(order[:k])]


def grounded_prompt(question: str, results: list[dict]) -> list[dict]:
    sources = "\n\n".join(f"[{r['source']}]\n{r['text']}" for r in results) or "(no matching notes)"
    return [
        {"role": "system", "content": (
            "You are Mini Muse. Answer only from the user's notes below. Cite the source in "
            f"brackets, like [Team offsite planning › Budget]. If the notes do not contain the "
            f"answer, reply exactly: \"{NOT_FOUND}\"\n\nNotes:\n{sources}")},
        {"role": "user", "content": question},
    ]


def answer(llm, index: NotesIndex, question: str, k: int = 3, mode: str = "keyword") -> dict:
    results = search(index, question, k, mode, llm)
    messages = grounded_prompt(question, results)
    return {"answer": llm.chat(messages).content, "results": results, "messages": messages}


if __name__ == "__main__":
    from mini_muse.llm import cli_llm

    model = cli_llm()
    question = " ".join(sys.argv[1:]) or "What did Jordan say about the offsite budget?"
    result = answer(model, build_index(model), question, mode="hybrid")
    for r in result["results"]:
        print(f"  #{r['rank']} {r['source']}  ({r['mode']} score {r['score']})")
    print(f"\n{result['answer']}")
