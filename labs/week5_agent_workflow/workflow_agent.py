"""Week 5 core logic: a stateful workflow agent with a bounded control loop.

A Python version of the Week 5 lab's architecture, applied to a writing task so it
is safe to run anywhere (no generated code is executed):

    request → TRIAGE → REQUIREMENTS → PLANNING → DRAFTING → QA → COMPLETE
                 │                                   ▲        │
                 └──────────► FAILED ◄── budget used ┴─ fail ─┘  (repair: back to DRAFTING)

Five concepts, each a small piece of this file:

    State         AgentState: everything the agent knows, explicit and inspectable
    Workflow      TRANSITIONS: which stage may follow which
    Actions       one function per stage; they do work and report what they observed,
                  and never change the stage themselves
    Router        decides the next stage from the updated state, with a reason
                  ("code" router by default; an "llm" router for the experiment)
    Control loop  run → observe → update → route → validate → advance, until a terminal
                  stage or a boundary (max steps, repair budget, action error, illegal move)

Principle: use code for decisions that can be code (word count, required phrases,
the routing rules); use the model only where judgment is needed (is the draft right?).

Try it:  python labs/week5_agent_workflow/workflow_agent.py "Write a 100-word welcome note …"
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Optional

from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # so the command-line run finds labs.shared

from labs.shared.settings import ModelSettings

STAGES = ["triage", "requirements", "planning", "drafting", "qa", "complete", "failed"]
TERMINAL = {"complete", "failed"}
TRANSITIONS = {
    "triage": {"requirements", "failed"},
    "requirements": {"planning", "failed"},
    "planning": {"drafting", "failed"},
    "drafting": {"qa", "failed"},
    "qa": {"complete", "drafting", "failed"},
}

EXAMPLES = [
    "Write a welcome note of at most 120 words for new members of the Agent Engineering Peer Learning Circle. "
    "Mention the 8-week plan, Mini Muse and the Monday sessions.",
    "Write a 3-sentence product update announcing that our app now supports dark mode. Mention 'Settings' and 'beta'.",
    "Write a polite reminder email, under 80 words, asking the team to submit their architecture diagrams by Friday.",
    "Book me a flight to Chicago next Tuesday.",
]


# ------------------------------------------------------------------ state
@dataclass
class AgentState:
    request: str
    stage: str = "triage"
    status: str = "running"            # running | complete | failed
    step_count: int = 0
    max_steps: int = 12
    repair_count: int = 0
    max_repairs: int = 2
    triage: Optional[dict] = None       # {"accepted", "reason"}
    requirements: Optional[dict] = None  # {"max_words", "must_include", "audience", "tone", "other"}
    plan: list = field(default_factory=list)
    draft: str = ""
    qa: Optional[dict] = None           # {"passed", "feedback", "checked_by"}
    failure_reason: str = ""
    trace: list = field(default_factory=list)

    def snapshot(self) -> dict:
        data = asdict(self)
        data.pop("trace")
        return data


# ------------------------------------------------------------------ model
class Model:
    """Two kinds of call: structured output (parse) and plain text. Counts tokens and cost."""

    def __init__(self, settings: ModelSettings, client=None):
        if client is None:
            from openai import OpenAI

            client = OpenAI()
        self.client, self.settings = client, settings
        self.calls = self.input_tokens = self.output_tokens = 0

    def _count(self, usage) -> int:
        self.calls += 1
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        return usage.input_tokens + usage.output_tokens

    def parse(self, instructions: str, text: str, schema):
        r = self.client.responses.parse(model=self.settings.model, instructions=instructions, input=text,
                                        text_format=schema, max_output_tokens=self.settings.max_output_tokens)
        self._count(r.usage)
        if r.output_parsed is None:
            raise ValueError("The model did not return the requested structure.")
        return r.output_parsed

    def text(self, instructions: str, text: str) -> str:
        r = self.client.responses.create(model=self.settings.model, instructions=instructions, input=text,
                                         max_output_tokens=self.settings.max_output_tokens)
        self._count(r.usage)
        return r.output_text or ""

    def cost(self) -> float:
        return self.settings.cost(self.input_tokens, self.output_tokens)


# ------------------------------------------------------------------ structured outputs
class Triage(BaseModel):
    accepted: bool = Field(description="True only for a request to write a short piece of text.")
    reason: str = Field(description="One sentence explaining the decision.")


class Requirements(BaseModel):
    max_words: int = Field(description="Word limit stated or implied; 150 if none is stated.")
    must_include: list[str] = Field(description="Exact words or short phrases the text must contain.")
    audience: str
    tone: str
    other: list[str] = Field(description="Other checkable requirements, one short line each.")


class Plan(BaseModel):
    sections: list[str] = Field(description="2-4 short outline points, in order.")


class Review(BaseModel):
    passed: bool
    feedback: str = Field(description="If failed: what to change, specifically. If passed: one line why.")


class RouteChoice(BaseModel):
    next: str = Field(description="The next stage name.")
    reason: str


# ------------------------------------------------------------------ actions
# Each action reads the state and returns (patch, summary). It never sets the stage.
def act_triage(state: AgentState, model: Model, options: dict):
    t = model.parse("You triage requests for a writing agent. Accept only requests to write a short text "
                    "(note, email, announcement, post, poem). Reject anything else.", state.request, Triage)
    return {"triage": t.model_dump()}, f"{'Accepted' if t.accepted else 'Rejected'}: {t.reason}"


def act_requirements(state: AgentState, model: Model, options: dict):
    r = model.parse("Turn the writing request into checkable requirements. Put names, products and required "
                    "terms in must_include, word for word as the request gives them.", state.request, Requirements)
    return {"requirements": r.model_dump()}, (f"≤ {r.max_words} words; must include "
                                              f"{', '.join(r.must_include) or 'nothing specific'}")


def act_planning(state: AgentState, model: Model, options: dict):
    p = model.parse("Outline the text in 2-4 short points.",
                    f"Request: {state.request}\nRequirements: {json.dumps(state.requirements)}", Plan)
    return {"plan": p.sections}, f"{len(p.sections)}-point outline"


def act_drafting(state: AgentState, model: Model, options: dict):
    prompt = (f"Request: {state.request}\nRequirements: {json.dumps(state.requirements)}\n"
              f"Outline: {json.dumps(state.plan)}")
    if state.qa and not state.qa["passed"]:
        prompt += f"\n\nYour previous draft failed review. Fix exactly this: {state.qa['feedback']}\n\nPrevious draft:\n{state.draft}"
    draft = model.text("Write the text. Return only the text itself, no title or commentary.", prompt).strip()
    label = f"repair {state.repair_count} draft" if state.repair_count else "first draft"
    return {"draft": draft}, f"{label}: {word_count(draft)} words"


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'’-]+\b", text))


def check_rules(draft: str, requirements: dict) -> list[str]:
    """The deterministic QA tool: things code can check exactly, for free."""
    problems = []
    words = word_count(draft)
    if words > requirements["max_words"]:
        problems.append(f"{words} words, over the {requirements['max_words']}-word limit")
    for phrase in requirements["must_include"]:
        if phrase.lower() not in draft.lower():
            problems.append(f"missing \"{phrase}\"")
    return problems


def act_qa(state: AgentState, model: Model, options: dict):
    if options.get("force_qa_fail"):
        return ({"qa": {"passed": False, "feedback": "Injected failure (fault injection is on).", "checked_by": "injected"}},
                "FAIL (injected)")
    problems = check_rules(state.draft, state.requirements)
    if problems:  # no need to pay for a model when code already found the problem
        return {"qa": {"passed": False, "feedback": "; ".join(problems), "checked_by": "tool"}}, "FAIL (tool): " + "; ".join(problems)
    review = model.parse("Review the draft against the request and requirements. Pass it only if it meets the "
                         "audience, tone and every other requirement.",
                         f"Request: {state.request}\nRequirements: {json.dumps(state.requirements)}\nDraft:\n{state.draft}",
                         Review)
    qa = {**review.model_dump(), "checked_by": "llm"}
    return {"qa": qa}, f"{'PASS' if review.passed else 'FAIL'} (tool ✓, then llm): {review.feedback}"


ACTIONS: dict[str, Callable] = {"triage": act_triage, "requirements": act_requirements, "planning": act_planning,
                                "drafting": act_drafting, "qa": act_qa}


# ------------------------------------------------------------------ routers
def route(state: AgentState) -> tuple[str, str]:
    """The code router: every workflow decision is a rule, with a reason."""
    if state.stage == "triage":
        accepted = state.triage and state.triage["accepted"]
        return ("requirements", "Request accepted") if accepted else ("failed", f"Triage rejected it: {state.triage['reason']}")
    if state.stage == "requirements":
        return ("planning", "Requirements ready") if state.requirements else ("failed", "No requirements")
    if state.stage == "planning":
        return ("drafting", f"{len(state.plan)} outline points") if state.plan else ("failed", "No plan")
    if state.stage == "drafting":
        return ("qa", "Draft ready for review") if state.draft else ("failed", "Empty draft")
    if state.stage == "qa":
        if state.qa["passed"]:
            return "complete", "QA passed"
        if state.repair_count >= state.max_repairs:
            return "failed", f"QA failed and the repair budget is used up ({state.repair_count}/{state.max_repairs}): {state.qa['feedback']}"
        return "drafting", f"QA failed ({state.qa['checked_by']}); repair {state.repair_count + 1} of {state.max_repairs}"
    return "failed", f"No route from {state.stage}"


def llm_route(model: Model) -> Callable[[AgentState], tuple[str, str]]:
    """Experiment: let the model pick the next stage. The workflow still checks it is legal."""
    def router(state: AgentState) -> tuple[str, str]:
        choice = model.parse(
            f"You route a writing agent. Stages: {', '.join(STAGES)}. Pick the next stage after "
            f"'{state.stage}' given the state. Repairs used: {state.repair_count} of {state.max_repairs}.",
            json.dumps(state.snapshot()), RouteChoice)
        return choice.next.strip().lower(), f"(llm) {choice.reason}"
    return router


# ------------------------------------------------------------------ control loop
def can_transition(src: str, dst: str) -> bool:
    return dst in TRANSITIONS.get(src, set())


def _finish(state: AgentState, stage: str, reason: str) -> None:
    state.stage, state.status = stage, ("complete" if stage == "complete" else "failed")
    if stage == "failed":
        state.failure_reason = reason


def run_agent(state: AgentState, model: Model, router: Callable | None = None, options: dict | None = None,
              on_step: Callable[[dict], None] | None = None) -> AgentState:
    router, options = router or route, options or {}
    while state.status == "running":
        if state.step_count >= state.max_steps:  # boundary 1: never loop forever
            _finish(state, "failed", f"Maximum steps exceeded ({state.max_steps})")
            _trace(state, on_step, state.stage, "Stopped by the step limit", None, "failed", state.failure_reason, 0, 0)
            break
        stage = state.stage
        state.step_count += 1
        started, tokens_before = time.perf_counter(), model.input_tokens + model.output_tokens
        try:  # execute + observe; boundary 2: an action error ends cleanly, with a reason
            patch, summary = ACTIONS[stage](state, model, options)
        except Exception as exc:  # noqa: BLE001
            _finish(state, "failed", f"Action '{stage}' failed: {type(exc).__name__}: {exc}")
            _trace(state, on_step, stage, f"ERROR: {exc}", stage, "failed", state.failure_reason,
                   time.perf_counter() - started, 0)
            break
        for key, value in patch.items():  # update state with what the action observed
            setattr(state, key, value)
        nxt, reason = router(state)  # decide
        tokens = model.input_tokens + model.output_tokens - tokens_before
        if not can_transition(stage, nxt):  # boundary 3: the workflow validates every decision
            _finish(state, "failed", f"Illegal transition proposed: {stage} → {nxt}")
            _trace(state, on_step, stage, summary, stage, nxt, state.failure_reason, time.perf_counter() - started, tokens)
            break
        if stage == "qa" and nxt == "drafting":
            state.repair_count += 1
        if nxt in TERMINAL:
            _finish(state, nxt, reason)
        else:
            state.stage = nxt
        _trace(state, on_step, stage, summary, stage, nxt, reason, time.perf_counter() - started, tokens)
    return state


def _trace(state, on_step, stage, summary, src, dst, reason, seconds, tokens) -> None:
    row = {"step": state.step_count, "stage": stage, "observed": summary, "next": dst or "",
           "reason": reason, "seconds": round(seconds, 2), "tokens": tokens}
    state.trace.append(row)
    if on_step:
        on_step(row)


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set. Copy .env.example to .env and add your key.")
    model = Model(ModelSettings())
    final = run_agent(AgentState(" ".join(sys.argv[1:]) or EXAMPLES[0]), model,
                      on_step=lambda r: print(f"[{r['step']}] {r['stage']:>12} → {r['next']:<12} {r['observed']}  ({r['reason']})"))
    print(f"\n{final.status.upper()}{': ' + final.failure_reason if final.failure_reason else ''}\n\n{final.draft}")
    print(f"\n{model.calls} model calls · ${model.cost():.4f}")
