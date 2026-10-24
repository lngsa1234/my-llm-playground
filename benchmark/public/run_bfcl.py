"""
Score a model on BFCL-style tool-calling cases: Step 3 (tool evaluation)
of the Week 6 eval lab, on a real public benchmark.

Each case gives the model a user request and some function definitions.
We check that it calls the right function(s) with acceptable arguments,
or calls nothing at all for "irrelevance" cases.

    python3 benchmark/public/run_bfcl.py                      # oracle: replays the answers (checks the scorer)
    python3 benchmark/public/run_bfcl.py --model none          # never calls a tool (baseline)
    python3 benchmark/public/run_bfcl.py --model claude        # needs ANTHROPIC_API_KEY
    python3 benchmark/public/run_bfcl.py --data downloads/bfcl # use downloaded files instead of samples

Optional: CLAUDE_MODEL env var (default claude-sonnet-5-5).
This is a simplified checker for teaching. The official BFCL harness
handles more cases: https://github.com/ShishirPatil/gorilla
"""
import argparse
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


# ------------------------------------------------------------------ data
def load_cases(folder):
    cases = []
    for fname in sorted(os.listdir(folder)):
        if not fname.endswith(".jsonl") or fname.endswith("_answers.jsonl"):
            continue
        category = fname[:-len(".jsonl")]
        answers = {}
        ans_path = os.path.join(folder, f"{category}_answers.jsonl")
        if os.path.exists(ans_path):
            for line in open(ans_path, encoding="utf-8"):
                if line.strip():
                    a = json.loads(line)
                    answers[a["id"]] = a["ground_truth"]
        for line in open(os.path.join(folder, fname), encoding="utf-8"):
            if not line.strip():
                continue
            c = json.loads(line)
            c["category"] = category
            c["expected"] = [] if "irrelevance" in category else answers.get(c["id"])
            if c["expected"] is not None:
                cases.append(c)
    return cases


# ---------------------------------------------------------------- models
def oracle_model(case):
    """Replays the first acceptable answer. Should score 100%: proves the checker works."""
    calls = []
    for exp in case["expected"]:
        (name, params), = exp.items()
        args = {k: v[0] for k, v in params.items() if v and v[0] != ""}
        calls.append({"name": name, "args": args})
    return calls


def no_tool_model(case):
    return []


_TYPE_MAP = {"dict": "object", "float": "number", "tuple": "array", "any": None}


def _to_json_schema(s):
    """Convert BFCL's schema dialect (dict, float, tuple, any) to JSON Schema."""
    if not isinstance(s, dict):
        return s
    out = {}
    for k, v in s.items():
        if k == "type" and isinstance(v, str):
            t = _TYPE_MAP.get(v, v)
            if t:
                out["type"] = t
        elif k == "properties" and isinstance(v, dict):
            # keys here are parameter names, not schema keywords
            out[k] = {name: _to_json_schema(sub) for name, sub in v.items()}
        elif k == "items":
            out[k] = _to_json_schema(v) if isinstance(v, dict) else v
        elif k in ("optional",):
            continue
        else:
            out[k] = v
    return out


def claude_model(case):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("Set ANTHROPIC_API_KEY to use --model claude")
    # Tool names may not contain dots: map math.factorial -> math_factorial and back.
    names = {}
    tools = []
    for f in case["function"]:
        safe = re.sub(r"[^a-zA-Z0-9_-]", "_", f["name"])[:64]
        names[safe] = f["name"]
        tools.append({"name": safe, "description": f.get("description", ""),
                      "input_schema": _to_json_schema(f["parameters"])})
    messages = [{"role": m["role"], "content": m["content"]} for m in case["question"][0]]
    body = json.dumps({"model": os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5"),
                       "max_tokens": 1024, "temperature": 0,
                       "system": "Use the provided tools when they fit the request. "
                                 "If none fit, answer without calling a tool.",
                       "tools": tools, "messages": messages}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        content = json.loads(r.read())["content"]
    return [{"name": names.get(b["name"], b["name"]), "args": b["input"]}
            for b in content if b["type"] == "tool_use"]


MODELS = {"oracle": oracle_model, "none": no_tool_model, "claude": claude_model}


# --------------------------------------------------------------- checker
def _norm(v):
    if isinstance(v, str):
        return v.strip().lower()
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, (list, tuple)):
        return [_norm(x) for x in v]
    if isinstance(v, dict):
        return {k: _norm(x) for k, x in v.items()}
    return v


