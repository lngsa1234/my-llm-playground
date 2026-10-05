"""Week 3 Streamlit RAG playground and benchmark."""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from pathlib import Path

import streamlit as st

from core.rag import (
    ABSTENTION,
    approximate_tokens,
    build_context,
    build_index,
    chunk_documents,
    generate_with_rag,
    generate_without_rag,
    load_documents,
    retrieve,
)


ROOT = Path(__file__).resolve().parents[1]
DATASETS = {
    "HotpotQA mini · multi-hop": {
        "knowledge_base": ROOT / "knowledge_base" / "hotpotqa_mini",
        "benchmark": ROOT / "benchmark" / "hotpotqa_mini_questions.json",
        "description": "50 official HotpotQA development questions over 198 Wikipedia articles. Each question needs two supporting articles.",
        "default_question": "What government position was held by the woman who portrayed Corliss Archer in the film Kiss and Tell?",
    },
    "NovaTech starter · single-hop": {
        "knowledge_base": ROOT / "knowledge_base",
        "benchmark": ROOT / "benchmark" / "questions.json",
        "description": "Ten fictional company-policy documents for a smaller, single-hop introduction.",
        "default_question": "How long do Pro customers have to request their money back?",
    },
}


def _index_key(knowledge_base: Path, chunk_size: int, overlap: int, embedding_model: str) -> tuple[str, int, int, str]:
    return str(knowledge_base), chunk_size, overlap, embedding_model


def _get_index(knowledge_base: Path, chunk_size: int, overlap: int, embedding_model: str):
    key = _index_key(knowledge_base, chunk_size, overlap, embedding_model)
    if st.session_state.get("week3_index_key") != key:
        with st.spinner("Loading documents, chunking, embedding, and building the FAISS index…"):
            st.session_state.week3_index = build_index(knowledge_base, chunk_size, overlap, embedding_model)
            st.session_state.week3_index_key = key
    return st.session_state.week3_index


def _render_retrieval(results: list[dict]) -> None:
    st.subheader("Retrieved context")
    if not results:
        st.info("Retrieve evidence to inspect the chunks before generating an answer.")
        return
    for rank, item in enumerate(results, start=1):
        method = item.get("retrieval_method", "dense retrieval")
        with st.expander(f"#{rank} · {item['source']} · chunk {item['chunk_number']} · {method} · similarity {item['score']:.3f}", expanded=rank == 1):
            st.code(item["text"], language="markdown", wrap_lines=True)


def _render_metrics(retrieval_latency: float | None, retrieval_tokens: int | None, results: list[dict], generation: dict | None) -> None:
    st.subheader("RAG metrics")
    a, b, c, d = st.columns(4)
    a.metric("Retrieval latency", f"{retrieval_latency * 1000:.0f} ms" if retrieval_latency is not None else "—")
    b.metric("Generation latency", f"{generation['latency_seconds']:.2f} s" if generation else "—")
    c.metric("Retrieved chunks", len(results))
    d.metric("Top similarity", f"{results[0]['score']:.3f}" if results else "—")
    if generation:
        st.caption(
            f"Embedding tokens: {retrieval_tokens or 0} · Context estimate: {approximate_tokens(build_context(results))} tokens "
            f"· Generation input/output: {generation['input_tokens']}/{generation['output_tokens']} · Status: {generation['status']}"
        )


def _run_retrieval(index, question: str, top_k: int) -> None:
    results, latency, tokens = retrieve(index, question, top_k)
    st.session_state.week3_retrieval = {"question": question, "results": results, "latency": latency, "tokens": tokens}


def _expected_answer(benchmark_file: Path, question: str) -> str | None:
    """Return the reference answer when the playground question is benchmarked."""
    questions = json.loads(benchmark_file.read_text(encoding="utf-8"))
    return next((item["expected_answer"] for item in questions if item["question"] == question), None)


