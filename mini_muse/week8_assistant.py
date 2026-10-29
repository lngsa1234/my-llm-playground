"""Week 8 · Assembly: every component wired into one assistant.

    User message
        ↓
    Week 1  understand()        structured fields: intent, date, time, people…  (a hint for the agent)
    Week 2  memory              saved facts + summary + recent turns go into the context;
                                new facts are learned from the message
        ↓
    Week 5  agent loop          decide → act → observe → … → answer, max_steps cap,
                                send_email held for approval
    Week 4    tools             calendar, contacts, email, weather, calculator
    Week 3    search_notes      RAG over your notes, as one more tool
    Week 7  runtime             every call traced, retried, timed out, with fallbacks
        ↓
    Answer (+ actions waiting for approval) → saved to memory
    Week 6  golden dataset      proves the whole thing still works after each change

Try it:  python -m mini_muse   (a chat loop with every component)
"""

from __future__ import annotations

from mini_muse import week1_understand, week2_memory, week5_agent
from mini_muse.week2_memory import Memory
from mini_muse.week4_tools import ALL_TOOLS
from mini_muse.week7_reliability import Runtime
from mini_muse.world import new_world


class MiniMuse:
    def __init__(self, llm, *, memory: Memory | None = None, world: dict | None = None, notes_index=None,
                 runtime: Runtime | None = None, use_understanding: bool = True, learn_facts: bool = True,
                 max_turns: int = 6, max_steps: int = week5_agent.DEFAULT_MAX_STEPS, search_mode: str = "keyword",
                 registry=None, tools=None):
        from mini_muse import week3_knowledge

        self.llm = llm
        self.memory = memory or Memory()
        self.world = world if world is not None else new_world()
        self.notes_index = notes_index or week3_knowledge.build_index()
        self.runtime = runtime or Runtime(max_retries=2)
        self.use_understanding, self.learn_facts = use_understanding, learn_facts
        self.max_turns, self.max_steps, self.search_mode = max_turns, max_steps, search_mode
        self.registry, self.tools = registry, tools

    def ask(self, text: str) -> dict:
        first_span = len(self.runtime.tracer.spans)
        request = week1_understand.understand(self.llm, text) if self.use_understanding else None
        new_facts = week2_memory.learn_facts(self.llm, self.memory, text) if self.learn_facts else []

        extra = [week2_memory.memory_text(self.memory)]
        if request is not None:
            extra.append(f"Parsed request (from structured output; may be imperfect): {request.model_dump_json()}")
        context = self.memory.history[-self.max_turns * 2:] if self.max_turns > 0 else []

        trace = week5_agent.run(
            self.llm, text, world=self.world, tools=self.tools or ALL_TOOLS, max_steps=self.max_steps,
            runtime=self.runtime, context=context, system_extra="\n\n".join(e for e in extra if e),
            version="mini-muse", registry=self.registry,
            tool_options={"notes_index": self.notes_index, "mode": self.search_mode,
                          "llm": self.llm if self.notes_index.semantic else None})

        self.memory.history += [{"role": "user", "content": text}, {"role": "assistant", "content": trace["answer"]}]
        trace.update(request=request.model_dump() if request is not None else None, new_facts=new_facts,
                     spans=[s.row() for s in self.runtime.tracer.spans[first_span:]])
        return trace

    def approve(self, action: dict) -> dict:
        result = week5_agent.approve(self.world, action, self.runtime, registry=self.registry)
        target = action["args"].get("to") or action["args"].get("title") or ""
        note = (f"(The user approved: {action['tool']} {target} — "
                f"{'done' if 'error' not in result else 'failed: ' + result['error']}.)")
        self.memory.history.append({"role": "assistant", "content": note})
        return result


def main() -> None:
    from mini_muse.llm import cli_llm

    llm = cli_llm()
    muse = MiniMuse(llm, memory=Memory.load())
    print("Mini Muse. Ask about your calendar, weather, notes, emails or tips. 'quit' to stop.")
    while (line := input("\nyou> ").strip()) not in {"quit", "exit"}:
        if not line:
            continue
        trace = muse.ask(line)
        for fact in trace["new_facts"]:
            print(f"  [remembered: {fact}]")
        for call in trace["tool_calls"]:
            print(f"  → {call['tool']}({call['args']})")
        print(f"muse> {trace['answer']}")
        for action in trace["pending_actions"]:
            if input(f"  Approve {action['tool']} to {action['args'].get('to')}? [y/N] ").lower() == "y":
                print(f"  {muse.approve(action)}")
        muse.memory.save()
    print(f"\n{llm.usage.calls} calls · ${llm.cost():.4f} · side effects: "
          f"{len(muse.world['events_created'])} events, {len(muse.world['emails_sent'])} emails (all fake)")


if __name__ == "__main__":
    main()
