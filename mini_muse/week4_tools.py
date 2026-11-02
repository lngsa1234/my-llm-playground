"""Week 4 · Hands: the tools Mini Muse can use, and one round of tool calling.

A tool is two things:
  a schema      name + description + JSON parameters, sent to the model so it knows the tool exists
  a function    ordinary Python that the *app* runs when the model asks for it

The model never runs anything itself. It replies "call check_calendar with
{date: 2026-10-27}"; the app runs the function and sends the result back.

This week's `answer_with_tools` does exactly one round:
    model picks tools → app runs them → model writes the answer
Try "Book a haircut on 2026-10-27 at 14:00": the model has to check the calendar
*before* deciding whether to book, which one round can't do well. It also sends
emails without asking. Both problems are what Week 5's agent loop fixes.

Tool names and arguments match the Week 6 golden dataset, so Week 6 can grade Mini Muse.

Try it:  python3 -m mini_muse.week4_tools "What's the weather in Detroit?"
"""

from __future__ import annotations

import ast
import json
import operator
import sys

from mini_muse.llm import parse_arguments
from mini_muse.world import new_world, side_effects
from mini_muse import persona


def _schema(name: str, description: str, /, **params: str) -> dict:
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object",
                       "properties": {p: {"type": "string", "description": d} for p, d in params.items()},
                       "required": list(params), "additionalProperties": False}}}


SCHEMAS = {
    "get_weather": _schema("get_weather", "Current weather for a city.", city="City name, e.g. Detroit."),
    "check_calendar": _schema("check_calendar", "List the user's events on a date.", date="Date as YYYY-MM-DD."),
    "create_event": _schema("create_event", "Add an event to the user's calendar. Check the calendar first.",
                            title="Short event title.", date="Date as YYYY-MM-DD.", time="Start time as 24-hour HH:MM."),
    "lookup_contact": _schema("lookup_contact", "Find a contact's email address by first name.", name="First name."),
    "send_email": _schema("send_email", "Send an email. Only after the user has approved the draft.",
                          to="Email address.", subject="Subject line.", body="Email body."),
    "calculator": _schema("calculator", "Evaluate arithmetic, e.g. '85 * 20 / 100'.", expression="Arithmetic expression."),
    "search_notes": _schema("search_notes", "Search the user's personal notes (meetings, plans, trips, recipes).",
                            query="What to look for."),
}
CORE_TOOLS = ["get_weather", "check_calendar", "create_event", "lookup_contact", "send_email", "calculator"]
ALL_TOOLS = CORE_TOOLS + ["search_notes"]


# ------------------------------------------------------------------ tool functions
def get_weather(world, city):
    found = world["weather"].get(city.strip().title())
    return {"city": city, **found} if found else {"error": f"No weather data for {city}"}


def check_calendar(world, date):
    return {"date": date, "events": world["calendar"].get(date, [])}


def create_event(world, title, date, time):
    event = {"title": title, "date": date, "time": time}
    world["calendar"].setdefault(date, []).append({"title": title, "time": time})
    world["events_created"].append(event)
    return {"status": "created", **event}


def lookup_contact(world, name):
    email = world["contacts"].get(name.strip().lower())
    return {"name": name, "email": email} if email else {"error": f"No contact named {name}"}


def send_email(world, to, subject, body):
    world["emails_sent"].append({"to": to, "subject": subject, "body": body})
    return {"status": "sent", "to": to}


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.USub: operator.neg, ast.Pow: operator.pow}


def _evaluate(node):
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_evaluate(node.left), _evaluate(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_evaluate(node.operand))
    raise ValueError("Only numbers and + - * / ** are allowed.")


def calculator(world, expression):
    try:
        return {"expression": expression, "result": round(_evaluate(ast.parse(expression, mode="eval")), 2)}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Could not evaluate {expression!r}: {exc}"}


def search_notes(world, query, notes_index=None, llm=None, mode="keyword"):
    from mini_muse import week3_knowledge as knowledge

    index = notes_index or knowledge.build_index()
    results = knowledge.search(index, query, k=3, mode=mode, llm=llm)
    return {"query": query, "results": [{"source": r["source"], "text": r["text"]} for r in results]}


FUNCTIONS = {"get_weather": get_weather, "check_calendar": check_calendar, "create_event": create_event,
             "lookup_contact": lookup_contact, "send_email": send_email, "calculator": calculator,
             "search_notes": search_notes}


def schemas(names=CORE_TOOLS) -> list[dict]:
    return [SCHEMAS[n] for n in names]


def execute(world: dict, name: str, args: dict, **extra) -> dict:
    """Run one tool. Errors become results the model can read, never crashes."""
    if name not in FUNCTIONS:
        return {"error": f"Unknown tool {name!r}."}
    try:
        if name == "search_notes":
            return search_notes(world, **args, **extra)
        return FUNCTIONS[name](world, **args)
    except TypeError as exc:
        return {"error": f"Bad arguments for {name}: {exc}"}


# ------------------------------------------------------------------ one round of tool calling
def system_prompt() -> str:
    return persona.system_prompt("This step: use the tools to get real data before you answer.")


def answer_with_tools(llm, text: str, world: dict | None = None, tool_names=CORE_TOOLS, registry=None) -> dict:
    """Model picks tools once, the app runs them, the model answers. Returns a trace.

    registry: optional ToolRegistry of enabled connectors; when None, the fake tools are used.
    Week 4 deliberately sends email without asking, so there is no approval gate here even
    when a live email connector is behind send_email.
    """
    world = world if world is not None else new_world()
    runner = registry.execute if registry else execute
    tool_schemas = registry.schemas_for(tool_names) if registry else schemas(tool_names)
    messages = [{"role": "system", "content": system_prompt()}, {"role": "user", "content": text}]
    first = llm.chat(messages, tools=tool_schemas)
    calls = []
    if first.tool_calls:
        messages.append(first.as_message())
        for call in first.tool_calls:
            args, error = parse_arguments(call.arguments)
            result = {"error": error} if error else runner(world, call.name, args)
            calls.append({"tool": call.name, "args": args, "result": result})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
        answer = llm.chat(messages).content  # no tools offered: the round is over
    else:
        answer = first.content
    return {"query": text, "version": "mini-muse-week4", "tool_calls": calls, "answer": answer,
            "final_state": side_effects(world), "messages": messages}


if __name__ == "__main__":
    from mini_muse.llm import cli_llm

    trace = answer_with_tools(cli_llm(), " ".join(sys.argv[1:]) or "What's the weather in Detroit?")
    for c in trace["tool_calls"]:
        print(f"  → {c['tool']}({c['args']}) = {c['result']}")
    print(f"\n{trace['answer']}\n\nSide effects: {trace['final_state']}")
