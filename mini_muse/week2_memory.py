"""Week 2 · Memory: what Mini Muse carries from one message to the next.

The model remembers nothing between API calls. Everything it "knows" about the
conversation is rebuilt and sent again on every call. Mini Muse keeps three kinds
of memory and decides what goes into each call's context:

    facts     durable preferences learned from the user ("prefers morning meetings")
    history   the recent turns, word for word (so "make it 1pm instead" makes sense)
    summary   older turns, compacted into a few sentences once history grows too long

    context = system prompt + today's date + facts + summary + last N turns + new message

Try it:  python3 -m mini_muse.week2_memory   (a chat loop; memory is saved between runs)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field

from mini_muse.persona import system_prompt

STATE_FILE = Path(__file__).resolve().parent / "state" / "memory.json"

# What Week 2 adds to the shared instructions in mini_muse/persona.py.
PERSONA = ("Use what you know about the user when it is relevant, and say so briefly when you rely "
           "on a saved preference.")


@dataclass
class Memory:
    facts: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)  # {"role": "user" | "assistant", "content": str}
    summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "Memory":
        data = data or {}
        return cls(facts=list(data.get("facts", [])), history=list(data.get("history", [])),
                   summary=data.get("summary", ""))

    def save(self, path: Path = STATE_FILE) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path = STATE_FILE) -> "Memory":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8"))) if path.exists() else cls()


def memory_text(memory: Memory) -> str:
    """Saved facts and the conversation summary, as text for a system prompt."""
    parts = []
    if memory.facts:
        parts.append("What you know about the user:\n" + "\n".join(f"- {f}" for f in memory.facts))
    if memory.summary:
        parts.append(f"Summary of the earlier conversation: {memory.summary}")
    return "\n\n".join(parts)


def system_message(memory: Memory, persona: str = PERSONA) -> dict:
    return {"role": "system", "content": system_prompt(persona, memory_text(memory))}


def build_context(memory: Memory, text: str, max_turns: int = 6, persona: str = PERSONA) -> list[dict]:
    """The exact messages sent to the model. One turn = one user message + one reply."""
    recent = memory.history[-max_turns * 2:] if max_turns > 0 else []
    return [system_message(memory, persona), *recent, {"role": "user", "content": text}]


class LearnedFacts(BaseModel):
    new_facts: list[str] = Field(description="Durable preferences or facts about the user, one short sentence each.")


def learn_facts(llm, memory: Memory, text: str) -> list[str]:
    """Ask the model whether the message states something worth keeping; add only new facts."""
    known = "\n".join(f"- {f}" for f in memory.facts) or "(none)"
    found = llm.parse(
        "Extract durable facts or preferences the user states about themselves in this message, "
        "such as working hours, meeting preferences, dietary needs or people they work with. "
        "Ignore one-off requests and anything already known. Return an empty list if none.\n\n"
        f"Already known:\n{known}",
        text, LearnedFacts)
    new = [f.strip() for f in found.new_facts if f.strip() and f.strip() not in memory.facts]
    memory.facts.extend(new)
    return new


class Summary(BaseModel):
    summary: str = Field(description="A few sentences keeping names, dates, decisions and open questions.")


def compact(llm, memory: Memory, keep_turns: int) -> bool:
    """Fold turns older than the last `keep_turns` into the running summary."""
    cut = len(memory.history) - keep_turns * 2
    if cut <= 0:
        return False
    old, memory.history = memory.history[:cut], memory.history[cut:]
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in old)
    if memory.summary:
        transcript = f"Earlier summary: {memory.summary}\n\n{transcript}"
    memory.summary = llm.parse("Summarize this conversation for the assistant's future reference.",
                               transcript, Summary).summary
    return True


def chat(llm, memory: Memory, text: str, max_turns: int = 6, learn: bool = True, compact_after: int | None = None) -> dict:
    """One turn of a memory-aware chat (no tools yet: those arrive in Week 4)."""
    new_facts = learn_facts(llm, memory, text) if learn else []
    context = build_context(memory, text, max_turns)
    answer = llm.chat(context).content
    memory.history += [{"role": "user", "content": text}, {"role": "assistant", "content": answer}]
    compacted = compact(llm, memory, max_turns) if compact_after and len(memory.history) > compact_after * 2 else False
    return {"answer": answer, "new_facts": new_facts, "context": context, "compacted": compacted}


if __name__ == "__main__":
    from mini_muse.llm import cli_llm

    model, memory = cli_llm(), Memory.load()
    print(f"Mini Muse (memory). {len(memory.facts)} saved facts. Type 'facts', 'reset' or 'quit'.")
    while (line := input("\nyou> ").strip()) not in {"quit", "exit"}:
        if line == "facts":
            print("\n".join(memory.facts) or "(no facts yet)")
        elif line == "reset":
            memory = Memory()
        elif line:
            result = chat(model, memory, line, compact_after=10)
            for fact in result["new_facts"]:
                print(f"  [remembered: {fact}]")
            print(f"muse> {result['answer']}")
        memory.save()
