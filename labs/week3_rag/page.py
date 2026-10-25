"""Week 3 page: retrieval-augmented generation (RAG). Answer from documents the model has never seen.

Run alone:   streamlit run labs/week3_rag/page.py
In the site: streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Lets this page run on its own (streamlit run labs/<lab>/page.py) as well as inside app.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from labs.shared.settings import ModelSettings
from labs.shared.ui import (can_run, example_text_area, lab_parameters, metric_row, mini_muse_part, model_settings,
                            page_layout, run_standalone, show_error, usage_line)
from labs.week3_rag import evaluation as ev
from labs.week3_rag.rag import build_index, chunk_documents, generate_with_rag, generate_without_rag, load_documents, retrieve

HOW_IT_WORKS = """
A model only knows what it was trained on and what you put in its context. **RAG** finds the relevant passages in your own documents and puts them in the context, so the answer can be grounded in them.

1. **Chunk:** each document is split into short, overlapping pieces (Chunk size and Chunk overlap in Lab parameters).
2. **Index:** every chunk is turned into an embedding (a list of numbers that captures meaning) and stored for search.
3. **Retrieve:** the question is matched against the chunks by meaning and by keywords, and the best **Top-K** are kept.
4. **Answer:** those chunks go into the context, and the model answers from them, citing the source files. If nothing relevant was found, it says so instead of guessing.

