"""Week 3 page: retrieval-augmented generation (RAG). Answer from documents the model has never seen.

Run alone:   streamlit run labs/week3_rag/page.py
In the site: streamlit run app.py
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

# Lets this page run on its own (streamlit run labs/<lab>/page.py) as well as inside app.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from labs.shared.settings import ModelSettings
from labs.shared.ui import (can_run, example_text_area, get_model_settings, lab_parameters, metric_row, mini_muse_part,
                            page_layout, run_standalone, show_error, usage_line)
from labs.week3_rag import evaluation as ev
from labs.week3_rag.rag import (CHUNK_STRATEGIES, EMBEDDING_MODELS, SEARCH_METHODS, build_index, chunk_documents,
                                generate_with_rag, generate_without_rag, load_documents, retrieve)

HOW_IT_WORKS = """
A model can't answer from documents it has never seen. **RAG** (retrieval-augmented generation) searches your documents first and puts the best passages into the context, so the answer comes from them.

**Documents → chunks → search → context → answer**

| Step | What happens | You control | See it in |
|---|---|---|---|
| 1. Chunk | Each document is cut into small pieces that can be searched | Chunk strategy, size, overlap | **See the chunks** |
| 2. Index | Each chunk becomes an embedding: numbers that capture its meaning | Embedding model | Built once per setting |
| 3. Search | The question is matched against every chunk; the best are kept | Search method, Top-K | **Ask a question** → What the model sees with RAG |
| 4. Answer | The kept chunks go into the context; the model answers from them and cites the files, or says it doesn't know | Model, Evidence threshold (Advanced) | **Ask a question** → With RAG |
| 5. Measure | Every benchmark question is searched: were the right documents found? | — | **Compare settings** |

**The two document sets** (Documents, in Lab parameters)
- **NovaTech** (start here): 10 short policies from a made-up company. The model can't know them, so without RAG it can only guess. Each answer sits in **one** document.
- **HotpotQA**: 198 real Wikipedia articles from a research benchmark. Each answer needs **two** articles (find who played a role, then what she did later), so search often finds only one of them. The model may already know some answers from training.

Both include a few questions with no answer in the documents, to check that the system says so instead of guessing.

**Reading the metrics** (Compare settings)

Search is scored first, then answers. Each number is an average over the questions.

| Metric | Scores | Question it answers | Example |
|---|---|---|---|
| **Recall@K** | Search | Of the documents the answer needs, how many were in the top K chunks? | A HotpotQA question needs 2 articles; 1 was found → 50%. |
| **Precision@K** | Search | Of the K chunks sent to the model, how many came from a needed document? | 3 chunks sent, 1 from a needed article → 33%. |
| **Exact match** | Answers | Is the **whole** answer the expected one (ignoring case, punctuation and cited sources)? Strict: extra words count as wrong. For questions with no answer in the documents, a match means the system said it didn't know. | Expected "Chief of Protocol": "chief of protocol" ✓; "She served as Chief of Protocol." ✗ |
| **F1** | Answers | Partial credit: the balance of how many of the answer's words are expected (precision) and how many expected words it includes (recall). | "Chief of Protocol of the United States" → about 60%. |

How to read them together:
- **Recall vs. precision is the Top-K trade-off.** A higher Top-K finds more needed documents (recall up) but sends more noise (precision down), and costs more tokens on every call.
- **Answers can't beat search.** When a needed document is missing, the model can only say it doesn't know or guess, so low recall caps exact match and F1. Fix search first.
- **The gap between F1 and exact match** is mostly right answers worded differently.