def _render_playground(dataset: dict, model: str, embedding_model: str, chunk_size: int, overlap: int, top_k: int, threshold: float) -> None:
    st.subheader("RAG playground")
    st.caption("Compare the base model's answer with an answer grounded in hybrid, multi-hop knowledge-base evidence.")
    question = st.text_area(
        "Ask a question",
        dataset["default_question"],
        height=88,
        key="week3_question",
    )
    plain, rag = st.columns(2)
    has_key = bool(os.getenv("OPENAI_API_KEY"))
    if not has_key:
        st.warning("Set OPENAI_API_KEY to run retrieval or generation.")
    if plain.button("1. Ask without RAG", use_container_width=True, disabled=not has_key):
        try:
            with st.spinner("Calling the base model without retrieved documents…"):
                st.session_state.week3_plain = {"question": question, "result": generate_without_rag(model, question)}
        except Exception as exc:
            st.error(f"Baseline request failed: {exc}")
    if rag.button("2. Ask with RAG", type="primary", use_container_width=True, disabled=not has_key):
        try:
            index = _get_index(dataset["knowledge_base"], chunk_size, overlap, embedding_model)
            _run_retrieval(index, question, top_k)
            retrieved = st.session_state.week3_retrieval
            with st.spinner("Generating a grounded answer from retrieved context…"):
                st.session_state.week3_rag = {"question": question, "result": generate_with_rag(model, question, retrieved["results"], threshold)}
        except Exception as exc:
            st.error(f"RAG request failed: {exc}")

    retrieved = st.session_state.get("week3_retrieval", {})
    if retrieved and retrieved.get("question") != question:
        st.caption("The visible retrieval belongs to a previous question. Ask with RAG to refresh it.")
    comparison_left, comparison_right = st.columns(2, gap="large")
    with comparison_left:
        st.markdown("#### Without RAG")
        stored = st.session_state.get("week3_plain")
        result = stored["result"] if stored and stored["question"] == question else None
        st.info(result["text"] if result else "Click Ask without RAG to generate a baseline answer.")
    with comparison_right:
        st.markdown("#### With RAG")
        stored = st.session_state.get("week3_rag")
        result = stored["result"] if stored and stored["question"] == question else None
        st.success(result["text"] if result else "Ask with RAG to generate a grounded answer.")
        if result and result.get("prompt"):
            with st.expander("Inspect augmented prompt"):
                st.code(result["prompt"], language="text")
    results = retrieved.get("results", []) if retrieved.get("question") == question else []
    expected_answer = _expected_answer(dataset["benchmark"], question)
    if expected_answer:
        st.caption(f"Benchmark expected answer: {expected_answer}")
    _render_retrieval(results)
    _render_metrics(retrieved.get("latency") if results else None, retrieved.get("tokens") if results else None, results, result)


def _render_knowledge_base(knowledge_base: Path, description: str, chunk_size: int, overlap: int) -> None:
    st.subheader("Knowledge base and chunking")
    documents = load_documents(knowledge_base)
    st.caption(f"{len(documents)} source documents. {description}")
    document_column, chunk_column = st.columns(2, gap="large")
    with document_column:
        selected_source = st.selectbox("Source document", [document.source for document in documents])
        document = next(item for item in documents if item.source == selected_source)
        st.caption(f"Original indexed Markdown file · {len(document.text):,} characters")
        st.code(document.text, language="markdown", wrap_lines=True, height=460)
    with chunk_column:
        chunks = chunk_documents(documents, chunk_size, overlap)
        st.metric("Chunks created", len(chunks))
        selected_chunks = [chunk for chunk in chunks if chunk.source == selected_source]
        for chunk in selected_chunks:
            with st.expander(f"{chunk.source} · chunk {chunk.chunk_number}", expanded=True):
                st.code(chunk.text, language="markdown", wrap_lines=True)


def _expected_found(item: dict, results: list[dict]) -> bool | None:
    evidence = item["evidence"]
    if evidence is None:
        return None
    expected_sources = {evidence} if isinstance(evidence, str) else set(evidence)
    return expected_sources.issubset({result["source"] for result in results})


