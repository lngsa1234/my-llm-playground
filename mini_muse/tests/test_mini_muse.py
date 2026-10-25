"""Offline tests for Mini Muse. A scripted fake model stands in for the API."""

from __future__ import annotations

import json

import pytest

from mini_muse import week1_understand, week2_memory, week3_knowledge, week4_tools, week5_agent, week6_eval
from mini_muse.llm import Reply, ToolCall, Usage, parse_arguments
from mini_muse.week7_reliability import Runtime
from mini_muse.week8_assistant import MiniMuse
from mini_muse.world import WORLD_TEMPLATE, new_world


class FakeLLM:
    """Replays scripted replies. A reply may be a Reply, a string, or a function of the messages."""

    model = "fake-model"

    def __init__(self, replies=(), parsed=None):
        self.replies = list(replies)
        self.parsed = parsed or {}
        self.usage = Usage()
        self.seen: list[list[dict]] = []

    def chat(self, messages, tools=None, model=None):
        self.seen.append([dict(m) for m in messages])
        self.usage.add(10, 5)
        reply = self.replies.pop(0)
        reply = reply(messages) if callable(reply) else reply
        return Reply(content=reply) if isinstance(reply, str) else reply

    def parse(self, instructions, text, schema):
        self.usage.add(10, 5)
        value = self.parsed[schema.__name__]
        return value(text) if callable(value) else value

    def embed(self, texts):
        words = ["budget", "venue", "hotel", "train", "book", "dumplings", "maya", "roadmap"]
        return [[float(w in t.lower()) + 0.01 for w in words] for t in texts]


def call(name, n=1, /, **args):
    return ToolCall(f"call_{name}_{n}", name, json.dumps(args))


def tools_reply(*calls):
    return Reply(tool_calls=list(calls))


# ------------------------------------------------------------------ world + tools
def test_world_matches_week6_golden_dataset_world():
    from labs.week6_agent_eval.evals import agent as simulated

    for key in ("weather", "contacts"):
        assert WORLD_TEMPLATE[key] == simulated.WORLD_TEMPLATE[key]
    for day, events in simulated.WORLD_TEMPLATE["calendar"].items():
        assert WORLD_TEMPLATE["calendar"][day] == events


def test_new_world_is_independent():
    w = new_world()
    w["calendar"]["2026-10-28"].append({"title": "x", "time": "1:00"})
    assert new_world()["calendar"]["2026-10-28"] == []


def test_tools_act_on_fake_world_and_report_errors():
    w = new_world()
    assert week4_tools.execute(w, "get_weather", {"city": "detroit"})["temp_f"] == 48
    assert "error" in week4_tools.execute(w, "get_weather", {"city": "Paris"})
    assert week4_tools.execute(w, "lookup_contact", {"name": "Maya"})["email"] == "maya@example.com"
    assert week4_tools.execute(w, "calculator", {"expression": "85 * 20 / 100"})["result"] == 17
    assert "error" in week4_tools.execute(w, "calculator", {"expression": "__import__('os')"})
    assert "error" in week4_tools.execute(w, "nope", {})
    assert "error" in week4_tools.execute(w, "check_calendar", {"day": "x"})
    week4_tools.execute(w, "create_event", {"title": "Yoga", "date": "2026-10-28", "time": "18:00"})
    assert w["events_created"] == [{"title": "Yoga", "date": "2026-10-28", "time": "18:00"}]
    found = week4_tools.execute(w, "search_notes", {"query": "offsite budget"})
    assert "4,000" in found["results"][0]["text"]


def test_parse_arguments_handles_bad_json():
    assert parse_arguments('{"a": 1}') == ({"a": 1}, None)
    assert parse_arguments("{oops")[1]
    assert parse_arguments("[1]")[1]


