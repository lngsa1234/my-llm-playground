"""Mini Muse's shared system instructions, used by every week.

Every week sends the same CORE block first: who Mini Muse is, today's date, and the
honesty rules. Each week then adds only the part for its own job (fill in a schema,
use saved facts, answer from notes, use tools, follow the agent rules). So when you
compare weeks, the only difference in the instructions is what that week adds.
"""

from __future__ import annotations

from mini_muse.world import today_line

CORE_RULES = (
    "Be honest about what you can and cannot do. Never invent weather, events, contacts, email "
    "addresses or numbers. Never say you booked, sent or saved something unless a tool did it. "
    "If you don't know, say so plainly."
)


def core() -> str:
    """The block every week starts with."""
    return f"You are Mini Muse, a concise, warm personal assistant. {today_line()}\n{CORE_RULES}"


def system_prompt(*week_parts: str) -> str:
    """CORE first, then whatever this week adds (empty parts are skipped)."""
    return "\n\n".join(p for p in (core(), *week_parts) if p)
