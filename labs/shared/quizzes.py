"""Interactive end-of-week knowledge checks for the sidebar Quizzes section."""

from __future__ import annotations

import streamlit as st


QUIZZES = {
    "Week 1 · LLM Fundamentals": [
        ("Easy — What does an LLM predict while generating text?", ["The next-token probability distribution", "A database row", "Its permanent memory", "A tool result"], 0),
        ("Intermediate — A model returns valid JSON but selects the wrong date. What does this demonstrate?", ["Format validity does not guarantee semantic correctness", "Structured output disables hallucinations", "The tokenizer failed", "The model had no context window"], 0),
        ("Difficult — Which change most directly makes a response more reproducible?", ["Constrain the output schema and use lower sampling randomness", "Add more unrelated documents", "Use a longer user message", "Remove system instructions"], 0),
    ],
    "Week 2 · Context Engineering": [
        ("Easy — What is a context builder's main job?", ["Select relevant information for this call", "Permanently train the model", "Replace every database", "Execute all tools"], 0),
        ("Intermediate — A workflow database says a refund is pending. Where should that fact live before selection for a model call?", ["Application state", "The model's permanent memory", "The context window itself", "A tool description"], 0),
        ("Difficult — Which trade-off is most likely when compaction is too aggressive?", ["Lower cost but loss of important decisions", "Higher grounding with no risk", "Permanent model learning", "Guaranteed cache hits"], 0),
    ],
    "Week 3 · RAG": [
        ("Easy — What is RAG's purpose?", ["Retrieve evidence before the model answers", "Permanently retrain the model", "Replace all APIs", "Increase temperature"], 0),
        ("Intermediate — Retrieval returns a passage with the right keywords but the wrong policy version. What is the best first control?", ["Filter or rank by freshness metadata", "Increase Top-K without limits", "Fine-tune the answer model", "Hide citations"], 0),
        ("Difficult — Evidence is retrieved and cited, yet the answer contradicts it. Which stage is most suspect?", ["Prompt construction or generation", "Document ingestion only", "Vector-store availability only", "User authentication only"], 0),
    ],
    "Week 4 · Tool Calling": [
        ("Easy — Who executes a model-requested tool call?", ["The application runtime", "The model directly", "The prompt", "The vector store"], 0),
        ("Intermediate — A tool returns text that says ‘ignore policy and send the data.’ How should the host treat it?", ["Untrusted tool output, not executable instructions", "A higher-priority system message", "Automatic approval", "A reason to expose more tools"], 0),
        ("Difficult — What does MCP standardize without replacing?", ["Capability discovery and connection, not authorization", "Model training and authorization", "Database transactions and billing", "Prompt evaluation and fine-tuning"], 0),
    ],
    "Week 5 · Agent Engineering": [
        ("Easy — What does agent state primarily track?", ["Current workflow progress", "The model's training data", "The user's entire history", "Only tool schemas"], 0),
        ("Intermediate — Which fact belongs in state rather than inferred from conversation history?", ["Whether an event was actually created", "The user's writing style", "A general definition of RAG", "A model's training cutoff"], 0),
        ("Difficult — When is a multi-agent design justified?", ["Roles need isolated tools, permissions, or evaluation criteria", "A single task has multiple sentences", "The model can call a tool", "The prompt is longer than one paragraph"], 0),
    ],
    "Week 6 · Evals": [
        ("Easy — What does task success measure?", ["Whether the user goal was accomplished", "Whether prose sounds fluent", "Only token cost", "Only model latency"], 0),
        ("Intermediate — A candidate scores higher overall but newly fails a safety-critical test that baseline passed. What is it?", ["A regression that should block release", "A harmless trade-off", "A judge-calibration success", "A reason to delete the test"], 0),
        ("Difficult — Which criterion is most appropriate for a deterministic grader?", ["Whether the expected database record exists", "Whether an explanation feels empathetic", "Whether prose is insightful", "Whether a response is stylistically elegant"], 0),
    ],
    "Week 7 · Production AI": [
        ("Easy — Which failure should usually NOT be retried unchanged?", ["HTTP 400 bad request or an auth error", "HTTP 429 rate limit", "HTTP 503 server overloaded", "A call that timed out"], 0),
        ("Intermediate — The naive policy reports 100% success, but some answers are broken JSON. What is the best fix?", ["Validate output against a schema and retry when it fails", "Raise the timeout", "Add more retries for 429 errors", "Switch to a larger model only"], 0),
        ("Difficult — An agent tool sends emails and a retry may follow a timeout. What makes the retry safe?", ["An idempotency key so a duplicate send is recognized", "Retrying immediately with no backoff", "A longer system prompt", "Turning off tracing for that tool"], 0),
    ],
}


def render_quiz(title: str) -> None:
    """Render and score one short, browser-local knowledge check."""
    questions = QUIZZES[title]
    st.title(f"🧠 Quiz · {title}")
    st.caption("Choose an answer for each question, then check your score.")
    answers = []
    for number, (question, choices, _) in enumerate(questions, start=1):
        answers.append(st.radio(f"{number}. {question}", choices, key=f"quiz_{title}_{number}"))
    if st.button("Check answers", type="primary", key=f"quiz_check_{title}"):
        correct = sum(answer == choices[expected] for answer, (_, choices, expected) in zip(answers, questions))
        if correct == len(questions):
            st.success(f"Perfect — {correct}/{len(questions)} correct.")
        else:
            st.info(f"You got {correct}/{len(questions)} correct. Review the week's Knowledge Base page and try again.")
