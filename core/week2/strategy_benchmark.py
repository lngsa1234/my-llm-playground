"""Week 2 Demo 1 core logic: a reproducible context-strategy benchmark."""

import re
import time
from collections import Counter

from openai import OpenAI

from core.common import ModelSettings
from core.week2.context_builder import estimate_tokens
from core.week2.longbench_subset import download_subset, load_cached_cases

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
SECURITY_HISTORY = [
    ("s01", "user", "Draft access policy: all staff use password plus SMS verification."),
    ("s02", "assistant", "Initial policy records SMS as the second factor."),
    ("s03", "user", "Administrators must use SSO and hardware security keys."),
    ("s04", "user", "Customer data must be encrypted at rest using AES-256 and in transit with TLS 1.3."),
    ("s05", "user", "Change request: SMS is no longer allowed. All staff must use an authenticator app for MFA."),
    ("s06", "assistant", "Active MFA requirement updated to an authenticator app."),
    ("s07", "user", "We have not decided the session duration or break-glass access process."),
    ("s08", "user", "The security team is ordering new stickers for laptops."),
]
SECURITY_INSTRUCTION = "Summarize the active access-security policy. Identify staff MFA, administrator controls, encryption requirements, and unresolved decisions."
SECURITY_EXPECTED_FACTS = {
    "staff mfa": ["authenticator"],
    "administrator controls": ["sso", "hardware"],
    "encryption": ["aes-256", "tls 1.3"],
    "unresolved": ["session", "break-glass"],
}
SUPPORT_HISTORY = [
    ("r01", "user", "Knowledge base: reset a password from Settings > Security > Reset password; reset links expire after 15 minutes."),
    ("r02", "assistant", "Password-reset article indexed."),
    ("r03", "user", "Knowledge base: billing invoices are downloaded from Billing > Invoices and are available to account owners only."),
    ("r04", "user", "Knowledge base: CSV exports support UTF-8 files up to 100 MB and complete asynchronously."),
    ("r05", "user", "A customer asks why their 120 MB export failed and whether they can retry immediately."),
    ("r06", "assistant", "The support reply should cite the export size limit and available next step."),
    ("r07", "user", "The support team picnic menu includes vegetarian sandwiches."),
]
SUPPORT_INSTRUCTION = "Answer the customer’s export question using the knowledge-base context. State the file-size limit, supported encoding, processing behavior, and a safe next step."
SUPPORT_EXPECTED_FACTS = {
    "limit": ["100", "mb"],
    "encoding": ["utf-8"],
    "processing": ["asynchronously"],
    "next step": ["smaller"],
}
DATASETS = {
    "Quick scenario · File-processing API": {
        "instruction": INSTRUCTION, "history": HISTORY, "expected_facts": EXPECTED_FACTS,
        "evidence_ids": ["h01", "h03", "h07", "h09"],
        "summary": "Earlier authoritative facts: supported types are PDF, CSV, PNG; maximum size is 25 MB; API-key authentication is required; the timeout was revised from 30 to 60 seconds.",
    },
    "Quick scenario · Task-management API": {
        "instruction": TASK_INSTRUCTION, "history": TASK_HISTORY, "expected_facts": TASK_EXPECTED_FACTS,
        "evidence_ids": ["t01", "t03", "t04", "t06", "t07"],
        "summary": "Earlier authoritative facts: tasks can be created, retrieved, and updated; IDs are globally unique; statuses are todo, in_progress, and done; deletion was changed to soft deletion; bearer-token authentication is required.",
    },
    "Quick scenario · Security policy updates": {
        "instruction": SECURITY_INSTRUCTION, "history": SECURITY_HISTORY, "expected_facts": SECURITY_EXPECTED_FACTS,
        "evidence_ids": ["s03", "s04", "s05", "s07"],
        "summary": "Earlier authoritative facts: SMS MFA was superseded by authenticator-app MFA for staff; administrators require SSO and hardware keys; data encryption uses AES-256 at rest and TLS 1.3 in transit.",
    },
    "Quick scenario · Support knowledge retrieval": {
        "instruction": SUPPORT_INSTRUCTION, "history": SUPPORT_HISTORY, "expected_facts": SUPPORT_EXPECTED_FACTS,
        "evidence_ids": ["r04", "r05"],
        "summary": "Earlier authoritative facts: CSV exports accept UTF-8 files up to 100 MB and process asynchronously; a customer’s 120 MB export failed.",
    },
}


