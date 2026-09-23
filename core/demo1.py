"""Demo 1: a reproducible context-strategy benchmark."""

import os
import time

import streamlit as st
from openai import OpenAI

from core.context_builder import estimate_tokens

INSTRUCTION = "Summarize the current requirements for the file-processing API. Identify the active timeout, supported file types, authentication requirements, and unresolved issues."
EXPECTED_FACTS = {
    "timeout": ["60", "second"],
    "file types": ["pdf", "csv", "png"],
    "authentication": ["api key"],
    "unresolved": ["retention", "virus"],
}
HISTORY = [
    ("h01", "user", "We need a file-processing API that accepts PDF, CSV, and PNG uploads."),
    ("h02", "assistant", "Initial requirement recorded: PDF, CSV, and PNG are supported."),
    ("h03", "user", "Files may be up to 25 MB. Authenticate every request with an API key."),
    ("h04", "assistant", "The synchronous processing timeout will be 30 seconds."),
    ("h05", "user", "Storage documentation: upload originals to encrypted object storage before processing."),
    ("h06", "user", "The product team prefers blue over green for the dashboard."),
    ("h07", "user", "Correction: the processing timeout must be 60 seconds, not 30."),
    ("h08", "assistant", "Updated active timeout to 60 seconds."),
    ("h09", "user", "We still need to decide retention period and whether virus scanning blocks or quarantines uploads."),
    ("h10", "assistant", "Open questions recorded: retention policy and virus-scanning behavior."),
    ("h11", "user", "The team lunch is Thursday."),
    ("h12", "user", "Reject unsupported formats with a clear validation error."),
]
TASK_HISTORY = [
    ("t01", "user", "Build a task-management REST API for creating, retrieving, and updating tasks."),
    ("t02", "assistant", "Initial design will expose /tasks endpoints."),
    ("t03", "user", "Every task needs a globally unique task ID and a status of todo, in_progress, or done."),
    ("t04", "user", "Deletion was initially permanent, but it must now be soft deletion."),
    ("t05", "assistant", "The active deletion behavior is soft deletion."),
    ("t06", "user", "Authentication will use bearer tokens."),
    ("t07", "user", "We still need to decide whether users can restore deleted tasks and how long audit logs are retained."),
    ("t08", "user", "The office coffee machine needs descaling."),
]
TASK_INSTRUCTION = "Summarize the current requirements for the task-management API. Identify task operations, task IDs and statuses, deletion behavior, authentication, and unresolved issues."
TASK_EXPECTED_FACTS = {
    "operations": ["create", "retriev", "updat"],
    "task model": ["unique", "todo", "in_progress", "done"],
    "deletion": ["soft deletion"],
    "authentication": ["bearer"],
    "unresolved": ["restore", "audit"],
}
DATASETS = {
    "File-processing API": {
        "instruction": INSTRUCTION, "history": HISTORY, "expected_facts": EXPECTED_FACTS,
        "summary": "Earlier authoritative facts: supported types are PDF, CSV, PNG; maximum size is 25 MB; API-key authentication is required; the timeout was revised from 30 to 60 seconds.",
    },
    "Task-management API": {
        "instruction": TASK_INSTRUCTION, "history": TASK_HISTORY, "expected_facts": TASK_EXPECTED_FACTS,
        "summary": "Earlier authoritative facts: tasks can be created, retrieved, and updated; IDs are globally unique; statuses are todo, in_progress, and done; deletion was changed to soft deletion; bearer-token authentication is required.",
    },
}


def _text(item: tuple[str, str, str]) -> str:
    return f"[{item[0]}] {item[1]}: {item[2]}"


def _retrieve(instruction: str, history: list[tuple[str, str, str]], limit: int = 5) -> list[tuple[str, str, str]]:
    terms = {word.lower().strip(".,?") for word in instruction.split() if len(word) > 3}
    ranked = sorted(history, key=lambda item: len(terms & set(item[2].lower().split())), reverse=True)
    return ranked[:limit]


def build_benchmark_context(strategy: str, instruction: str, history: list[tuple[str, str, str]] = HISTORY, summary: str = "", budget: int = 1800) -> dict:
    if strategy == "S0 · Baseline":
        selected = []
        source = "Instruction only"
    elif strategy == "S1 · Full history":
        selected = history
        source = "All history (oldest first; truncated to budget if needed)"
    elif strategy == "S2 · Recent window":
        selected = history[-5:]
        source = "Last 5 turns"
    elif strategy == "S3 · Summary + recent":
        selected = [("summary", "system", summary)] + history[-4:]
        source = "Curated older-history summary plus last 4 turns"
    else:
        selected = _retrieve(instruction, history)
        source = "Top 5 keyword-retrieved turns"
    passages = [_text(item) for item in selected]
    while passages and estimate_tokens("\n".join(passages) + instruction) > budget:
        passages.pop(0)
    context = f"Instruction:\n{instruction}\n\nContext:\n" + ("\n".join(passages) or "(No additional context supplied.)")
    return {"context": context, "provenance": source, "source_ids": [item[0] for item in selected[-len(passages):]], "estimated_tokens": estimate_tokens(context)}