def check_call(call, expected):
    """expected = {func_name: {param: [acceptable values; "" = may be omitted]}}"""
    (name, params), = expected.items()
    if call["name"] != name:
        return False, f"called {call['name']}, expected {name}"
    for p, allowed in params.items():
        if p not in call["args"]:
            if "" not in allowed:
                return False, f"missing argument {p}"
            continue
        if _norm(call["args"][p]) not in [_norm(a) for a in allowed if a != ""]:
            return False, f"{p}={call['args'][p]!r} not in {allowed}"
    extra = set(call["args"]) - set(params)
    if extra:
        return False, f"unexpected argument(s) {sorted(extra)}"
    return True, ""


def score(case, calls):
    exp = case["expected"]
    if not exp:
        return (not calls), (not calls), ("" if not calls else f"called {calls[0]['name']} but no tool fits")
    if len(calls) != len(exp):
        right_tools = sorted(c["name"] for c in calls) == sorted(next(iter(e)) for e in exp)
        return right_tools, False, f"{len(calls)} call(s), expected {len(exp)}"
    remaining = list(exp)
    first_error = ""
    for call in calls:                      # parallel calls may come in any order
        for e in remaining:
            ok, why = check_call(call, e)
            if ok:
                remaining.remove(e)
                break
            first_error = first_error or why
    selection_ok = sorted(c["name"] for c in calls) == sorted(next(iter(e)) for e in exp)
    return selection_ok, not remaining, ("" if not remaining else first_error)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", choices=MODELS, default="oracle")
    ap.add_argument("--data", default=os.path.join(HERE, "samples", "bfcl"))
    ap.add_argument("--limit", type=int, default=0, help="max cases per category")
    args = ap.parse_args()

    data = args.data if os.path.isabs(args.data) or os.path.exists(args.data) else os.path.join(HERE, args.data)
    cases = load_cases(data)
    if args.limit:
        seen = {}
        cases = [c for c in cases if seen.setdefault(c["category"], []).append(1) or len(seen[c["category"]]) <= args.limit]

    model = MODELS[args.model]
    by_cat = {}
    print(f"BFCL tool-calling check — model: {args.model} — {len(cases)} cases from {os.path.relpath(data)}\n")
    for c in cases:
        try:
            calls = model(c)
        except Exception as e:  # noqa: BLE001
            calls, err = None, f"model error: {e}"
        if calls is None:
            sel, ok, why = False, False, err
        else:
            sel, ok, why = score(c, calls)
        s = by_cat.setdefault(c["category"], [0, 0, 0])
        s[0] += sel
        s[1] += ok
        s[2] += 1
        if not ok:
            print(f"  ✗ {c['id']:<22} {why}")

    print(f"\n{'category':<20}{'tool selection':>16}{'fully correct':>16}")
    tot = [0, 0, 0]
    for cat, (sel, ok, n) in by_cat.items():
        print(f"{cat:<20}{sel:>10}/{n:<5}{ok:>10}/{n:<5}")
        tot = [tot[0] + sel, tot[1] + ok, tot[2] + n]
    print(f"{'TOTAL':<20}{tot[0]:>10}/{tot[2]:<5}{tot[1]:>10}/{tot[2]:<5}"
          f"   accuracy {tot[1] / max(tot[2], 1):.0%}")


if __name__ == "__main__":
    main()