def _longbench_case_dataset(case: dict) -> dict:
    passages = [part.strip() for part in re.split(r"(?=Passage \d+:)", case["context"]) if part.strip()]
    history = [(f"p{index}", "document", passage) for index, passage in enumerate(passages, start=1)]
    answer = case["answers"][0]
    return {
        "instruction": case["input"],
        "history": history,
        "expected_facts": {"reference answer": [answer.lower()]},
        "evidence_ids": [],
        "summary": "",
        "official": True,
        "reference_answer": answer,
        "reference_answers": case["answers"],
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
    included = selected[:]
    passages = [_text(item) for item in included]
    while passages and estimate_tokens("\n".join(passages) + instruction) > budget:
        # Full-document and retrieval contexts are ordered by importance at
        # the front. Recent-window contexts intentionally retain the tail.
        if strategy in {"S1 · Full history", "S4 · Keyword retrieval"}:
            included.pop()
            passages.pop()
        else:
            included.pop(0)
            passages.pop(0)
    if not passages and selected:
        # A single LongBench passage can exceed the entire budget. Retain the
        # summary record when available; otherwise retain a clipped
        # excerpt rather than silently sending no context.
        preferred = selected[0] if strategy in {"S1 · Full history", "S3 · Summary + recent", "S4 · Keyword retrieval"} else selected[-1]
        available_characters = max(200, (budget - estimate_tokens(instruction) - 12) * 4)
        included = [preferred]
        passages = [_text(preferred)[:available_characters] + "\n[Context clipped to budget]"]
    context = f"Instruction:\n{instruction}\n\nContext:\n" + ("\n".join(passages) or "(No additional context supplied.)")
    return {"context": context, "provenance": source, "source_ids": [item[0] for item in included], "estimated_tokens": estimate_tokens(context)}


def _score(answer: str, expected_facts: dict[str, list[str]] = EXPECTED_FACTS) -> tuple[int, int, list[str]]:
    normalized = answer.lower()
    passed = [name for name, words in expected_facts.items() if all(word in normalized for word in words)]
    return len(passed), len(expected_facts), passed


def _longbench_f1(answer: str, references: list[str]) -> tuple[float, list[str]]:
    """A transparent token-overlap score for the HotpotQA classroom subset."""
    prediction = re.findall(r"\w+", answer.lower())
    best_score = 0.0
    best_reference = ""
    for reference in references:
        gold = re.findall(r"\w+", reference.lower())
        overlap = sum((Counter(prediction) & Counter(gold)).values())
        if not overlap:
            score = 0.0
        else:
            precision = overlap / len(prediction)
            recall = overlap / len(gold)
            score = 2 * precision * recall / (precision + recall)
        if score > best_score:
            best_score, best_reference = score, reference
    return best_score, [best_reference] if best_reference else []


def _generate_query_summary(model: str, question: str, history: list[tuple[str, str, str]], max_output_tokens: int) -> tuple[str, dict]:
    """Create a query-focused summary when an official document provides none."""
    document = "\n\n".join(_text(item) for item in history)
    started = time.perf_counter()
    response = OpenAI().responses.create(
        model=model,
        instructions="Create a concise, factual summary focused on answering the question. Preserve names, dates, comparisons, and uncertainty. Do not answer from outside the supplied document.",
        input=f"Question:\n{question}\n\nDocument:\n{document}",
        max_output_tokens=max_output_tokens,
    )
    return response.output_text, {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "latency": time.perf_counter() - started,
    }


OFFICIAL_DATASET = "Official LongBench · HotpotQA subset"
STRATEGIES = ["S0 · Baseline", "S1 · Full history", "S2 · Recent window", "S3 · Summary + recent", "S4 · Keyword retrieval"]
DEFAULT_STRATEGIES = {"S0 · Baseline", "S2 · Recent window", "S4 · Keyword retrieval"}


def longbench_dataset(case: dict) -> dict:
    return _longbench_case_dataset(case)


def context_budget(dataset: dict) -> int:
    return 16_000 if dataset.get("official") else 1_800


def run_strategy_benchmark(settings: ModelSettings, dataset: dict, instruction: str, strategies: list[str], case_key: str, progress=None) -> list[dict]:
    """Run one LLM call per strategy against the same dataset and score each answer."""
    history = dataset["history"]
    results = []
    summary = dataset["summary"]
    summary_metrics = None
    summary_error = None
    if "S3 · Summary + recent" in strategies and not summary:
        try:
            if progress:
                progress("Generating query-focused document summary…")
            summary, summary_metrics = _generate_query_summary(settings.model, instruction, history, settings.max_output_tokens)
            if not summary or not summary.strip():
                raise ValueError("The model returned an empty summary.")
        except Exception as exc:  # noqa: BLE001
            summary_error = str(exc)
    for strategy in strategies:
        if strategy == "S3 · Summary + recent" and summary_error:
            results.append({"case_key": case_key, "strategy": strategy, "error": f"Summary generation failed; this strategy was not run: {summary_error}", "context": None, "evidence_recall": None})
            continue
        built = build_benchmark_context(strategy, instruction, history, summary, context_budget(dataset))
        evidence = set(built["source_ids"]) & set(dataset["evidence_ids"])
        evidence_recall = len(evidence) / len(dataset["evidence_ids"]) if dataset["evidence_ids"] else None
        try:
            if progress:
                progress(f"Running {strategy}…")
            started = time.perf_counter()
            response_instruction = (
                "Answer only from the supplied context. Return only the short final answer; do not include reasoning, explanation, or citations. "
                "If the answer is absent, return exactly: Insufficient information."
                if dataset.get("official")
                else "Answer only from supplied context. Clearly identify missing information."
            )
            response = OpenAI().responses.create(model=settings.model, instructions=response_instruction, input=built["context"], max_output_tokens=settings.max_output_tokens)
            if dataset.get("official"):
                accuracy, facts = _longbench_f1(response.output_text, dataset["reference_answers"])
            else:
                correct, total, facts = _score(response.output_text, dataset["expected_facts"])
                accuracy = correct / total
            cost = settings.cost(response.usage.input_tokens, response.usage.output_tokens)
            if strategy == "S3 · Summary + recent" and summary_metrics:
                cost += settings.cost(summary_metrics["input_tokens"], summary_metrics["output_tokens"])
            results.append({"case_key": case_key, "strategy": strategy, "response": response.output_text, "context": built, "input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens, "latency": time.perf_counter() - started, "accuracy": accuracy, "facts": facts, "evidence_recall": evidence_recall, "cost": cost, "summary_metrics": summary_metrics if strategy == "S3 · Summary + recent" else None})
        except Exception as exc:  # noqa: BLE001
            results.append({"case_key": case_key, "strategy": strategy, "error": str(exc), "context": built, "evidence_recall": evidence_recall})
    return results
