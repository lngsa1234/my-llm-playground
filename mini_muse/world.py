"""The fake world Mini Muse acts on: a calendar, contacts, an outbox, weather and notes.

Every tool reads and writes this dictionary, never a real service, so nothing is
ever really booked or sent. A fresh copy is made for each conversation or test.

The calendar, contacts and weather match the Week 6 golden dataset exactly, so the
same test cases grade both the simulated Muse (v1, v2) and Mini Muse.
"""

from __future__ import annotations

import copy
from datetime import date
from pathlib import Path

# The world's "today". Fixed, so relative dates ("tomorrow", "Wednesday") resolve the
# same way for everyone and the golden dataset's dates stay in the future.
TODAY = date(2026, 10, 26)  # a Monday

NOTES_DIR = Path(__file__).resolve().parent / "data" / "notes"

WORLD_TEMPLATE = {
    "weather": {
        "Detroit": {"temp_f": 48, "conditions": "light rain"},
        "Chicago": {"temp_f": 52, "conditions": "cloudy"},
        "Beijing": {"temp_f": 61, "conditions": "sunny"},
    },
    "calendar": {
        "2026-10-26": [{"title": "Weekly planning", "time": "10:00"}],
        "2026-10-27": [{"title": "Dentist", "time": "14:00"}],
        "2026-10-28": [],
        "2026-10-29": [{"title": "Team sync", "time": "09:00"},
                       {"title": "Coffee chat", "time": "15:30"}],
        "2026-10-30": [{"title": "Book club", "time": "18:30"}],
    },
    "contacts": {
        "maya": "maya@example.com",
        "jordan": "jordan@example.com",
    },
    "events_created": [],
    "emails_sent": [],
}


def new_world() -> dict:
    """A fresh, independent copy of the world."""
    return copy.deepcopy(WORLD_TEMPLATE)


def side_effects(world: dict) -> dict:
    """What the agent changed: the part of the world a Week 6 task-success check reads."""
    return {"events_created": list(world["events_created"]), "emails_sent": list(world["emails_sent"])}


def today_line() -> str:
    return f"Today is {TODAY.strftime('%A')}, {TODAY.isoformat()}."