def _score(answer: str, expected_facts: dict[str, list[str]] = EXPECTED_FACTS) -> tuple[int, int, list[str]]:
    normalized = answer.lower()
    passed = [name for name, words in expected_facts.items() if all(word in normalized for word in words)]
    return len(passed), len(expected_facts), passed


def render_demo1() -> None:
    st.subheader("Context Strategy Benchmark")
    st.caption("Run independent calls against one selected synthetic API dataset.")
    left, right = st.columns([0.9, 1.1], gap="large")
    with left:
        dataset_name = st.selectbox("Dataset", list(DATASETS), key="demo1_dataset")
        dataset = DATASETS[dataset_name]
        current_history = dataset["history"]
        st.markdown("**Strategies**")
        strategy_options = ["S0 · Baseline", "S1 · Full history", "S2 · Recent window", "S3 · Summary + recent", "S4 · Keyword retrieval"]
        strategies = [
            strategy for index, strategy in enumerate(strategy_options)
            if st.checkbox(strategy, value=strategy in {"S0 · Baseline", "S2 · Recent window", "S4 · Keyword retrieval"}, key=f"demo1_{index}")
        ]
        model_column, token_column, input_price_column, output_price_column = st.columns(4)
        with model_column:
            model = st.text_input("Model", "gpt-5.4-mini", key="demo1_model")
        with token_column:
            max_output = st.number_input("Max output tokens", 200, 3000, 700, 100, key="demo1_max_output")
        with input_price_column:
            input_price = st.number_input("Input $ / 1M", 0.0, 0.75, format="%.4f", key="demo1_in_price")
        with output_price_column:
            output_price = st.number_input("Output $ / 1M", 0.0, 4.50, format="%.4f", key="demo1_out_price")
        with st.expander("Benchmark Dataset and Expected Facts"):
            st.markdown("**Conversation history**")
            for message_id, role, content in current_history:
                with st.chat_message(role):
                    st.write(f"[{message_id}] {role.title()}: {content}")
            st.markdown("**Expected facts**")
            st.dataframe(
                [{"Requirement": name.title(), "Expected terms": ", ".join(words)} for name, words in dataset["expected_facts"].items()],
                use_container_width=True, hide_index=True,
            )
    if "demo1_results" not in st.session_state:
        st.session_state.demo1_results = []
    with right:
        instruction = st.text_area("Benchmark instruction", dataset["instruction"], key=f"demo1_instruction_{dataset_name}", height=95)
        if st.button("Run benchmark", type="primary", disabled=not strategies, key="demo1_run", use_container_width=True):
            if not os.getenv("OPENAI_API_KEY"):
                st.error("OPENAI_API_KEY is not configured.")
            else:
                results = []
                for strategy in strategies:
                    built = build_benchmark_context(strategy, instruction, current_history, dataset["summary"])
                    try:
                        with st.spinner(f"Running {strategy}…"):
                            started = time.perf_counter()
                            response = OpenAI().responses.create(model=model, instructions="Answer only from supplied context. Clearly identify missing information.", input=built["context"], max_output_tokens=int(max_output))
                        correct, total, facts = _score(response.output_text, dataset["expected_facts"])
                        cost = (response.usage.input_tokens * input_price + response.usage.output_tokens * output_price) / 1_000_000
                        results.append({"dataset": dataset_name, "strategy": strategy, "response": response.output_text, "context": built, "input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens, "latency": time.perf_counter() - started, "accuracy": correct / total, "facts": facts, "cost": cost})
                    except Exception as exc:
                        results.append({"dataset": dataset_name, "strategy": strategy, "error": str(exc), "context": built})
                st.session_state.demo1_results = results
        results = [result for result in st.session_state.demo1_results if result.get("dataset") == dataset_name]
        st.subheader("Benchmark results")
        if not results:
            st.info("Select one or more strategies, then run the benchmark.")
        else:
            table = [{"Strategy": r["strategy"], "Accuracy": f"{r.get('accuracy', 0):.0%}", "Input": r.get("input_tokens", "—"), "Output": r.get("output_tokens", "—"), "Latency": f"{r.get('latency', 0):.2f}s", "Cost": f"${r.get('cost', 0):.5f}"} for r in results]
            st.dataframe(table, use_container_width=True, hide_index=True)
            tabs = st.tabs([r["strategy"] for r in results])
            for tab, result in zip(tabs, results):
                with tab:
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.caption(f"Required facts found: {', '.join(result['facts']) or 'none'}")
                        st.info(result["response"] or "No visible response returned.")
                    with st.expander("Constructed Context to LLM"):
                        st.caption(f"{result['context']['provenance']} · IDs: {', '.join(result['context']['source_ids']) or 'none'} · Estimated: {result['context']['estimated_tokens']} tokens")
                        st.code(result["context"]["context"], language="text")
