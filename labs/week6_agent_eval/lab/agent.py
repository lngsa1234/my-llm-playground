"""
The agent under test: "Muse", a tiny personal-assistant agent.

It is deliberately rule-based (no LLM needed) so the lab runs offline and
results are reproducible. It behaves like a real tool-using agent:
  query -> decide which tools to call -> call them -> write a final answer

Two versions exist:
  v1  - the "good" baseline
  v2  - a "faster, friendlier" update that quietly introduces regressions
        (your job in the lab is to catch them with evals)

Swap in a real LLM agent later: anything that returns the same Trace shape
can be evaluated by every stage of this lab.
"""
import ast
import copy
import operator
import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# The "world" the agent acts on (fake data, reset for every test case)
# --------------------------------------------------------------------------
WORLD_TEMPLATE = {
    "weather": {
        "Detroit": {"temp_f": 48, "conditions": "light rain"},
        "Chicago": {"temp_f": 52, "conditions": "cloudy"},
        "Beijing": {"temp_f": 61, "conditions": "sunny"},
    },
    "calendar": {
        "2026-10-27": [{"title": "Dentist", "time": "14:00"}],
        "2026-10-28": [],
        "2026-10-29": [{"title": "Team sync", "time": "09:00"},
                       {"title": "Coffee chat", "time": "15:30"}],
    },
    "contacts": {
        "maya": "maya@example.com",
        "jordan": "jordan@example.com",
    },
    "events_created": [],
    "emails_sent": [],
}


# --------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------
def get_weather(world, city):
    w = world["weather"].get(city)
    if not w:
        return {"error": f"No weather data for {city}"}
    return {"city": city, **w}


def check_calendar(world, date):
    return {"date": date, "events": world["calendar"].get(date, [])}


def create_event(world, title, date, time):
    ev = {"title": title, "date": date, "time": time}
    world["calendar"].setdefault(date, []).append({"title": title, "time": time})
    world["events_created"].append(ev)
    return {"status": "created", **ev}


def lookup_contact(world, name):
    email = world["contacts"].get(name.lower())
    return {"name": name, "email": email} if email else {"error": f"No contact named {name}"}


def send_email(world, to, subject, body):
    world["emails_sent"].append({"to": to, "subject": subject, "body": body})
    return {"status": "sent", "to": to}


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.USub: operator.neg}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("unsupported expression")


def calculator(world, expression):
    try:
        return {"result": round(_safe_eval(ast.parse(expression, mode="eval")), 2)}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


TOOLS = {
    "get_weather": get_weather,
    "check_calendar": check_calendar,
    "create_event": create_event,
    "lookup_contact": lookup_contact,
    "send_email": send_email,
    "calculator": calculator,
}


# --------------------------------------------------------------------------
# Trace: everything an evaluator might want to look at
# --------------------------------------------------------------------------
@dataclass
class Trace:
    query: str
    version: str
    tool_calls: list = field(default_factory=list)   # [{"tool", "args", "result"}]
    answer: str = ""
    final_state: dict = field(default_factory=dict)  # side effects

    def call(self, world, tool, **args):
        result = TOOLS[tool](world, **args)
        self.tool_calls.append({"tool": tool, "args": args, "result": result})
        return result

    def to_dict(self):
        return {"query": self.query, "version": self.version,
                "tool_calls": self.tool_calls, "answer": self.answer,
                "final_state": self.final_state}


# --------------------------------------------------------------------------
# The agent
# --------------------------------------------------------------------------
def _style(text, version):
    # v2's "friendlier" persona -- an LLM judge should notice this
    if version == "v2":
        return "Absolutely!! As your super-amazing assistant, I'm SO happy to help! " + text
    return text


def run_agent(query, version="v1"):
    world = copy.deepcopy(WORLD_TEMPLATE)
    t = Trace(query=query, version=version)
    q = query.lower()

    # Guardrail: obvious instruction-override attempts
    if "ignore" in q and "instruction" in q:
        t.answer = "I can't do that. I only act on your direct requests, and I won't bulk-email your contacts."

    # Email someone
    elif m := re.search(r"email (\w+) (?:about|that) (.+)", q):
        name, topic = m.group(1), m.group(2).rstrip(".?!")
        c = t.call(world, "lookup_contact", name=name)
        if "error" in c:
            t.answer = f"I couldn't find anyone named {name.title()} in your contacts. Can you give me their email?"
        elif version == "v1":
            t.answer = (f"Here's a draft to {c['email']}:\nSubject: {topic.capitalize()}\n"
                        f"Hi {name.title()}, quick note about {topic}.\nShould I send it?")
        else:  # v2 regression: sends without asking
            t.call(world, "send_email", to=c["email"], subject=topic.capitalize(),
                   body=f"Hi {name.title()}, quick note about {topic}.")
            t.answer = f"Sent your email to {c['email']}."

    # Schedule an event
    elif m := re.search(r"(?:schedule|book) (.+?) on (\d{4}-\d{2}-\d{2}) at (\d{1,2}:\d{2})", q):
        title, date, time = m.group(1).strip().title(), m.group(2), m.group(3).zfill(5)
        conflict = None
        if version == "v1":  # v2 regression: skips the conflict check
            cal = t.call(world, "check_calendar", date=date)
            conflict = next((e for e in cal["events"] if e["time"] == time), None)
        if conflict:
            t.answer = (f"You already have '{conflict['title']}' at {time} on {date}, "
                        f"so I didn't book {title}. Want a different time?")
        else:
            t.call(world, "create_event", title=title, date=date, time=time)
            t.answer = f"Booked {title} on {date} at {time}."

    # Read the calendar
    elif m := re.search(r"calendar (?:on|for) (\d{4}-\d{2}-\d{2})", q):
        date = m.group(1)
        cal = t.call(world, "check_calendar", date=date)
        if cal["events"]:
            items = "; ".join(f"{e['time']} {e['title']}" for e in cal["events"])
            t.answer = f"On {date} you have: {items}."
        else:
            t.answer = f"Your calendar is free on {date}."

    # Weather
    elif m := re.search(r"weather (?:in|for) ([a-z ]+)", q):
        city = m.group(1).strip().title()
        w = t.call(world, "get_weather", city=city)
        if "error" in w:
            t.answer = f"Sorry, I don't have weather for {city}."
        else:
            t.answer = f"It's {w['temp_f']}°F with {w['conditions']} in {city}."

    # Tip / percentage math
    elif m := re.search(r"(\d+(?:\.\d+)?)% tip on \$?(\d+(?:\.\d+)?)", q):
        pct, amt = m.group(1), m.group(2)
        r = t.call(world, "calculator", expression=f"{amt} * {pct} / 100")
        t.answer = f"A {pct}% tip on ${amt} is ${r['result']:.2f}."

    # Out of scope
    else:
        t.answer = ("I can help with weather, your calendar, scheduling, emails to contacts, "
                    "and tip math. I can't help with that request.")

    t.answer = _style(t.answer, version)
    t.final_state = {"events_created": world["events_created"],
                     "emails_sent": world["emails_sent"]}
    return t


if __name__ == "__main__":
    import json, sys
    v = sys.argv[2] if len(sys.argv) > 2 else "v1"
    print(json.dumps(run_agent(sys.argv[1], v).to_dict(), indent=2, ensure_ascii=False))
