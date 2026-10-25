"""Week 3 page: build and evaluate a RAG system.

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
from labs.week3_rag import evaluation as ev
from labs.week3_rag.rag import (
    approximate_tokens,
    build_context,
    build_index,
    chunk_documents,
    generate_with_rag,
    generate_without_rag,
    load_documents,
    retrieve,
)
from labs.shared.ui import mini_muse_part, can_run, lab_parameters, metric_row, model_settings, page_layout, show_error, run_standalone

HOW_IT_WORKS = """
1. **Load and chunk** — Markdown files from this lab's `documents/` folder are split into overlapping chunks with source and chunk-number metadata.
2. **Build two retrieval signals** — Every chunk gets an embedding for semantic search, and token frequencies for BM25 keyword search.
3. **Rank the question** — The question is embedded, compared with chunks in FAISS, and combined with BM25 rankings through reciprocal-rank fusion (RRF).
4. **Follow evidence links** — If a top chunk names another document's title, up to three chunks from that document are added for a grounded second hop.
5. **Construct the context** — The selected chunks, with source filenames and chunk numbers, become the context sent to the answer model.
6. **Gate and answer** — The app answers only when dense, keyword or title-linked evidence supports the question, and cites the source files. Otherwise it abstains.
7. **Inspect and evaluate** — Retrieved chunks, ranks, scores, the augmented prompt and benchmark Evidence Recall@K are all visible.
"""


def render() -> None:
    main, panel = page_layout("Week 3 · Build and Evaluate a RAG System")
    if mini_muse_part(main, panel, 3, embedding=True,
                      caption="Documents → chunks → embeddings → FAISS search → grounded answer + sources → evidence evaluation",
                      how_it_works=HOW_IT_WORKS):
        return
    settings = model_settings(panel, max_tokens=False, prices=False, embedding=True)
    with lab_parameters(panel):
        dataset_name = st.selectbox("Dataset", list(ev.DATASETS), key="week3_dataset")
        chunk_size = int(st.slider("Chunk size (characters)", 100, 1200, 200, 50, key="week3_chunk_size"))
        overlap = int(st.slider("Chunk overlap (characters)", 0, 250, 50, 10, key="week3_overlap"))
        if overlap >= chunk_size:
            st.error("Overlap must be smaller than chunk size.")
            overlap = max(0, chunk_size - 1)
        top_k = int(st.slider("Top-K initial chunks", 1, 8, 3, key="week3_top_k"))
        threshold = float(st.slider("Evidence threshold", 0.0, 1.0, 0.10, 0.01, key="week3_threshold_v2"))
        st.caption("Below the evidence threshold, the app abstains unless keyword or title-linked evidence supports the question. "
                   "0.10 allows multi-hop evidence with modest embedding similarity.")
    panel.caption(ev.LOADED_BUILD_STAMP)

    params = {"dataset": ev.DATASETS[dataset_name], "chunk_size": chunk_size, "overlap": overlap,
              "top_k": top_k, "threshold": threshold}
    with main:
        playground, documents, benchmark = st.tabs(["Playground", "Documents & chunks", "Benchmark"])
        with playground:
            _render_playground(settings, **params)
        with documents:
            _render_documents(params["dataset"], chunk_size, overlap)
        with benchmark:
            _render_benchmark(settings, **params)


def _get_index(knowledge_base: Path, chunk_size: int, overlap: int, embedding_model: str):
    """Build the FAISS index once per (dataset, chunking, embedding model) and keep it in the session."""
    key = (str(knowledge_base), chunk_size, overlap, embedding_model)
    if st.session_state.get("week3_index_key") != key:
        with st.spinner("Loading documents, chunking, embedding, and building the FAISS index…"):
            st.session_state.week3_index = build_index(knowledge_base, chunk_size, overlap, embedding_model)
            st.session_state.week3_index_key = key
    return st.session_state.week3_index


def _render_playground(settings: ModelSettings, dataset: dict, chunk_size: int, overlap: int, top_k: int, threshold: float) -> None:
    st.caption("Compare the base model's answer with an answer grounded in retrieved evidence.")
    question = st.text_area("Ask a question", dataset["default_question"], height=88, key="week3_question")
    plain, rag = st.columns(2)
    if plain.button("1. Ask without RAG", width="stretch", key="week3_plain_run") and can_run(settings, question):
        try:
            with st.spinner("Calling the base model without retrieved documents…"):
                st.session_state.week3_plain = {"question": question, "result": generate_without_rag(settings.model, question)}
        except Exception as exc:  # noqa: BLE001
            show_error("Baseline generation", exc)
    if rag.button("2. Ask with RAG", type="primary", width="stretch", key="week3_rag_run") and can_run(settings, question):
        stage = "RAG index build"
        try:
            index = _get_index(dataset["knowledge_base"], chunk_size, overlap, settings.embedding_model)
            stage = "RAG retrieval"
            results, latency, tokens = retrieve(index, question, top_k)
            st.session_state.week3_retrieval = {"question": question, "results": results, "latency": latency,
                                                "tokens": tokens, "pipeline_version": ev.RETRIEVAL_PIPELINE_VERSION}
            stage = "Grounded generation"
            with st.spinner("Generating a grounded answer from retrieved context…"):
                st.session_state.week3_rag = {"question": question, "pipeline_version": ev.RETRIEVAL_PIPELINE_VERSION,
                                              "result": generate_with_rag(settings.model, question, results, threshold)}
        except Exception as exc:  # noqa: BLE001
            show_error(stage, exc)

    retrieved = st.session_state.get("week3_retrieval", {})
    current = retrieved.get("question") == question and retrieved.get("pipeline_version") == ev.RETRIEVAL_PIPELINE_VERSION
    if retrieved and not current:
        st.caption("The visible retrieval is for a previous question. Ask with RAG to refresh it.")
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("#### Without RAG")
        stored = st.session_state.get("week3_plain")
        plain_result = stored["result"] if stored and stored["question"] == question else None
        st.info(plain_result["text"] if plain_result else "Click Ask without RAG to generate a baseline answer.")
    with right:
        st.markdown("#### With RAG")
        stored = st.session_state.get("week3_rag")
        rag_result = (stored["result"] if stored and stored["question"] == question
                      and stored.get("pipeline_version") == ev.RETRIEVAL_PIPELINE_VERSION else None)
        st.success(rag_result["text"] if rag_result else "Ask with RAG to generate a grounded answer.")
        if rag_result:
            st.caption(f"Generation decision: {rag_result.get('gate', 'not recorded')}")
            if rag_result.get("prompt"):
                with st.expander("Inspect augmented prompt"):
                    st.code(rag_result["prompt"], language="text")
    results = retrieved.get("results", []) if current else []
    expected = ev.expected_answer(dataset["benchmark"], question)
    if expected:
        st.caption(f"Benchmark expected answer: {expected}")

    st.subheader("Retrieved context")
    if not results:
        st.info("Ask with RAG to see the retrieved chunks.")
    for rank, item in enumerate(results, start=1):
        with st.expander(f"#{rank} · {item['source']} · chunk {item['chunk_number']} · "
                         f"{item.get('retrieval_method', 'dense retrieval')} · similarity {item['score']:.3f}", expanded=rank == 1):
            st.code(item["text"], language="markdown", wrap_lines=True)

    st.subheader("RAG metrics")
    metric_row({
        "Retrieval latency": f"{retrieved['latency'] * 1000:.0f} ms" if results else "—",
        "Generation latency": f"{rag_result['latency_seconds']:.2f}s" if rag_result else "—",
        "Retrieved chunks": len(results),
        "Top similarity": f"{max(item['score'] for item in results):.3f}" if results else "—",
    })
    if rag_result and results:
        st.caption(f"Embedding tokens: {retrieved.get('tokens') or 0} · Context estimate: {approximate_tokens(build_context(results))} tokens "
                   f"· Generation input/output: {rag_result['input_tokens']}/{rag_result['output_tokens']} · Status: {rag_result['status']}")
    with st.expander("Retrieval diagnostics"):
        if not results:
            st.info("Run Ask with RAG to collect retrieval diagnostics.")
        else:
            st.dataframe([{
                "Selected": rank, "Source": item["source"], "Chunk": item["chunk_number"],
                "Method": item.get("retrieval_method"), "Dense similarity": f"{item['score']:.3f}",
                "Dense rank": item.get("dense_rank", "—"), "BM25 score": f"{item.get('lexical_score', 0.0):.3f}",
                "BM25 rank": item.get("lexical_rank", "—"), "Fused rank": item.get("fused_rank", "—"),
            } for rank, item in enumerate(results, start=1)], width="stretch", hide_index=True)


def _render_documents(dataset: dict, chunk_size: int, overlap: int) -> None:
    documents = load_documents(dataset["knowledge_base"])
    st.caption(f"{len(documents)} source documents. {dataset['description']}")
    document_column, chunk_column = st.columns(2, gap="large")
    with document_column:
        source = st.selectbox("Source document", [d.source for d in documents], key="week3_document")
        document = next(item for item in documents if item.source == source)
        st.caption(f"Original Markdown file · {len(document.text):,} characters")
        st.code(document.text, language="markdown", wrap_lines=True, height=460)
    with chunk_column:
        chunks = chunk_documents(documents, chunk_size, overlap)
        st.metric("Chunks created (all documents)", len(chunks))
        for chunk in (c for c in chunks if c.source == source):
            with st.expander(f"{chunk.source} · chunk {chunk.chunk_number}", expanded=True):
                st.code(chunk.text, language="markdown", wrap_lines=True)


def _render_benchmark(settings: ModelSettings, dataset: dict, chunk_size: int, overlap: int, top_k: int, threshold: float) -> None:
    st.caption("Evidence Recall@K evaluates retrieval on its own. The full benchmark also checks each grounded answer, or that it abstains.")
    with st.expander("How benchmark evaluation works"):
        st.markdown("""
