"""Week 2 page: context engineering. What does the model actually see?

Run alone:   streamlit run labs/week2_context_engineering/page.py
In the site: streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Lets this page run on its own (streamlit run labs/<lab>/page.py) as well as inside app.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from labs.shared.ui import (can_run, lab_parameters, mini_muse_part, model_settings, page_layout,
                            run_standalone, show_error)
from labs.week2_context_engineering import strategy_benchmark as bench

# Short names for the five strategies, in order, and what each sends.
STRATEGIES = {
    "None": ("S0 · Baseline", "Only the question. No conversation."),
    "Everything": ("S1 · Full history", "Every earlier message, word for word."),
    "Last 5": ("S2 · Recent window", "Only the five most recent messages."),
    "Summary + last 4": ("S3 · Summary + recent", "A short summary of older messages, plus the last four."),
    "Keyword search": ("S4 · Keyword retrieval", "The five messages that share the most words with the question."),
}
SHORT = {code: short for short, (code, _) in STRATEGIES.items()}

HOW_IT_WORKS = """
The model remembers nothing between calls. Everything it knows about the conversation has to be **put into the context** on each call, and **context engineering** is deciding what goes in.

1. Choose a **sample conversation** in Lab parameters: a past chat between a user and an assistant, with a question asked at the end. Some facts change along the way (for example, a timeout corrected from 30 to 60 seconds), and some messages are off-topic.
2. Pick a **strategy**. The page shows at once which messages it keeps (✅) and which it drops. ⭐ marks the messages that hold the facts the question needs. This part is free: nothing is sent yet.
3. **Ask** with that strategy, or **compare all five**. Each answer is checked against the expected facts, with its tokens and cost.

Look for the trade-off: more context finds more facts but costs more on every call, and the latest version of a changed fact is the one that matters.
"""


def _label(name: str) -> str:
    return name.removeprefix("Quick scenario · ")


def render() -> None:
    main, panel = page_layout("Week 2 · Context engineering")
    if mini_muse_part(main, panel, 2,
                      caption="The model only knows what you put in its context. Choose what goes in, and see what it changes.",
                      how_it_works=HOW_IT_WORKS):
        return
    settings = model_settings(panel)
    with lab_parameters(panel):
        scenario = st.selectbox("Sample conversation", list(bench.DATASETS), format_func=_label, key="week2_scenario",
                                help="A past chat, plus a question asked at the end of it.")
    dataset = bench.DATASETS[scenario]
    history, needed, facts = dataset["history"], set(dataset["evidence_ids"]), list(dataset["expected_facts"])

    with main:
        question = st.text_area("Question", dataset["instruction"], key=f"week2_question_{scenario}", height=80)
        short = st.segmented_control("Context strategy", list(STRATEGIES), default="Last 5", key="week2_strategy") \
            or "Last 5"
        code, what = STRATEGIES[short]
        built = bench.build_benchmark_context(code, question, history, dataset["summary"], bench.context_budget(dataset))
        kept = set(built["source_ids"])

        seen, answer_col = st.columns([3, 2], gap="large")
        # What the model will see: free, instant, before any call
        with seen, st.container(border=True):
            st.markdown(f"**What the model will see** · {what}")
            st.caption(f"{len(kept & {m[0] for m in history})} of {len(history)} messages · "
                       f"{len(kept & needed)} of {len(needed)} ⭐ needed messages · ~{built['estimated_tokens']} tokens")
            if "summary" in kept:
                st.markdown(f"✅ 📝 *Summary of older messages:* {dataset['summary']}")
            for message_id, role, text in history:
                star = " ⭐" if message_id in needed else ""
                if message_id in kept:
                    st.markdown(f"✅ `{message_id}` {role}: {text}{star}")
                else:
                    st.markdown(f":gray[⬜ {message_id} {role}: ~~{text}~~]{star}")
            st.caption("✅ sent · ⬜ left out · ⭐ holds a fact the question needs")

        with answer_col:
            run_one = st.button(f"Ask with “{short}”", type="primary", width="stretch", key="week2_ask")
            run_all = st.button("Compare all five", width="stretch", key="week2_compare",
                                help="Five API calls, one per strategy.")
            if (run_one or run_all) and can_run(settings, question):
                chosen = [c for c, _ in STRATEGIES.values()] if run_all else [code]
                status = st.empty()
                try:
                    results = bench.run_strategy_benchmark(settings, dataset, question, chosen, scenario,
                                                           progress=lambda text: status.caption(text))
                    st.session_state.week2_result = {"scenario": scenario, "results": results}
                except Exception as exc:  # noqa: BLE001
                    show_error("Model call", exc)
                status.empty()
            saved = st.session_state.get("week2_result")
            single = saved and saved["scenario"] == scenario and len(saved["results"]) == 1
            if single:
                _single(saved["results"][0], facts)
            else:
                st.caption("Pick a strategy, check what it keeps, then ask. The answer appears here.")

        if saved and saved["scenario"] == scenario and len(saved["results"]) > 1:
            _scoreboard(saved["results"], facts)


def _checks(result: dict, facts: list[str]) -> dict:
    found = set(result.get("facts", []))
    return {fact: ("✓" if fact in found else "✗") for fact in facts}


def _single(result: dict, facts: list[str]) -> None:
    with st.container(border=True):
        st.markdown(f"**Answer with “{SHORT.get(result['strategy'], result['strategy'])}”**")
        if "error" in result:
            st.error(result["error"])
            return
        st.info(result["response"] or "No text returned.")
        st.dataframe([{"Expected fact": f, "Found": mark} for f, mark in _checks(result, facts).items()],
                     width="stretch", hide_index=True)
        st.caption(f"{len(result['facts'])} of {len(facts)} facts · {result['input_tokens']} input tokens · "
                   f"${result['cost']:.5f}")


def _scoreboard(results: list[dict], facts: list[str]) -> None:
    with st.container(border=True):
        st.markdown("**All five strategies, same question**")
        st.dataframe([{"Strategy": SHORT.get(r["strategy"], r["strategy"]),
                       **({f: "error" for f in facts} if "error" in r else _checks(r, facts)),
                       "Facts found": "—" if "error" in r else f"{len(r['facts'])} / {len(facts)}",
                       "Input tokens": str(r.get("input_tokens", "—")),
                       "Cost": f"${r['cost']:.5f}" if "cost" in r else "—"} for r in results],
                     width="stretch", hide_index=True)
        for tab, r in zip(st.tabs([SHORT.get(r["strategy"], r["strategy"]) for r in results]), results):
            with tab:
                if "error" in r:
                    st.error(r["error"])
                else:
                    st.info(r["response"] or "No text returned.")


if __name__ == "__main__":
    run_standalone(render, "Week 2 · Context engineering")