def test_every_schema_is_strict_and_named():
    for name, schema in week4_tools.SCHEMAS.items():
        fn = schema["function"]
        assert fn["name"] == name
        assert set(fn["parameters"]["required"]) == set(fn["parameters"]["properties"])


# ------------------------------------------------------------------ week 1
def test_understand_sends_today_and_returns_structure():
    req = week1_understand.UnderstoodRequest(intent="schedule", summary="Lunch with Maya", title="Lunch",
                                       date="2026-10-27", time="12:00", city=None, people=["Maya"], missing_info=[])
    llm = FakeLLM(parsed={"UnderstoodRequest": req})
    assert week1_understand.understand(llm, "Lunch with Maya Tuesday noon").date == "2026-10-27"
    assert "2026-10-26" in week1_understand.instructions()


# ------------------------------------------------------------------ week 2
def test_memory_context_has_facts_and_only_recent_turns():
    m = week2_memory.Memory(facts=["Prefers mornings"], summary="Planned the offsite.")
    for i in range(10):
        m.history += [{"role": "user", "content": f"u{i}"}, {"role": "assistant", "content": f"a{i}"}]
    ctx = week2_memory.build_context(m, "new", max_turns=2)
    assert "Prefers mornings" in ctx[0]["content"] and "Planned the offsite" in ctx[0]["content"]
    assert [x["content"] for x in ctx[1:]] == ["u8", "a8", "u9", "a9", "new"]
    assert week2_memory.build_context(m, "new", max_turns=0)[1:] == [{"role": "user", "content": "new"}]


def test_chat_learns_facts_once_and_round_trips(tmp_path):
    facts = week2_memory.LearnedFacts(new_facts=["Prefers morning meetings"])
    llm = FakeLLM(replies=["Noted!", "How about 9:00?"], parsed={"LearnedFacts": facts})
    m = week2_memory.Memory()
    assert week2_memory.chat(llm, m, "I prefer morning meetings")["new_facts"] == ["Prefers morning meetings"]
    assert week2_memory.chat(llm, m, "When should I meet Maya?")["new_facts"] == []
    assert m.facts == ["Prefers morning meetings"]
    assert "Prefers morning meetings" in llm.seen[1][0]["content"]
    m.save(tmp_path / "m.json")
    assert week2_memory.Memory.load(tmp_path / "m.json") == m


def test_compact_moves_old_turns_into_summary():
    llm = FakeLLM(parsed={"Summary": week2_memory.Summary(summary="They discussed lunch.")})
    m = week2_memory.Memory(history=[{"role": "user", "content": str(i)} for i in range(8)])
    assert week2_memory.compact(llm, m, keep_turns=1)
    assert m.summary == "They discussed lunch." and len(m.history) == 2
    assert not week2_memory.compact(llm, m, keep_turns=1)


# ------------------------------------------------------------------ week 3
def test_notes_are_chunked_by_section():
    chunks = week3_knowledge.load_chunks()
    labels = {c.label for c in chunks}
    assert "Team offsite planning › Budget" in labels
    assert all(c.text for c in chunks)


@pytest.mark.parametrize("question, source", [
    ("What did Jordan say about the offsite budget?", "Team offsite planning › Budget"),
    ("Which hotel am I staying at in Chicago?", "Chicago trip › Hotel"),
    ("How long do I boil the dumplings?", "Home and errands › Dumplings (Grandma's recipe)"),
])
def test_keyword_search_finds_the_right_section(question, source):
    index = week3_knowledge.build_index()
    assert week3_knowledge.search(index, question, k=3)[0]["source"] == source


def test_semantic_and_hybrid_search_with_embeddings():
    llm = FakeLLM()
    index = week3_knowledge.build_index(llm)
    assert index.semantic
    for mode in ("semantic", "hybrid"):
        results = week3_knowledge.search(index, "hotel", k=2, mode=mode, llm=llm)
        assert results[0]["mode"] == mode and "Chicago" in results[0]["source"]
    # Without embeddings, semantic search falls back to keyword search.
    assert week3_knowledge.search(week3_knowledge.build_index(), "hotel", mode="semantic")[0]["mode"] == "keyword"


