"""Week 1 · Understanding: turn a free-text request into structured fields.

    "Book lunch with Maya on Tuesday at noon"
        ↓  one API call with structured output
    {"intent": "schedule", "title": "Lunch", "date": "2026-10-27", "time": "12:00",
     "people": ["Maya"], ...}

This is the first thing Mini Muse needs: before it can do anything, it has to know
what is being asked, with the details in a shape code can rely on. Later weeks use
this as the router and as a hint to the agent.

Try it:  python -m mini_muse.week1_understand "Book lunch with Maya Tuesday at noon"
"""

from __future__ import annotations

import sys
from typing import Literal, Optional

from pydantic import BaseModel, Field

from mini_muse.world import today_line

Intent = Literal["weather", "calendar", "schedule", "email", "notes", "math", "other"]

INTENTS = {
    "weather": "current weather in a city",
    "calendar": "what is on the calendar on a day",
    "schedule": "create a calendar event",
    "email": "write or send an email to a contact",
    "notes": "a question about the user's own notes, meetings or plans",
    "math": "arithmetic, such as a tip or a split bill",
    "other": "anything else, including requests Mini Muse cannot do",
}


class MuseRequest(BaseModel):
    """What the user wants, in fields. Every field is present; unknown values are null."""

    intent: Intent = Field(description="The kind of request.")
    summary: str = Field(description="The request restated in under 12 words.")
    title: Optional[str] = Field(description="Event title or email subject, if any.")
    date: Optional[str] = Field(description="Date as YYYY-MM-DD, resolved from relative words like 'Tuesday'.")
    time: Optional[str] = Field(description="Time as 24-hour HH:MM.")
    city: Optional[str] = Field(description="City for a weather request.")
    people: list[str] = Field(description="Names of people mentioned.")
    missing_info: list[str] = Field(description="Details still needed before acting, e.g. 'time'. Empty if none.")


def instructions() -> str:
    intents = "\n".join(f"- {name}: {meaning}" for name, meaning in INTENTS.items())
    return (
        "You read requests sent to Mini Muse, a personal assistant, and fill in the fields of "
        f"the response schema. {today_line()} Resolve relative dates against today: a weekday "
        "name means its next occurrence after today. Use null for anything not stated; never "
        "guess a time or a date. List what is missing before the request can be carried out.\n\n"
        f"Intents:\n{intents}"
    )


def understand(llm, text: str) -> MuseRequest:
    """One structured-output call. `llm` is a mini_muse.llm.LLM (or a test fake)."""
    return llm.parse(instructions(), text, MuseRequest)


if __name__ == "__main__":
    from mini_muse.llm import cli_llm

    model = cli_llm()
    request = understand(model, " ".join(sys.argv[1:]) or "Book lunch with Maya on Tuesday at noon")
    print(request.model_dump_json(indent=2))
    print(f"\n{model.usage.calls} call · {model.usage.input_tokens} in / {model.usage.output_tokens} out tokens "
          f"· ${model.cost():.5f}")
