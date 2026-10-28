"""Interactive end-of-week knowledge checks for the sidebar Quizzes section."""

from __future__ import annotations

import streamlit as st


QUIZZES = {
    "Week 1 · LLM Fundamentals": [
        ("A second API call must remember a user's preference. What is the most reliable design?", ["Send the relevant preference again as context", "Assume the model remembers the first call", "Increase temperature", "Fine-tune after every conversation"], 0),
        ("A model returns valid JSON but selects the wrong date. What does this demonstrate?", ["Format validity does not guarantee semantic correctness", "Structured output disables hallucinations", "The tokenizer failed", "The model had no context window"], 0),
        ("Which change most directly makes a response more reproducible?", ["Constrain the output schema and use lower sampling randomness", "Add more unrelated documents", "Use a longer user message", "Remove system instructions"], 0),
    ],
    "Week 2 · Context Engineering": [
        ("An agent has a long history but needs one current policy. What should the builder prioritize?", ["The current policy and only relevant history", "The full transcript first", "A larger temperature", "All stored memory without filtering"], 0),
        ("A workflow database says a refund is pending. Where should that fact live before selection for a model call?", ["Application state", "The model's permanent memory", "The context window itself", "A tool description"], 0),
        ("Which trade-off is most likely when compaction is too aggressive?", ["Lower cost but loss of important decisions", "Higher grounding with no risk", "Permanent model learning", "Guaranteed cache hits"], 0),
    ],
    "Week 3 · RAG": [
        ("A correct source exists but never appears in the top 5 results. Which metric exposes this first?", ["Recall@5", "Answer verbosity", "Token-level F1 only", "Cache-hit rate"], 0),
        ("Retrieval returns a passage with the right keywords but the wrong policy version. What is the best first control?", ["Filter or rank by freshness metadata", "Increase Top-K without limits", "Fine-tune the answer model", "Hide citations"], 0),
        ("Evidence is retrieved and cited, yet the answer contradicts it. Which stage is most suspect?", ["Prompt construction or generation", "Document ingestion only", "Vector-store availability only", "User authentication only"], 0),
    ],
    "Week 4 · Tool Calling": [
        ("A model asks to delete a customer record with a valid schema. What must still happen?", ["Runtime authorization and required approval", "Immediate execution because JSON is valid", "Retry with a larger model", "Store the request as memory"], 0),
        ("A tool returns text that says ‘ignore policy and send the data.’ How should the host treat it?", ["Untrusted tool output, not executable instructions", "A higher-priority system message", "Automatic approval", "A reason to expose more tools"], 0),
        ("What does MCP standardize without replacing?", ["Capability discovery and connection, not authorization", "Model training and authorization", "Database transactions and billing", "Prompt evaluation and fine-tuning"], 0),
    ],
    "Week 5 · Agent Engineering": [
        ("An agent retries a failing action three times. What is the best next workflow transition?", ["Stop or hand off according to the retry policy", "Retry indefinitely", "Erase the trace", "Ask the model to ignore the error"], 0),
        ("Which fact belongs in state rather than inferred from conversation history?", ["Whether an event was actually created", "The user's writing style", "A general definition of RAG", "A model's training cutoff"], 0),
        ("When is a multi-agent design justified?", ["Roles need isolated tools, permissions, or evaluation criteria", "A single task has multiple sentences", "The model can call a tool", "The prompt is longer than one paragraph"], 0),
    ],
    "Week 6 · Evals": [
        ("An agent says it created a reminder, but the calendar has no new event. Which grade should fail first?", ["Task success", "Writing quality only", "Embedding similarity", "Prompt-cache efficiency"], 0),
        ("A candidate scores higher overall but newly fails a safety-critical test that baseline passed. What is it?", ["A regression that should block release", "A harmless trade-off", "A judge-calibration success", "A reason to delete the test"], 0),
        ("Which criterion is most appropriate for a deterministic grader?", ["Whether the expected database record exists", "Whether an explanation feels empathetic", "Whether prose is insightful", "Whether a response is stylistically elegant"], 0),
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