def test_grounded_answer_puts_sources_in_prompt():
    llm = FakeLLM(replies=["$4,000 [Team offsite planning › Budget]"])
    result = week3_knowledge.answer(llm, week3_knowledge.build_index(), "offsite budget")
    assert "4,000" in llm.seen[0][0]["content"] and week3_knowledge.NOT_FOUND in llm.seen[0][0]["content"]
    assert result["results"]


# ------------------------------------------------------------------ week 4
def test_one_round_of_tools_runs_the_tool_then_answers():
    llm = FakeLLM([tools_reply(call("get_weather", city="Detroit")), "48°F and light rain."])
    trace = week4_tools.answer_with_tools(llm, "Weather in Detroit?")
    assert trace["tool_calls"][0]["result"]["temp_f"] == 48
    assert trace["messages"][-1]["role"] == "tool"
    assert trace["answer"] == "48°F and light rain."


def test_one_round_sends_email_without_asking():
    """The Week 4 limitation that Week 5 fixes."""
    llm = FakeLLM([tools_reply(call("send_email", to="maya@example.com", subject="Hi", body="Hi")), "Sent."])
    assert len(week4_tools.answer_with_tools(llm, "Email Maya")["final_state"]["emails_sent"]) == 1


# ------------------------------------------------------------------ week 5
def test_agent_checks_then_books_then_stops():
    llm = FakeLLM([
        tools_reply(call("check_calendar", date="2026-10-28")),
        tools_reply(call("create_event", title="Yoga", date="2026-10-28", time="18:00")),
        "Booked Yoga on 2026-10-28 at 18:00.",
    ])
    trace = week5_agent.run(llm, "Schedule yoga on 2026-10-28 at 18:00")
    assert [c["tool"] for c in trace["tool_calls"]] == ["check_calendar", "create_event"]
    assert trace["status"] == "done" and len(trace["steps"]) == 3
    assert len(trace["final_state"]["events_created"]) == 1


def test_agent_holds_email_for_approval_then_approve_sends():
    llm = FakeLLM([
        tools_reply(call("lookup_contact", name="maya")),
        tools_reply(call("send_email", to="maya@example.com", subject="Agenda", body="Hi Maya")),
        "Here's the draft. Should I send it?",
    ])
    trace = week5_agent.run(llm, "Email Maya about the agenda")
    assert trace["final_state"]["emails_sent"] == []
    assert trace["pending_actions"] == [{"tool": "send_email", "args": {"to": "maya@example.com",
                                                                        "subject": "Agenda", "body": "Hi Maya"}}]
    assert "send_email" not in [c["tool"] for c in trace["tool_calls"]]
    week5_agent.approve(trace["world"], trace["pending_actions"][0])
    assert len(trace["world"]["emails_sent"]) == 1


def test_agent_stops_at_max_steps():
    llm = FakeLLM([tools_reply(call("check_calendar", n=i, date="2026-10-28")) for i in range(3)])
    trace = week5_agent.run(llm, "loop forever", max_steps=3)
    assert trace["status"] == "max_steps" and "3 steps" in trace["answer"]


def test_agent_recovers_from_bad_arguments_and_unavailable_tools():
    llm = FakeLLM([
        tools_reply(ToolCall("c1", "check_calendar", "{bad json"), call("search_notes", query="x")),
        "Sorry.",
    ])
    trace = week5_agent.run(llm, "x")
    results = [c["result"] for c in trace["steps"][0]["calls"]]
    assert "valid JSON" in results[0]["error"] and "not available" in results[1]["error"]


def test_agent_includes_context_and_extra_system_text():
    llm = FakeLLM(["Hi"])
    week5_agent.run(llm, "hello", context=[{"role": "user", "content": "earlier"}], system_extra="Likes tea")
    assert "Likes tea" in llm.seen[0][0]["content"] and llm.seen[0][1]["content"] == "earlier"