1. **Gold evidence** — Each question names the source file or files that support it.
2. **Evidence Recall@K** — A question counts as retrieved only when every expected source appears in the top-*K* chunks, so multi-hop questions need all their documents.
3. **Answer evaluation (optional)** — With **Generate answers too**, each grounded answer is compared with the expected answer by exact match and token F1. Unanswerable questions check that the system abstained.
4. **Limitation** — Gold evidence is per document, not per chunk: any chunk from an expected document earns credit.
""")
    questions = ev.load_questions(dataset["benchmark"])
    generate = st.checkbox("Generate answers too (one LLM call per question)", key="week3_benchmark_full")
    if st.button("Run benchmark", type="primary", key="week3_benchmark_run") and can_run(settings):
        try:
            index = _get_index(dataset["knowledge_base"], chunk_size, overlap, settings.embedding_model)
            bar = st.progress(0, text="Retrieving benchmark evidence…")
            st.session_state.week3_benchmark_rows = ev.run_rag_benchmark(
                index, questions, settings.model, top_k, threshold, generate,
                progress=lambda done, total: bar.progress(done / total, text=f"Processed {done}/{total} questions"))
            bar.empty()
        except Exception as exc:  # noqa: BLE001
            show_error("Benchmark", exc)
    rows = st.session_state.get("week3_benchmark_rows")
    if rows:
        summary = ev.summarize_benchmark(rows)
        metric_row({
            f"Evidence Recall@{top_k}": f"{summary['evidence_recall']:.0%}",
            "Answer exact match": f"{summary['exact_match']:.0%}" if summary["exact_match"] is not None else "—",
            "Mean token F1": f"{summary['mean_f1']:.0%}" if summary["mean_f1"] is not None else "—",
        })
        st.dataframe(rows, width="stretch", hide_index=True)


if __name__ == "__main__":
    run_standalone(render, "Week 3 · RAG")
