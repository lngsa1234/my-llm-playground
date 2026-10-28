"""Interactive end-of-week knowledge checks for the sidebar Quizzes section."""

from __future__ import annotations

import streamlit as st


QUIZZES = {
    "Week 1 · LLM Fundamentals": [
        ("What does an LLM predict while generating text?", ["The next-token probability distribution", "A database row", "Its permanent memory"], 0),
        ("Who supplies relevant history for a later stateless API call?", ["The application", "The model automatically", "The tokenizer"], 0),
        ("When is structured output most useful?", ["When software needs typed fields", "When writing poetry", "When increasing randomness"], 0),
    ],
    "Week 2 · Context Engineering": [
        ("What is a context builder's main job?", ["Select relevant information for this call", "Permanently train the model", "Replace every database"], 0),
        ("Why can more context hurt performance?", ["It can bury evidence in noise", "It makes facts permanent", "It disables tools"], 0),
        ("What tracks current workflow progress?", ["State", "The context window", "Temperature"], 0),
    ],
    "Week 3 · RAG": [
        ("What must happen before a grounded RAG answer?", ["Retrieve relevant evidence", "Fine-tune the model", "Clear all history"], 0),
        ("What does Recall@K check?", ["Required evidence is among the first K results", "The response length", "The number of documents indexed"], 0),
        ("If evidence was retrieved but the answer is wrong, inspect:", ["Prompt and reasoning", "Only the embedding model", "Only the user interface"], 0),
    ],
    "Week 4 · Tool Calling": [
        ("Who actually executes a requested tool call?", ["The application runtime", "The LLM directly", "The prompt"], 0),
        ("What should happen before a sensitive action?", ["Authorization and, when required, approval", "Automatic execution", "A longer model response"], 0),
        ("What is MCP?", ["A standard connection protocol", "A replacement for authorization", "An LLM model"], 0),
    ],
    "Week 5 · Agent Engineering": [
        ("When should a deterministic route be preferred?", ["For known rules and safety boundaries", "Never", "Only after five failures"], 0),
        ("Which is a valid agent termination condition?", ["Budget exhausted", "The model is curious", "A prompt gets longer"], 0),
        ("When might a specialist agent help?", ["It needs distinct tools or permissions", "It has a different name", "Every task has two steps"], 0),
    ],
    "Week 6 · Evals": [
        ("What does task success measure?", ["Whether the user goal was accomplished", "Whether prose sounds fluent", "Only token cost"], 0),
        ("When should a deterministic check be preferred?", ["When behavior is directly observable", "Never", "Only for creative tasks"], 0),
        ("What is a regression?", ["A previously passing case now fails", "A new feature", "A high judge score"], 0),
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
