"""Week 4 page: tool calling. The model asks for a tool; the app runs it and sends back the result.

Run alone:   streamlit run labs/week4_tool_calling/page.py
In the site: streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Lets this page run on its own (streamlit run labs/<lab>/page.py) as well as inside app.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json

import streamlit as st

from labs.shared.ui import (can_run, example_text_area, get_model_settings, lab_parameters, mini_muse_part,
                            page_layout, run_standalone, show_error, usage_line)
from labs.week4_tool_calling import weather

TOOLS = {t["function"]["name"]: t for t in (weather.WEATHER_TOOL, weather.WEEKEND_FORECAST_TOOL)}

HOW_IT_WORKS = """
A model can't look anything up by itself: it only writes text. **Tool calling** lets it ask the app to run a function, here a live weather lookup, and then answer from the real result.

**Question → model picks a tool → app runs it → result back to the model → answer**

| Step | What happens | You control | See it in |
|---|---|---|---|
| 1. Offer tools | Each tool is described to the model: a name, what it does, and its inputs | Tools offered | The two tools (below) |
| 2. Choose | The model reads the question and replies with a **tool call** (a tool name and its inputs, such as `location: "Detroit"`) instead of an answer | Model | What happened with tools |
| 3. Run | The **app**, not the model, runs the function: it calls the Open-Meteo weather service | — | What happened → Result |
| 4. Answer | The result goes back to the model, which may ask for more tools or write the answer | Max tool-call rounds | With tools |

**The two tools**
- `get_weather(location)`: current temperature and feels-like temperature.
- `get_weekend_forecast(location)`: rain chance and high for the coming Saturday and Sunday.

**Try this**
- Ask the hiking question. Without tools the model can't know the forecast; with tools it compares real Saturday and Sunday numbers.
- Untick `get_weekend_forecast` in **Tools offered** and ask the same question. What does the model do with only current weather?
- Ask about two cities at once, then set **Max tool-call rounds** to 1 and ask again.
- Ask "Do not look up weather: why are coastal cities milder?" The right choice is no tool at all.