# ------------------------------------------------------------------ week 7
def test_flaky_tool_is_retried_and_traced():
    rt = Runtime(max_retries=2, faults={"get_weather": "flaky"})
    result = rt.call_tool(week4_tools.execute, new_world(), "get_weather", {"city": "Detroit"})
    assert result["temp_f"] == 48
    assert [(s.attempt, s.ok) for s in rt.tracer.spans] == [(1, False), (2, True)]


def test_down_tool_returns_error_after_retries():
    rt = Runtime(max_retries=1, faults={"get_weather": "down"})
    result = rt.call_tool(week4_tools.execute, new_world(), "get_weather", {"city": "Detroit"})
    assert "failed after 2 attempts" in result["error"] and rt.tracer.summary()["errors"] == 2


def test_slow_tool_times_out_without_really_waiting():
    waits = []
    rt = Runtime(faults={"check_calendar": "slow"}, tool_timeout_s=0.1, slow_tool_s=5, sleep=waits.append)
    assert "timed out" in rt.call_tool(week4_tools.execute, new_world(), "check_calendar", {"date": "2026-10-28"})["error"]
    assert waits == [0.1]


def test_llm_falls_back_to_second_model():
    rt = Runtime(llm_fault="down", fallback_model="backup")
    llm = FakeLLM(["ok"])
    assert rt.call_llm(llm, [{"role": "user", "content": "hi"}]).content == "ok"
    assert rt.tracer.spans[-1].note == "fallback model" and rt.tracer.spans[0].ok is False
    with pytest.raises(RuntimeError):
        Runtime(llm_fault="down").call_llm(FakeLLM(["x"]), [])


def test_no_retries_means_one_attempt():
    rt = Runtime(faults={"get_weather": "flaky"})
    assert "error" in rt.call_tool(week4_tools.execute, new_world(), "get_weather", {"city": "Detroit"})


# ------------------------------------------------------------------ week 6
def test_golden_runner_reports_rates_and_flaky_cases():
    cases = week6_eval.load_cases(["weather"])
    from labs.week6_agent_eval import evals

    answers = iter([True, False, True, True])

    def runner(text):
        trace = evals.run_agent(text, "v1")
        if not next(answers):
            trace["answer"] = "no idea"
        return trace

    report = week6_eval.run_golden(runner, cases, repeats=2)
    assert len(report["runs"]) == 4
    statuses = {r["Case"]: r["Status"] for r in report["rows"]}
    assert statuses == {"wx-01": "FLAKY", "wx-02": "PASS"}
    assert report["flaky"] == ["wx-01"] and report["task_rate"] == 0.75


def test_golden_grade_counts_held_back_actions():
    case = next(c for c in week6_eval.load_cases() if c["id"] == "em-01")
    llm = FakeLLM([
        tools_reply(call("lookup_contact", name="maya")),
        tools_reply(call("send_email", to="maya@example.com", subject="Monday agenda", body="Hi")),
        "Draft to maya@example.com. Should I send it?",
    ])
    g = week6_eval.grade(case, week5_agent.run(llm, case["input"]))
    assert g["task"] and g["tools"] and g["held_for_approval"] == ["send_email"]