def _normalize_answer(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _answer_before_sources(text: str) -> str:
    return re.split(r"\n\s*sources?\s*:", text, maxsplit=1, flags=re.IGNORECASE)[0]


def _answer_scores(answer: str, expected: str) -> tuple[float, float]:
    """Return normalized exact match and token F1 for a generated answer."""
    predicted_tokens = _normalize_answer(_answer_before_sources(answer))
    expected_tokens = _normalize_answer(expected)
    exact = float(predicted_tokens == expected_tokens)
    if not predicted_tokens or not expected_tokens:
        return exact, float(predicted_tokens == expected_tokens)
    overlap = sum((Counter(predicted_tokens) & Counter(expected_tokens)).values())
    precision = overlap / len(predicted_tokens)
    recall = overlap / len(expected_tokens)
    return exact, 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _render_benchmark(knowledge_base: Path, benchmark_file: Path, model: str, embedding_model: str, chunk_size: int, overlap: int, top_k: int, threshold: float) -> None:
    st.subheader("Benchmark")
    st.caption("Evidence Recall@K evaluates retrieval independently. The full benchmark then checks whether a grounded answer contains the expected phrase or properly abstains.")
    questions = json.loads(benchmark_file.read_text(encoding="utf-8"))
    full = st.checkbox("Generate answers too (uses one LLM call per question)", key="week3_benchmark_full")
    if st.button("Run benchmark", type="primary", disabled=not os.getenv("OPENAI_API_KEY"), key="week3_benchmark_run"):
        try:
            index = _get_index(knowledge_base, chunk_size, overlap, embedding_model)
            rows = []
            progress = st.progress(0, text="Retrieving benchmark evidence…")
            for position, item in enumerate(questions, start=1):
                results, latency, tokens = retrieve(index, item["question"], top_k)
                answer = generate_with_rag(model, item["question"], results, threshold) if full else None
                evidence_found = _expected_found(item, results)
                exact_match = None
                f1 = None
                if answer:
                    expected = item["expected_answer"].lower()
                    if expected != "not_found":
                        exact_match, f1 = _answer_scores(answer["text"], expected)
                    else:
                        exact_match = float(answer["abstained"] or ABSTENTION.lower() in answer["text"].lower())
                rows.append({
                    "Question": item["question"], "Expected evidence": item["evidence"] or "N/A (abstain)",
                    "Evidence found": "N/A" if evidence_found is None else ("✓" if evidence_found else "✗"),
                    "Exact match": "—" if exact_match is None else f"{exact_match:.0%}",
                    "Token F1": "—" if f1 is None else f"{f1:.0%}",
                    "Grounded": "—" if answer is None else ("✓" if answer["abstained"] or evidence_found else "?"),
                    "Latency": f"{latency + (answer['latency_seconds'] if answer else 0):.2f}s",
                })
                progress.progress(position / len(questions), text=f"Processed {position}/{len(questions)} questions")
            progress.empty()
            st.session_state.week3_benchmark_rows = rows
        except Exception as exc:
            st.error(f"Benchmark failed: {exc}")
    rows = st.session_state.get("week3_benchmark_rows")
    if rows:
        evaluable = [row for row in rows if row["Evidence found"] != "N/A"]
        recall = sum(row["Evidence found"] == "✓" for row in evaluable) / len(evaluable) if evaluable else 0
        answers = [row for row in rows if row["Exact match"] != "—"]
        exact_match = sum(float(row["Exact match"].strip("%")) / 100 for row in answers) / len(answers) if answers else None
        f1 = [float(row["Token F1"].strip("%")) / 100 for row in rows if row["Token F1"] != "—"]
        a, b = st.columns(2)
        a.metric(f"Evidence Recall@{top_k}", f"{recall:.0%}")
        b.metric("Answer exact match", f"{exact_match:.0%}" if exact_match is not None else "Run full benchmark")
        st.metric("Mean token F1", f"{sum(f1) / len(f1):.0%}" if f1 else "Run full benchmark")
        st.dataframe(rows, use_container_width=True, hide_index=True)


def render_week3() -> None:
    """Render the complete Week 3 RAG lab."""
    st.header("Week 3 · Build and Evaluate a RAG System")
    st.caption("Documents → chunks → embeddings → FAISS search → grounded answer + sources → evidence evaluation")
    with st.sidebar:
        st.divider()
        st.subheader("RAG controls")
        dataset_name = st.selectbox("Dataset", list(DATASETS), key="week3_dataset")
        dataset = DATASETS[dataset_name]
        model = st.text_input("Generation model", "gpt-5.4-mini", key="week3_model")
        embedding_model = st.text_input("Embedding model", "text-embedding-3-small", key="week3_embedding_model")
        chunk_size = int(st.slider("Chunk size (characters)", 100, 1200, 200, 50, key="week3_chunk_size"))
        overlap = int(st.slider("Chunk overlap (characters)", 0, 250, 50, 10, key="week3_overlap"))
        if overlap >= chunk_size:
            st.error("Overlap must be smaller than chunk size.")
            overlap = max(0, chunk_size - 1)
        top_k = int(st.slider("Top-K chunks", 1, 8, 3, key="week3_top_k"))
        threshold = float(st.slider("Evidence threshold", 0.0, 1.0, 0.35, 0.01, key="week3_threshold"))
        st.caption("Retrieval combines dense embeddings, BM25 keywords, reciprocal-rank fusion, and title-linked second hops. Below this cosine-similarity score, the app abstains before calling the LLM.")
    playground, knowledge, benchmark = st.tabs(["Playground", "Documents & chunks", "Benchmark"])
    with playground:
        _render_playground(dataset, model, embedding_model, chunk_size, overlap, top_k, threshold)
    with knowledge:
        _render_knowledge_base(dataset["knowledge_base"], dataset["description"], chunk_size, overlap)
    with benchmark:
        _render_benchmark(dataset["knowledge_base"], dataset["benchmark"], model, embedding_model, chunk_size, overlap, top_k, threshold)