The same tools also run through **MCP** (a standard way to share tools between apps): see `weather_mcp_server.py` and `mcp_client_demo.py` in this lab's folder.
"""


def render() -> None:
    main, panel = page_layout("Week 4 · Tool calling")
    if mini_muse_part(main, panel, 4,
                      caption="Let the model ask the app to run a function, here a live weather lookup, and answer from the result.",
                      how_it_works=HOW_IT_WORKS):
        return
    settings = get_model_settings()
    with lab_parameters(panel):
        offered = st.multiselect("Tools offered", list(TOOLS), list(TOOLS), key="week4_tools",
                                 help="Remove a tool to see what the model does without it.")
        max_rounds = int(st.slider("Max tool-call rounds", 1, 10, 5, key="week4_max_rounds",
                                   help="How many times the model may ask for tools before the run stops."))

    with main:
        _render_ask(settings, offered, max_rounds)


def _cost(settings, result: dict) -> float:
    return settings.cost(result.get("input_tokens", 0), result.get("output_tokens", 0))


def _render_ask(settings, offered: list[str], max_rounds: int) -> None:
    examples = [weather.DEFAULT_PROMPT] + [case["prompt"] for case in weather.LIVE_BENCHMARKS]
    prompt = example_text_area("Question", examples, "week4", height=80)
    if st.button("Ask with and without tools", type="primary", key="week4_run") and can_run(settings, prompt):
        try:
            with st.spinner("Asking without tools, then with tools…"):
                plain = weather.run_direct_agent(prompt, settings.model, use_tools=False,
                                                 max_output_tokens=settings.max_output_tokens)
                tooled = weather.run_direct_agent(prompt, settings.model, max_tool_rounds=max_rounds,
                                                  max_output_tokens=settings.max_output_tokens, tools=offered)
            st.session_state.week4_ask = {"prompt": prompt, "plain": plain, "tooled": tooled, "offered": offered}
        except Exception as exc:  # noqa: BLE001
            show_error("Model call", exc)

    saved = st.session_state.get("week4_ask")
    if not saved or saved["prompt"] != prompt:
        st.caption("Ask a question to compare the two answers and see each tool call.")
        return
    without, with_tools = st.columns(2, gap="large")
    for column, title, result in ((without, "Without tools", saved["plain"]), (with_tools, "With tools", saved["tooled"])):
        with column, st.container(border=True):
            st.markdown(f"**{title}**")
            st.markdown(result["answer"])
            usage_line(result.get("input_tokens", 0), result.get("output_tokens", 0), result["latency"], _cost(settings, result))

    tooled = saved["tooled"]
    with st.container(border=True):
        st.markdown("**Tool-use timeline**")
        st.caption(f"{len(tooled['trace'])} tool call{'s' * (len(tooled['trace']) != 1)} · "
                   f"{tooled.get('model_calls', '?')} model calls · tools offered: {', '.join(saved['offered']) or 'none'}")
        if "calls" not in tooled:  # saved before model-call details were recorded
            st.caption("Ask again to see each model call.")
            return
        st.markdown("**Start · Your question**")
        st.info(saved["prompt"])
        runs = {}  # tool results, grouped by the model call that asked for them
        for entry in tooled["trace"]:
            runs.setdefault(entry.get("round"), []).append(entry)
        for call in tooled["calls"]:
            _timeline_step(call, runs.get(call["call"], []))


def _timeline_step(call: dict, tool_runs: list[dict]) -> None:
    returned = call["returned"]
    if "tool_calls" in returned:
        st.markdown(f"**Step {call['call']} · Model chooses what information it needs**")
        st.caption("The model cannot look up live weather itself, so it asks the app to run a tool.")
        for requested in returned["tool_calls"]:
            st.code(f"{requested['tool']}({_args(requested['arguments'])})", language=None)
        st.markdown("**App runs the requested tool**")
        for entry in tool_runs:
            _tool_result(entry)
    else:
        st.markdown(f"**Step {call['call']} · Model writes the final answer**")
        st.success(returned.get("answer") or "No visible answer was returned.")
    st.caption(f"Model call {call['call']} · {call['input_tokens']:,} input tokens · "
               f"{call['output_tokens']:,} output tokens · {call['seconds']:.2f} s")
    with st.expander("Inspect the raw API request and response"):
        st.caption("This is the technical version of the step: the conversation and tool definitions sent to the model, then its response.")
        st.markdown("Request")
        st.json(call.get("request") or {"messages": call["messages"]}, expanded=2)
        st.markdown("Response")
        st.json(call.get("response") or call["returned"], expanded=2)


def _tool_result(entry: dict) -> None:
    result = entry["result"]
    if "error" in result:
        st.error(f"`{entry['tool']}({_args(entry['arguments'])})` failed: {result['error']}")
        return
    st.success(_result_summary(entry))


def _result_summary(entry: dict) -> str:
    """Translate the weather tool's result into the one thing the learner needs to know."""
    result = entry["result"]
    location = result.get("location", "the requested location")
    if "forecast" in result:
        days = [f"{day['day']}: high {day['high_f']}°F, {day['precipitation_probability_max']}% rain chance"
                for day in result["forecast"]]
        return f"The app returned the weekend forecast for {location}: " + "; ".join(days) + "."
    if "temperature_f" in result:
        return f"The app returned current weather for {location}: {result['temperature_f']}°F, feels like {result['feels_like_f']}°F."
    return f"The app ran `{entry['tool']}` and returned data for {location}."


def _args(raw: str) -> str:
    try:
        args = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return str(raw)
    return ", ".join(f'{k}="{v}"' for k, v in args.items())


if __name__ == "__main__":
    run_standalone(render, "Week 4 · Tool calling")