The **Ask** tab compares the same question with and without RAG. **Documents & chunks** shows how chunking cuts a document. **Benchmark** measures retrieval over many questions at once.
"""


def _evidence(item: dict) -> set[str]:
    value = item.get("evidence") or []
    return {value} if isinstance(value, str) else set(value)


def render() -> None:
    main, panel = page_layout("Week 3 · Retrieval-augmented generation")
    if mini_muse_part(main, panel, 3, embedding=True,
                      caption="Give the model passages from your own documents, and compare its answer with and without them.",
                      how_it_works=HOW_IT_WORKS):
        return
    settings = model_settings(panel, embedding=True)
    names = list(ev.DATASETS)
    with lab_parameters(panel):
        dataset_name = st.selectbox("Documents", names, index=len(names) - 1, key="week3_dataset",
                                    help="NovaTech: 10 short company policies, one document per answer. "
                                         "HotpotQA: 198 Wikipedia articles, two documents per answer.")
        chunk_size = int(st.slider("Chunk size (characters)", 100, 1200, 200, 50, key="week3_chunk_size"))
        overlap = int(st.slider("Chunk overlap (characters)", 0, 250, 50, 10, key="week3_overlap"))
        if overlap >= chunk_size:
            st.error("Overlap must be smaller than chunk size.")
            overlap = max(0, chunk_size - 1)
        top_k = int(st.slider("Top-K chunks", 1, 8, 3, key="week3_top_k", help="How many chunks go into the context."))
        with st.expander("Advanced"):
            threshold = float(st.slider("Evidence threshold", 0.0, 1.0, 0.10, 0.01, key="week3_threshold_v2",
                                        help="Below this similarity the app declines to answer, unless keyword or "
                                             "title matches support the question."))
            st.caption(ev.LOADED_BUILD_STAMP)

    dataset = ev.DATASETS[dataset_name]
    params = {"dataset": dataset, "chunk_size": chunk_size, "overlap": overlap, "top_k": top_k, "threshold": threshold}
    with main:
        ask, documents, benchmark = st.tabs(["Ask", "Documents & chunks", "Benchmark"])
        with ask:
            _render_ask(settings, **params)
        with documents:
            _render_documents(dataset, chunk_size, overlap)
        with benchmark:
            _render_benchmark(settings, **params)


def _get_index(knowledge_base: Path, chunk_size: int, overlap: int, embedding_model: str):
    """Build the index once per (documents, chunking, embedding model) and keep it in the session."""
    key = (str(knowledge_base), chunk_size, overlap, embedding_model)
    if st.session_state.get("week3_index_key") != key:
        with st.spinner("Chunking and embedding the documents (once per setting)…"):
            st.session_state.week3_index = build_index(knowledge_base, chunk_size, overlap, embedding_model)
            st.session_state.week3_index_key = key
    return st.session_state.week3_index


def _render_ask(settings: ModelSettings, dataset: dict, chunk_size: int, overlap: int, top_k: int, threshold: float) -> None:
    questions = ev.load_questions(dataset["benchmark"])
    # Benchmark questions first: they come with an expected answer and the documents that hold it.
    examples = [q["question"] for q in questions][:8]
    if dataset["default_question"] not in examples:
        examples.append(dataset["default_question"])
    key = "week3_" + Path(dataset["knowledge_base"]).name
    question = example_text_area("Question", examples, key, height=70)

    if st.button("Ask with and without RAG", type="primary", key="week3_run") and can_run(settings, question):
        stage = "Answer without RAG"
        try:
            with st.spinner("Asking the model without documents…"):
                plain = generate_without_rag(settings.model, question)
            stage = "Building the index"
            index = _get_index(dataset["knowledge_base"], chunk_size, overlap, settings.embedding_model)
            stage = "Retrieval"
            results, latency, embed_tokens = retrieve(index, question, top_k)
            stage = "Answer with RAG"
            with st.spinner("Asking the model with the retrieved chunks…"):
                grounded = generate_with_rag(settings.model, question, results, threshold)
            st.session_state.week3_ask = {"question": question, "dataset": dataset["knowledge_base"], "plain": plain,
                                          "rag": grounded, "results": results, "latency": latency,
                                          "pipeline": ev.RETRIEVAL_PIPELINE_VERSION}
        except Exception as exc:  # noqa: BLE001
            show_error(stage, exc)

    saved = st.session_state.get("week3_ask")
    if not saved or saved["question"] != question or saved["dataset"] != dataset["knowledge_base"] \
            or saved.get("pipeline") != ev.RETRIEVAL_PIPELINE_VERSION:
        st.caption("Ask a question to compare the two answers and see which chunks were retrieved.")
        return

    item = next((q for q in questions if q["question"] == question), None)
    gold = _evidence(item) if item else set()

    without, with_rag = st.columns(2, gap="large")
    with without, st.container(border=True):
        st.markdown("**Without RAG**")
        st.markdown(saved["plain"]["text"] or "_No text returned._")
        p = saved["plain"]
        usage_line(p["input_tokens"], p["output_tokens"], p["latency_seconds"], settings.cost(p["input_tokens"], p["output_tokens"]))
    with with_rag, st.container(border=True):
        st.markdown("**With RAG**")
        r = saved["rag"]
        st.markdown(r["text"] or "_No text returned._")
        usage_line(r.get("input_tokens", 0), r.get("output_tokens", 0), r.get("latency_seconds"),
                   settings.cost(r.get("input_tokens", 0), r.get("output_tokens", 0)))
    if item:
        st.caption(f"Expected answer: **{item['expected_answer']}**")

    results = saved["results"]
    with st.container(border=True):
        found = {c["source"] for c in results} & gold
        st.markdown("**What the model sees with RAG**")
        st.caption(f"{len(results)} chunks retrieved in {saved['latency'] * 1000:.0f} ms"
                   + (f" · {len(found)} of {len(gold)} ⭐ documents that hold the answer" if gold else ""))
        for rank, c in enumerate(results, start=1):
            star = " ⭐" if c["source"] in gold else ""
            with st.expander(f"#{rank} · {c['source']} · chunk {c['chunk_number']} · similarity {c['score']:.2f}{star}",
                             expanded=rank == 1):
                st.code(c["text"], language=None, wrap_lines=True)
        if gold:
            st.caption("⭐ comes from a document that holds the answer, according to the benchmark.")
        if r.get("prompt"):
            with st.expander("The full prompt sent with RAG"):
                st.code(r["prompt"], language=None, wrap_lines=True)
        with st.expander("Retrieval details"):
            st.caption(f"Decision: {r.get('gate', 'not recorded')}")
            st.dataframe([{"#": rank, "Source": c["source"], "Chunk": c["chunk_number"],
                           "Found by": c.get("retrieval_method", "meaning"), "Similarity": f"{c['score']:.3f}",
                           "Keyword (BM25) score": f"{c.get('lexical_score', 0.0):.3f}"}
                          for rank, c in enumerate(results, start=1)], width="stretch", hide_index=True)


def _render_documents(dataset: dict, chunk_size: int, overlap: int) -> None:
    documents = load_documents(dataset["knowledge_base"])
    chunks = chunk_documents(documents, chunk_size, overlap)
    st.caption(f"{dataset['description']} With the current settings they make {len(chunks):,} chunks.")
    source = st.selectbox("Document", [d.source for d in documents], key="week3_document")
    document = next(d for d in documents if d.source == source)
    original, cut = st.columns(2, gap="large")
    with original, st.container(border=True):
        st.markdown(f"**Original** · {len(document.text):,} characters")
        st.code(document.text, language=None, wrap_lines=True, height=460)
    with cut, st.container(border=True):
        own = [c for c in chunks if c.source == source]
        st.markdown(f"**Chunks** · {len(own)} of up to {chunk_size} characters, overlapping by {overlap}")
        for chunk in own:
            st.code(chunk.text, language=None, wrap_lines=True)


def _render_benchmark(settings: ModelSettings, dataset: dict, chunk_size: int, overlap: int, top_k: int, threshold: float) -> None:
    questions = ev.load_questions(dataset["benchmark"])
    st.caption(f"Run all {len(questions)} benchmark questions. **Evidence recall@{top_k}** counts a question as found when "
               f"every document that holds its answer is among the top {top_k} chunks. Change chunking or Top-K and "
               "run again to compare.")
    generate = st.checkbox("Also generate and score answers (one model call per question)", key="week3_benchmark_full")
    if st.button("Run benchmark", type="primary", key="week3_benchmark_run") and can_run(settings):
        try:
            index = _get_index(dataset["knowledge_base"], chunk_size, overlap, settings.embedding_model)
            bar = st.progress(0, text="Retrieving…")
            st.session_state.week3_benchmark_rows = ev.run_rag_benchmark(
                index, questions, settings.model, top_k, threshold, generate,
                progress=lambda done, total: bar.progress(done / total, text=f"{done} of {total} questions"))
            bar.empty()
        except Exception as exc:  # noqa: BLE001
            show_error("Benchmark", exc)
    rows = st.session_state.get("week3_benchmark_rows")
    if not rows:
        st.caption("Run the benchmark to see recall and, optionally, answer scores.")
        return
    summary = ev.summarize_benchmark(rows)
    with st.container(border=True):
        metric_row({
            f"Evidence recall@{top_k}": f"{summary['evidence_recall']:.0%}",
            "Exact match": f"{summary['exact_match']:.0%}" if summary["exact_match"] is not None else "—",
            "Token F1": f"{summary['mean_f1']:.0%}" if summary["mean_f1"] is not None else "—",
        })
        st.dataframe(rows, width="stretch", hide_index=True)
        st.caption("Exact match and token F1 compare each answer with the expected one; they appear when answers are "
                   "generated. Evidence is judged per document, so any chunk of the right document counts.")


if __name__ == "__main__":
    run_standalone(render, "Week 3 · Retrieval-augmented generation")
