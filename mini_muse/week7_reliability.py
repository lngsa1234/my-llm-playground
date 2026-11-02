"""Week 7 · Reliability: tracing, retries, timeouts, fallbacks and fault injection.

A demo works when everything works. Production is about what happens when it doesn't.
Every model call and tool call in Mini Muse goes through a `Runtime`, which:

    traces      records a span per call: what, how long, tokens, success or error
    retries     tries a failed call again, with a short backoff, up to `max_retries`
    times out   treats a tool that takes longer than `tool_timeout_s` as failed
    falls back  switches to `fallback_model` if the main model keeps failing

and lets you break things on purpose (fault injection) to check that it copes:

    faults={"get_weather": "flaky"}    fails on the first attempt, then works
    faults={"get_weather": "down"}     always fails
    faults={"check_calendar": "slow"}  takes longer than the timeout
    llm_fault="flaky" | "down"         the main model fails once / always

The cap on agent-loop steps (Week 5's `max_steps`) is the third safety net.

Try it:  python3 -m mini_muse.week7_reliability
         python3 -m mini_muse.week7_reliability --fault get_weather=down --retries 0
         python3 -m mini_muse.week7_reliability "Schedule yoga on 2026-10-28 at 18:00" --fault check_calendar=slow
"""

from __future__ import annotations

import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field

FAULTS = ["flaky", "down", "slow"]


class TransientError(Exception):
    """A failure worth retrying: a dropped connection, a 503, a timeout."""


@dataclass
class Span:
    name: str
    kind: str          # "llm" or "tool"
    attempt: int
    ms: float = 0.0
    ok: bool = True
    error: str = ""
    tokens: int = 0
    note: str = ""

    def row(self) -> dict:
        return {"Call": self.name, "Kind": self.kind, "Attempt": self.attempt, "ms": round(self.ms, 1),
                "OK": "✓" if self.ok else "✗", "Tokens": str(self.tokens or ""), "Error": self.error, "Note": self.note}


@dataclass
class Tracer:
    spans: list[Span] = field(default_factory=list)

    @contextmanager
    def span(self, name: str, kind: str, attempt: int = 1):
        record = Span(name, kind, attempt)
        started = time.perf_counter()
        try:
            yield record
        except Exception as exc:
            record.ok, record.error = False, f"{type(exc).__name__}: {exc}"
            raise
        finally:
            record.ms = (time.perf_counter() - started) * 1000
            self.spans.append(record)

    def summary(self) -> dict:
        llm = [s for s in self.spans if s.kind == "llm"]
        tools = [s for s in self.spans if s.kind == "tool"]
        return {"llm_calls": len(llm), "tool_calls": len(tools), "errors": sum(not s.ok for s in self.spans),
                "retries": sum(s.attempt > 1 for s in self.spans), "tokens": sum(s.tokens for s in llm),
                "total_ms": round(sum(s.ms for s in self.spans), 1)}


