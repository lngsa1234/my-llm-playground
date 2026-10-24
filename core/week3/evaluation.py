"""Week 3 core logic: RAG datasets and benchmark scoring (Evidence Recall@K, exact match, token F1)."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from core.week3.rag import ABSTENTION, generate_with_rag, retrieve

ROOT = Path(__file__).resolve().parents[2]
RETRIEVAL_PIPELINE_VERSION = "hybrid-title-neighbors-v7"

DATASETS = {
    "HotpotQA mini · multi-hop": {
        "knowledge_base": ROOT / "rag_corpus" / "hotpotqa_mini",
        "benchmark": ROOT / "benchmark" / "rag" / "hotpotqa_mini_questions.json",
        "description": "50 official HotpotQA development questions over 198 Wikipedia articles. Each question needs two supporting articles.",
        "default_question": "What government position was held by the woman who portrayed Corliss Archer in the film Kiss and Tell?",
    },
    "NovaTech starter · single-hop": {
        "knowledge_base": ROOT / "rag_corpus" / "novatech",
        "benchmark": ROOT / "benchmark" / "rag" / "questions.json",
        "description": "Ten fictional company-policy documents for a smaller, single-hop introduction.",
        "default_question": "How long do Pro customers have to request their money back?",
    },
}


def build_stamp() -> str:
    """Identify the code revision this process loaded, to debug stale deployments."""
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True, timeout=1,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        revision = "git-unavailable"
    digest = hashlib.sha256()
    for file in (ROOT / "core" / "week3" / "rag.py", Path(__file__)):
        digest.update(file.read_bytes())
    return f"Loaded {revision} · code {digest.hexdigest()[:8]} · RAG {RETRIEVAL_PIPELINE_VERSION}"


LOADED_BUILD_STAMP = build_stamp()


def load_questions(benchmark_file: Path) -> list[dict]:
    return json.loads(Path(benchmark_file).read_text(encoding="utf-8"))


def expected_answer(benchmark_file: Path, question: str) -> str | None:
    """Return the reference answer when the playground question is in the benchmark."""
    return next((item["expected_answer"] for item in load_questions(benchmark_file) if item["question"] == question), None)


def expected_found(item: dict, results: list[dict]) -> bool | None:
    """True when every gold evidence document appears in the retrieved chunks; None if unanswerable."""
    evidence = item["evidence"]
    if evidence is None:
        return None
    expected_sources = {evidence} if isinstance(evidence, str) else set(evidence)
    return expected_sources.issubset({result["source"] for result in results})


def _normalize_answer(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _answer_before_sources(text: str) -> str:
    return re.split(r"\n\s*sources?\s*:", text, maxsplit=1, flags=re.IGNORECASE)[0]


def answer_scores(answer: str, expected: str) -> tuple[float, float]:
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


def run_rag_benchmark(index, questions: list[dict], model: str, top_k: int, threshold: float,
                      generate_answers: bool, progress=None) -> list[dict]:
    """Retrieve (and optionally answer) every benchmark question; return one row per question."""
    rows = []
    for position, item in enumerate(questions, start=1):
        results, latency, _ = retrieve(index, item["question"], top_k)
        answer = generate_with_rag(model, item["question"], results, threshold) if generate_answers else None
        evidence_found = expected_found(item, results)
        exact_match = f1 = None
        if answer:
            expected = item["expected_answer"].lower()
            if expected != "not_found":
                exact_match, f1 = answer_scores(answer["text"], expected)
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
        if progress:
            progress(position, len(questions))
    return rows


def summarize_benchmark(rows: list[dict]) -> dict:
    evaluable = [row for row in rows if row["Evidence found"] != "N/A"]
    answers = [row for row in rows if row["Exact match"] != "—"]
    f1 = [float(row["Token F1"].strip("%")) / 100 for row in rows if row["Token F1"] != "—"]
    return {
        "evidence_recall": sum(row["Evidence found"] == "✓" for row in evaluable) / len(evaluable) if evaluable else 0.0,
        "exact_match": sum(float(row["Exact match"].strip("%")) / 100 for row in answers) / len(answers) if answers else None,
        "mean_f1": sum(f1) / len(f1) if f1 else None,
    }