**Try this**
- Ask "How many remote days are employees allowed?" Without RAG the model can only guess; with RAG it quotes NovaTech's policy.
- Switch **Chunk strategy** to *By heading*, then open **See the chunks**: each policy becomes a single chunk. Ask again and compare the input tokens.
- In **Compare settings**, run once with *Keywords*, once with *Meaning*, once with *Hybrid*, and compare in "Your runs" (or click "Compare all three search methods").
- Switch **Documents** to HotpotQA. Each answer needs two articles, so watch whether both ⭐ documents are found, and try a higher Top-K.
"""


def _evidence(item: dict) -> set[str]:
    value = item.get("evidence") or []
    return {value} if isinstance(value, str) else set(value)


def render() -> None:
    main, panel = page_layout("Week 3 · Retrieval-augmented generation")
    if mini_muse_part(main, panel, 3,
                      caption="Give the model passages from your own documents, and compare its answer with and without them.",
                      how_it_works=HOW_IT_WORKS):
        return
    settings = get_model_settings()
    names = list(ev.DATASETS)
    with lab_parameters(panel):
        dataset_name = st.selectbox("Documents", names, index=len(names) - 1, key="week3_dataset",
                                    help="NovaTech: 10 short company policies, one document per answer. "
                                         "HotpotQA: 198 Wikipedia articles, two documents per answer.")
        st.markdown("Chunking")
        strategy = st.radio("Chunk strategy", list(CHUNK_STRATEGIES), format_func=CHUNK_STRATEGIES.get,
                            key="week3_strategy", help="How each document is cut into pieces.")
        chunk_size, overlap = 200, 50
        if strategy == "fixed":
            chunk_size = int(st.slider("Chunk size (characters)", 100, 1200, 200, 50, key="week3_chunk_size"))
            overlap = int(st.slider("Chunk overlap (characters)", 0, 250, 50, 10, key="week3_overlap"))
            if overlap >= chunk_size:
                st.error("Overlap must be smaller than chunk size.")
                overlap = max(0, chunk_size - 1)
        else:
            st.caption("Chunks follow the document's own " + ("paragraphs." if strategy == "paragraph" else "headings."))
        st.markdown("Search")
        method = st.radio("Search method", list(SEARCH_METHODS), format_func=SEARCH_METHODS.get, key="week3_method",
                          help="Meaning: embeddings match paraphrases. Keywords: BM25 matches exact words. "
                               "Hybrid: both, merged.")
        embedding_model = st.selectbox("Embedding model", EMBEDDING_MODELS, key="week3_embedding_model",
                                       accept_new_options=True, disabled=method == "keyword",
                                       help="Turns chunks and questions into vectors for meaning search. "
                                            "Not used by keyword search.")
        top_k = int(st.slider("Top-K chunks", 1, 8, 3, key="week3_top_k", help="How many chunks go into the context."))
        with st.expander("Advanced"):
            threshold = float(st.slider("Evidence threshold", 0.0, 1.0, 0.10, 0.01, key="week3_threshold_v2",
                                        help="Below this similarity the app declines to answer, unless keyword or "
                                             "title matches support the question."))
            st.caption(ev.LOADED_BUILD_STAMP)
    settings = replace(settings, embedding_model=embedding_model or settings.embedding_model)

    dataset = ev.DATASETS[dataset_name]
    params = {"dataset": dataset, "chunk_size": chunk_size, "overlap": overlap, "top_k": top_k, "threshold": threshold,
              "strategy": strategy, "method": method}
    with main:
        ask, documents, benchmark = st.tabs(["Ask a question", "See the chunks", "Compare settings"])
        with ask:
            _render_ask(settings, **params)
        with documents:
            _render_documents(dataset, chunk_size, overlap, strategy)
        with benchmark:
            _render_benchmark(settings, **params)


def _get_index(knowledge_base: Path, chunk_size: int, overlap: int, embedding_model: str, strategy: str):
    """Build the index once per (documents, chunking, embedding model) and keep it in the session."""
    key = (str(knowledge_base), chunk_size, overlap, embedding_model, strategy)
    if st.session_state.get("week3_index_key") != key:
        with st.spinner("Chunking and embedding the documents (once per setting)…"):
            st.session_state.week3_index = build_index(knowledge_base, chunk_size, overlap, embedding_model, strategy)
            st.session_state.week3_index_key = key
    return st.session_state.week3_index


def _render_ask(settings: ModelSettings, dataset: dict, chunk_size: int, overlap: int, top_k: int, threshold: float,
                strategy: str, method: str) -> None:
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
            index = _get_index(dataset["knowledge_base"], chunk_size, overlap, settings.embedding_model, strategy)
            stage = "Retrieval"
            results, latency, embed_tokens = retrieve(index, question, top_k, method)
            stage = "Answer with RAG"
            with st.spinner("Asking the model with the retrieved chunks…"):
                grounded = generate_with_rag(settings.model, question, results, threshold)
            st.session_state.week3_ask = {"question": question, "dataset": dataset["knowledge_base"], "plain": plain,
                                          "rag": grounded, "results": results, "latency": latency,
                                          "pipeline": ev.RETRIEVAL_PIPELINE_VERSION,
                                          "how": {"fixed": "fixed-size chunks", "paragraph": "paragraph chunks",
                                                  "heading": "section chunks"}[strategy] + " · " +
                                                 {"hybrid": "hybrid search", "dense": "meaning search",
                                                  "keyword": "keyword search"}[method]}
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
        st.caption(f"{len(results)} chunks retrieved in {saved['latency'] * 1000:.0f} ms · {saved.get('how', '')}"
                   + (f" · {len(found)} of {len(gold)} ⭐ documents that hold the answer" if gold else ""))
        for rank, c in enumerate(results, start=1):
            star = " ⭐" if c["source"] in gold else ""
            score = f"similarity {c['score']:.2f}" if c["score"] else f"keyword score {c.get('lexical_score', 0):.2f}"
            with st.expander(f"#{rank} · {c['source']} · chunk {c['chunk_number']} · {score}{star}",
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


def _render_documents(dataset: dict, chunk_size: int, overlap: int, strategy: str) -> None:
    documents = load_documents(dataset["knowledge_base"])
    chunks = chunk_documents(documents, chunk_size, overlap, strategy)
    st.caption(f"{dataset['description']} With the current settings they make {len(chunks):,} chunks.")
    source = st.selectbox("Document", [d.source for d in documents], key="week3_document")
    document = next(d for d in documents if d.source == source)
    original, cut = st.columns(2, gap="large")
    with original, st.container(border=True):
        st.markdown(f"**Original** · {len(document.text):,} characters")
        st.code(document.text, language=None, wrap_lines=True, height=460)
    with cut, st.container(border=True):
        own = [c for c in chunks if c.source == source]
        how = {"fixed": f"up to {chunk_size} characters, overlapping by {overlap}",
               "paragraph": "one per paragraph", "heading": "one per heading section"}[strategy]
        st.markdown(f"**Chunks** · {len(own)}, {how}")
        for chunk in own:
            st.code(chunk.text, language=None, wrap_lines=True)


DOCUMENT_SET = {"novatech": "NovaTech", "hotpotqa_mini": "HotpotQA"}
RUN_COLUMNS = {
    "Recall@K": st.column_config.TextColumn("Recall@K", help="Search: share of the needed documents found in the top K chunks."),
    "Precision@K": st.column_config.TextColumn("Precision@K", help="Search: share of the top K chunks that came from a needed document."),
    "Exact match": st.column_config.TextColumn("Exact match", help="Answers: whole answer equals the expected one."),
    "F1": st.column_config.TextColumn("F1", help="Answers: word overlap with the expected answer (partial credit)."),
}


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.0%}"


def _settings_label(strategy: str, chunk_size: int, overlap: int, method: str, embedding: str, top_k: int) -> dict:
    return {"Chunks": CHUNK_STRATEGIES[strategy] + (f" {chunk_size}/{overlap}" if strategy == "fixed" else ""),
            "Search": SEARCH_METHODS[method], "Embedding": "—" if method == "keyword" else embedding, "Top-K": top_k}


def _render_benchmark(settings: ModelSettings, dataset: dict, chunk_size: int, overlap: int, top_k: int, threshold: float,
                      strategy: str, method: str) -> None:
    questions = ev.load_questions(dataset["benchmark"])
    docs = DOCUMENT_SET.get(Path(dataset["knowledge_base"]).name, Path(dataset["knowledge_base"]).name)
    current = _settings_label(strategy, chunk_size, overlap, method, settings.embedding_model, top_k)
    st.caption(f"Runs all {len(questions)} {docs} questions and checks whether the documents that hold each answer "
               f"are among the top {top_k} chunks. Change one setting in Lab parameters, run again, and compare.")
    st.markdown("Now testing: " + " · ".join(f"**{k}** {v}" for k, v in current.items()))
    generate = st.checkbox("Also generate and score answers", key="week3_benchmark_full",
                           help="One extra model call per question.")
    if generate:
        st.caption(f"Adds {len(questions)} model calls per run.")
    run, run_all, clear = st.columns([1.2, 1.8, 1])
    single = run.button("Run", type="primary", width="stretch", key="week3_benchmark_run")
    three = run_all.button("Compare all three search methods", width="stretch", key="week3_benchmark_methods",
                           help="Runs Keywords, Meaning and Hybrid with everything else unchanged.")
    if clear.button("Clear runs", width="stretch", key="week3_benchmark_clear"):
        st.session_state.pop("week3_runs", None)
        st.session_state.pop("week3_benchmark_rows", None)

    if (single or three) and can_run(settings):
        methods = ["keyword", "dense", "hybrid"] if three else [method]
        try:
            index = _get_index(dataset["knowledge_base"], chunk_size, overlap, settings.embedding_model, strategy)
            bar = st.progress(0.0, text="Searching…")
            runs = st.session_state.setdefault("week3_runs", [])
            for i, m in enumerate(methods):
                rows = ev.run_rag_benchmark(
                    index, questions, settings.model, top_k, threshold, generate, method=m,
                    progress=lambda done, total, i=i, m=m: bar.progress(
                        (i * total + done) / (len(methods) * total),
                        text=f"{SEARCH_METHODS[m]}: {done} of {total} questions"))
                summary = ev.summarize_benchmark(rows)
                runs.append({"Run": len(runs) + 1, "Documents": docs,
                             **_settings_label(strategy, chunk_size, overlap, m, settings.embedding_model, top_k),
                             "Recall@K": _pct(summary["recall_at_k"]), "Precision@K": _pct(summary["precision_at_k"]),
                             "Exact match": _pct(summary["exact_match"]), "F1": _pct(summary["mean_f1"])})
                st.session_state.week3_benchmark_rows = {"run": len(runs), "rows": rows}
            bar.empty()
        except Exception as exc:  # noqa: BLE001
            show_error("Benchmark", exc)

    runs = st.session_state.get("week3_runs", [])
    if runs and any("Recall@K" not in r for r in runs):  # recorded before Recall@K / Precision@K existed
        st.session_state.week3_runs = runs = [r for r in runs if "Recall@K" in r]
        st.session_state.pop("week3_benchmark_rows", None)
        st.info("Earlier runs used the old metrics and were cleared. Run again to compare with Recall@K and Precision@K.")
    if not runs:
        st.caption("Run once to start a comparison table.")
        return
    with st.container(border=True):
        st.markdown("**Your runs**")
        latest = runs[-1]["Run"]
        st.dataframe([{**r, "Run": f"#{r['Run']}" + (" (latest)" if r["Run"] == latest else "")} for r in runs[::-1]],
                     width="stretch", hide_index=True, column_config=RUN_COLUMNS)
        st.caption("Search: **Recall@K** (were the needed documents found?) and **Precision@K** (how much of what was "
                   "sent was needed?). Answers, when generated: **Exact match** and **F1**. Hover a column for details.")

    saved = st.session_state.get("week3_benchmark_rows")
    if saved and saved["rows"] and "Recall@K" in saved["rows"][0]:
        with st.expander(f"Question by question · run #{saved['run']}"):
            misses_only = st.checkbox("Show only misses", key="week3_misses")
            table = []
            for row in saved["rows"]:
                found = row["Evidence found"]
                answered = row["Exact match"]
                missed = found == "✗" or answered == "0%"
                if misses_only and not missed:
                    continue
                entry = {"Question": row["Question"],
                         "Documents needed": ", ".join(row["Expected evidence"]) if isinstance(row["Expected evidence"], list)
                         else row["Expected evidence"],
                         "All found?": {"✓": "✓", "✗": "✗"}.get(found, "no answer exists"),
                         "Recall@K": row.get("Recall@K", "—"), "Precision@K": row.get("Precision@K", "—")}
                if answered != "—":
                    entry["Answer correct?"] = "✓" if answered == "100%" else "✗"
                    entry["Answer"] = row.get("Answer", "")
                table.append(entry)
            if table:
                st.dataframe(table, width="stretch", hide_index=True)
            else:
                st.caption("No misses in this run.")


if __name__ == "__main__":
    run_standalone(render, "Week 3 · Retrieval-augmented generation")