# ------------------------------------------------------------------ week 8
def test_assistant_uses_every_component_and_remembers():
    req = week1_understand.UnderstoodRequest(intent="notes", summary="Offsite budget", title=None, date=None,
                                       time=None, city=None, people=["Jordan"], missing_info=[])
    llm = FakeLLM(
        replies=[tools_reply(call("search_notes", query="offsite budget")), "Jordan capped it at $4,000.",
                 lambda messages: "You asked about the budget." if any(
                     "Jordan capped" in m.get("content", "") for m in messages) else "?"],
        parsed={"UnderstoodRequest": req, "LearnedFacts": week2_memory.LearnedFacts(new_facts=[])})
    muse = MiniMuse(llm)
    trace = muse.ask("What did Jordan say about the offsite budget?")
    assert trace["request"]["intent"] == "notes"
    assert "4,000" in json.dumps(trace["tool_calls"][0]["result"])
    assert any(s["Kind"] == "tool" for s in trace["spans"])
    assert "Parsed request" in llm.seen[0][0]["content"]
    assert muse.ask("What did I just ask?")["answer"] == "You asked about the budget."


def test_assistant_approval_is_recorded_in_memory():
    llm = FakeLLM([], parsed={"LearnedFacts": week2_memory.LearnedFacts(new_facts=[])})
    muse = MiniMuse(llm, use_understanding=False)
    muse.approve({"tool": "send_email", "args": {"to": "maya@example.com", "subject": "s", "body": "b"}})
    assert len(muse.world["emails_sent"]) == 1 and "approved" in muse.memory.history[-1]["content"]


# ------------------------------------------------------------------ the real SDK, with a fake HTTP server
def test_llm_wrapper_talks_to_the_real_openai_sdk():
    """Checks the request and response shapes against the actual openai package, offline."""
    import httpx
    from openai import OpenAI

    from labs.shared.settings import ModelSettings
    from mini_muse.llm import LLM

    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append((request.url.path, body))
        if request.url.path.endswith("/chat/completions"):
            message = ({"role": "assistant", "content": "Done."} if body["messages"][-1]["role"] == "tool" else
                       {"role": "assistant", "content": None, "tool_calls": [{"id": "c1", "type": "function",
                        "function": {"name": "get_weather", "arguments": "{\"city\": \"Detroit\"}"}}]})
            return httpx.Response(200, json={"id": "x", "object": "chat.completion", "created": 0, "model": body["model"],
                                             "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
                                             "usage": {"prompt_tokens": 20, "completion_tokens": 7, "total_tokens": 27}})
        if request.url.path.endswith("/embeddings"):
            return httpx.Response(200, json={"object": "list", "model": body["model"],
                                             "data": [{"object": "embedding", "index": i, "embedding": [0.1, 0.2]}
                                                      for i, _ in enumerate(body["input"])],
                                             "usage": {"prompt_tokens": 3, "total_tokens": 3}})
        raise AssertionError(request.url.path)

    client = OpenAI(api_key="test", http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    llm = LLM(ModelSettings(), client=client)
    trace = week5_agent.run(llm, "Weather in Detroit?")
    assert trace["tool_calls"][0]["result"]["temp_f"] == 48 and trace["answer"] == "Done."
    first = sent[0][1]
    assert first["tools"][0]["function"]["name"] == "get_weather" and first["max_completion_tokens"] == 1000
    assert sent[1][1]["messages"][-2]["tool_calls"][0]["id"] == "c1"
    assert llm.usage.calls == 2 and llm.usage.input_tokens == 40
    assert llm.embed(["a", "b"]) == [[0.1, 0.2], [0.1, 0.2]]


def test_parse_keeps_the_raw_model_output():
    from types import SimpleNamespace

    from labs.shared.settings import ModelSettings
    from mini_muse.llm import LLM

    raw = '{"new_facts": ["Prefers mornings"]}'
    response = SimpleNamespace(usage=SimpleNamespace(input_tokens=40, output_tokens=9), output_text=raw,
                               output_parsed=week2_memory.LearnedFacts(new_facts=["Prefers mornings"]))
    client = SimpleNamespace(responses=SimpleNamespace(parse=lambda **_: response))
    llm = LLM(ModelSettings(), client=client)
    assert llm.parse("x", "y", week2_memory.LearnedFacts).new_facts == ["Prefers mornings"]
    assert llm.last_output == raw and llm.usage.output_tokens == 9