@dataclass
class Runtime:
    max_retries: int = 0
    backoff_s: float = 0.0
    tool_timeout_s: float = 0.5
    fallback_model: str | None = None
    faults: dict = field(default_factory=dict)   # tool name -> "flaky" | "down" | "slow"
    llm_fault: str | None = None                 # "flaky" | "down"
    slow_tool_s: float = 1.0                     # how long a "slow" tool pretends to take
    tracer: Tracer = field(default_factory=Tracer)
    sleep: Callable[[float], None] = time.sleep

    def __post_init__(self):
        self._seen: dict[str, int] = {}

    # ------------------------------------------------------------ fault injection
    def _inject(self, key: str, fault: str | None) -> None:
        self._seen[key] = self._seen.get(key, 0) + 1
        if fault == "down":
            raise TransientError("service unavailable (injected)")
        if fault == "flaky" and self._seen[key] == 1:
            raise TransientError("connection reset (injected, first attempt only)")

    def _backoff(self, attempt: int) -> None:
        if self.backoff_s:
            self.sleep(self.backoff_s * 2 ** (attempt - 1))

    # ------------------------------------------------------------ tools
    def call_tool(self, execute, world: dict, name: str, args: dict, **extra) -> dict:
        """Run a tool with tracing, timeout and retries. Returns an error result, never raises."""
        last_error = ""
        for attempt in range(1, self.max_retries + 2):
            try:
                with self.tracer.span(name, "tool", attempt) as span:
                    fault = self.faults.get(name)
                    self._inject(f"tool:{name}:{sorted(args.items())}", fault)
                    if fault == "slow":
                        # Simulated latency: wait up to the timeout, then give up if it is still "running".
                        self.sleep(min(self.slow_tool_s, self.tool_timeout_s))
                        if self.slow_tool_s > self.tool_timeout_s:
                            raise TransientError(f"timed out after {self.tool_timeout_s:.2f}s")
                        span.note = f"slow ({self.slow_tool_s:.2f}s) but within the timeout"
                    return execute(world, name, args, **extra)
            except TransientError as exc:
                last_error = str(exc)
                if attempt <= self.max_retries:
                    self._backoff(attempt)
        attempts = self.max_retries + 1
        return {"error": f"{name} failed after {attempts} attempt{'s' * (attempts > 1)}: {last_error}. "
                         "Tell the user it is unavailable right now; do not guess."}

    # ------------------------------------------------------------ model
    def call_llm(self, llm, messages: list[dict], tools: list[dict] | None = None):
        """A model call with tracing and retries, then one try on the fallback model."""
        models = [None] + ([self.fallback_model] if self.fallback_model else [])
        last: Exception | None = None
        for model in models:
            label = f"llm:{model or llm.model}"
            for attempt in range(1, self.max_retries + 2):
                try:
                    with self.tracer.span(label, "llm", attempt) as span:
                        if model is None:
                            self._inject("llm", self.llm_fault)
                        before = llm.usage.input_tokens + llm.usage.output_tokens
                        reply = llm.chat(messages, tools=tools, model=model)
                        span.tokens = llm.usage.input_tokens + llm.usage.output_tokens - before
                        if model:
                            span.note = "fallback model"
                        return reply
                except TransientError as exc:
                    last = exc
                    if attempt <= self.max_retries:
                        self._backoff(attempt)
        raise RuntimeError(f"The model is unavailable: {last}")


if __name__ == "__main__":
    import argparse

    from mini_muse.llm import cli_llm
    from mini_muse.week5_agent import run

    parser = argparse.ArgumentParser(description="Run Mini Muse through the Week 7 runtime with faults injected.")
    parser.add_argument("request", nargs="*", help="What to ask Mini Muse.")
    parser.add_argument("--fault", action="append", default=[], metavar="TOOL=FAULT",
                        help=f"Break a tool, e.g. get_weather=flaky. Faults: {', '.join(FAULTS)}. Repeatable.")
    parser.add_argument("--llm-fault", choices=["flaky", "down"], help="Break the main model.")
    parser.add_argument("--retries", type=int, default=2, help="Retries per call (default 2).")
    parser.add_argument("--timeout", type=float, default=0.5, help="Tool timeout in seconds (default 0.5).")
    parser.add_argument("--fallback", help="Fallback model if the main model keeps failing.")
    args = parser.parse_args()

    text = " ".join(args.request)
    faults = dict(f.split("=", 1) for f in args.fault)
    if not text:
        text = "What's the weather in Detroit, and what's on my calendar on 2026-10-29?"
        print(f'No request given, so using the example: "{text}"')
    if not args.request and not args.fault and not args.llm_fault:
        faults = {"get_weather": "flaky"}
        print("No faults given, so get_weather is set to flaky (fails once, then works).")
        print("Try: python3 -m mini_muse.week7_reliability --fault get_weather=down --retries 0\n")

    runtime = Runtime(max_retries=args.retries, tool_timeout_s=args.timeout, fallback_model=args.fallback,
                      faults=faults, llm_fault=args.llm_fault)
    print(f"Faults: {faults or 'none'} · model fault: {args.llm_fault or 'none'} · retries: {args.retries} "
          f"· timeout: {args.timeout}s · fallback: {args.fallback or 'none'}\n")
    try:
        trace = run(cli_llm(), text, runtime=runtime)
        print(f"Mini Muse: {trace['answer']}\n")
    except RuntimeError as exc:
        print(f"Mini Muse failed: {exc}\n")

    print("Trace:")
    for span in runtime.tracer.spans:
        status = "ok " if span.ok else "ERR"
        extra = f"  {span.error or span.note}".rstrip()
        print(f"  {status} {span.kind:4} {span.name:24} attempt {span.attempt}  {span.ms:7.1f} ms{extra}")
    summary = runtime.tracer.summary()
    print(f"\n{summary['llm_calls']} model calls · {summary['tool_calls']} tool calls · "
          f"{summary['errors']} errors · {summary['retries']} retries · {summary['tokens']} tokens")
