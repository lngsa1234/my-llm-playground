"""Offline tests for the Week 5 workflow agent, with a scripted fake model."""

from labs.week5_agent_workflow import workflow_agent as wf


class FakeModel:
    def __init__(self, drafts, reviews=None, triage=True, routes=None, must=("Mini Muse",), max_words=20):
        self.drafts, self.reviews, self.routes = list(drafts), list(reviews or []), list(routes or [])
        self.triage, self.must, self.max_words = triage, list(must), max_words
        self.calls = self.input_tokens = self.output_tokens = 0

    def _tick(self):
        self.calls += 1
        self.input_tokens += 10
        self.output_tokens += 5

    def parse(self, instructions, text, schema):
        self._tick()
        name = schema.__name__
        if name == "Triage":
            return schema(accepted=self.triage, reason="writing task" if self.triage else "not writing")
        if name == "Requirements":
            return schema(max_words=self.max_words, must_include=self.must, audience="members", tone="warm", other=[])
        if name == "Plan":
            return schema(sections=["hello", "details"])
        if name == "Review":
            return self.reviews.pop(0)
        if name == "RouteChoice":
            nxt, reason = self.routes.pop(0)
            return schema(next=nxt, reason=reason)
        raise AssertionError(name)

    def text(self, instructions, text):
        self._tick()
        self.last_prompt = text
        return self.drafts.pop(0)

    def cost(self):
        return 0.0


def stages(state):
    return [(r["stage"], r["next"]) for r in state.trace]


def test_happy_path_ends_complete_and_qa_uses_tool_then_llm():
    model = FakeModel(["Welcome to Mini Muse!"], [wf.Review(passed=True, feedback="good")])
    state = wf.run_agent(wf.AgentState("write a note"), model)
    assert state.status == "complete" and state.qa["checked_by"] == "llm"
    assert stages(state) == [("triage", "requirements"), ("requirements", "planning"), ("planning", "drafting"),
                             ("drafting", "qa"), ("qa", "complete")]


def test_tool_failure_skips_the_model_and_repairs_with_feedback():
    model = FakeModel(["No project name here.", "Now with Mini Muse."], [wf.Review(passed=True, feedback="ok")])
    state = wf.run_agent(wf.AgentState("write"), model)
    assert state.status == "complete" and state.repair_count == 1
    assert 'missing "Mini Muse"' in state.trace[4]["observed"] and state.trace[4]["next"] == "drafting"
    assert "Fix exactly this" in model.last_prompt
    assert model.calls == 6  # 3 parses + 2 drafts + 1 review; the failed QA cost nothing


def test_repair_budget_ends_in_failed_with_reason():
    model = FakeModel(["x"] * 5)
    state = wf.run_agent(wf.AgentState("write", max_repairs=2), model, options={"force_qa_fail": True})
    assert state.status == "failed" and state.repair_count == 2
    assert "repair budget is used up (2/2)" in state.failure_reason
    assert state.step_count == 9  # the lab's count: 3 setup + (draft, qa) × 3


def test_triage_rejection_and_max_steps():
    rejected = wf.run_agent(wf.AgentState("book a flight"), FakeModel([], triage=False))
    assert rejected.status == "failed" and "rejected" in rejected.failure_reason and rejected.step_count == 1
    capped = wf.run_agent(wf.AgentState("write", max_steps=3), FakeModel(["x"]))
    assert capped.status == "failed" and "Maximum steps exceeded (3)" in capped.failure_reason


def test_llm_router_illegal_jump_is_refused():
    model = FakeModel([], routes=[("complete", "looks done to me")])
    state = wf.run_agent(wf.AgentState("write"), model, router=wf.llm_route(model))
    assert state.status == "failed" and "Illegal transition proposed: triage → complete" in state.failure_reason


def test_action_error_ends_cleanly():
    model = FakeModel([])  # drafting will run out of scripted drafts
    state = wf.run_agent(wf.AgentState("write"), model)
    assert state.status == "failed" and "Action 'drafting' failed" in state.failure_reason


def test_rule_check_counts_words_and_phrases():
    req = {"max_words": 3, "must_include": ["Muse"]}
    assert wf.check_rules("Hello Mini Muse", req) == []
    assert len(wf.check_rules("one two three four", req)) == 2
