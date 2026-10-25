"""Week 7 core logic: what happens to an LLM feature when the demo meets real traffic.

One small production-style task (classify a support ticket into JSON) is sent many
times while failures are injected at chosen rates:

    rate limit (429)   fails fast; retry after a pause
    server error (503) fails fast; retry
    hang               no answer; without a timeout the caller waits until the server gives up (60 s)
    slow               answers, but far slower than usual
    malformed output   answers with broken JSON. A naive caller passes it on as a "success"

The same requests run under two policies, side by side:

    naive     one attempt, no timeout, no output check
    hardened  retries with exponential backoff and jitter, a timeout per attempt,
              JSON validated against a schema (a bad answer is retried), a fallback model

and every attempt is traced, so you can see where time and money went.

Simulated mode needs no API key and runs instantly: latency is simulated, not waited
for. Live mode makes real calls (faults are still injected on top, so you can see them).
"""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Literal, Optional

from pydantic import BaseModel, ValidationError

from labs.shared.settings import ModelSettings

HANG_SECONDS = 60.0  # how long a server takes to give up on a hung request
RETRYABLE = {"rate_limit", "server_error", "timeout", "malformed"}


class TicketLabel(BaseModel):
    category: Literal["billing", "bug", "feature", "account", "other"]
    urgency: Literal["low", "medium", "high"]
    summary: str


TICKETS = [
    ("I was charged twice for my October subscription.", "billing", "high"),
    ("The export button does nothing on Safari.", "bug", "medium"),
    ("Could you add a dark mode to the mobile app?", "feature", "low"),
    ("I can't log in after resetting my password.", "account", "high"),
    ("Where can I download last year's invoices?", "billing", "low"),
    ("The dashboard takes over a minute to load since yesterday.", "bug", "high"),
    ("Please support exporting reports to CSV.", "feature", "medium"),
    ("How do I change the email on my account?", "account", "low"),
    ("Your app crashed and I lost an hour of work!", "bug", "high"),
    ("Do you offer a discount for nonprofits?", "billing", "medium"),
    ("Can I invite a teammate who uses a different domain?", "account", "medium"),
    ("Love the product, just saying thanks.", "other", "low"),
]

INSTRUCTIONS = ("Classify the support ticket. Reply with JSON only, no prose: "
                '{"category": "billing|bug|feature|account|other", "urgency": "low|medium|high", '
                '"summary": "<= 12 words"}')


@dataclass
class Faults:
    rate_limit: float = 0.10
    server_error: float = 0.05
    hang: float = 0.05
    slow: float = 0.10
    malformed: float = 0.10


@dataclass
class Policy:
    name: str
    max_retries: int = 0
    backoff_s: float = 0.5
    jitter: bool = True
    timeout_s: Optional[float] = None
    validate: bool = False
    fallback_model: Optional[str] = None


NAIVE = Policy("Naive")


def hardened(max_retries=3, backoff_s=0.5, timeout_s=8.0, validate=True, fallback_model=None) -> Policy:
    return Policy("Hardened", max_retries, backoff_s, True, timeout_s, validate, fallback_model or None)


@dataclass
class Attempt:
    model: str
    outcome: str          # ok | rate_limit | server_error | timeout | malformed (invalid JSON caught)
    seconds: float
    input_tokens: int = 0
    output_tokens: int = 0
    text: str = ""
    note: str = ""
    fault: Optional[str] = None  # the fault injected into this attempt, if any


@dataclass
class RequestResult:
    id: int
    ticket: str
    status: str           # ok | failed | silent_bad
    seconds: float
    cost: float
    attempts: list = field(default_factory=list)
    used_fallback: bool = False
    label: Optional[dict] = None


# ------------------------------------------------------------------ backends
def _roll(rng: random.Random, faults: Faults) -> str | None:
    """Pick at most one fault for this attempt, from the configured rates."""
    x = rng.random()
    for name in ("rate_limit", "server_error", "hang", "slow", "malformed"):
        p = getattr(faults, name)
        if x < p:
            return name
        x -= p
    return None


class SimulatedBackend:
    """No network: latency and tokens are drawn from simple distributions. Instant and free."""

    live = False

    def attempt(self, model: str, ticket: tuple, rng: random.Random, faults: Faults, timeout_s, primary: bool) -> Attempt:
        fault = _roll(rng, faults)
        result = self._attempt(model, ticket, rng, fault, timeout_s, primary)
        result.fault = fault
        return result

    def _attempt(self, model, ticket, rng, fault, timeout_s, primary) -> Attempt:
        base = rng.lognormvariate(math.log(1.2 if primary else 0.7), 0.35)
        if fault == "rate_limit":
            return Attempt(model, "rate_limit", 0.1, note="429 Too Many Requests (injected)")
        if fault == "server_error":
            return Attempt(model, "server_error", 0.3, note="503 Service Unavailable (injected)")
        if fault == "hang":
            waited = timeout_s if timeout_s else HANG_SECONDS
            return Attempt(model, "timeout", waited, note=f"no answer; gave up after {waited:.0f}s (injected hang)")
        seconds = base * (6 if fault == "slow" else 1)
        if timeout_s and seconds > timeout_s:
            return Attempt(model, "timeout", timeout_s, note=f"slow answer cut off at {timeout_s:.0f}s")
        text = json.dumps({"category": ticket[1], "urgency": ticket[2], "summary": ticket[0][:60]})
        if fault == "malformed":
            text = text[: len(text) // 2]
        tokens_in, tokens_out = 120 + rng.randint(0, 30), 30 + rng.randint(0, 15)
        note = {"slow": "slow (injected)", "malformed": "output cut in half (injected)"}.get(fault, "")
        return Attempt(model, "ok", seconds, tokens_in, tokens_out, text, note=note)


class LiveBackend:
    """Real API calls with the SDK's own retries turned off, so every retry is ours and visible.

    Faults are injected before the call (429, 503, hang) or after it (malformed output);
    "slow" only exists in simulated mode.
    """

    live = True

    def __init__(self, settings: ModelSettings, client=None):
        self.settings = settings
        if client is None:
            from openai import OpenAI

            client = OpenAI(max_retries=0)
        self.client = client

    def attempt(self, model: str, ticket: tuple, rng: random.Random, faults: Faults, timeout_s, primary: bool) -> Attempt:
        fault = _roll(rng, Faults(faults.rate_limit, faults.server_error, faults.hang, 0.0, faults.malformed))
        result = self._attempt(model, ticket, fault, timeout_s)
        result.fault = fault
        return result

    def _attempt(self, model, ticket, fault, timeout_s) -> Attempt:
        if fault == "rate_limit":
            return Attempt(model, "rate_limit", 0.0, note="429 (injected, no call made)")
        if fault == "server_error":
            return Attempt(model, "server_error", 0.0, note="503 (injected, no call made)")
        if fault == "hang":
            waited = timeout_s if timeout_s else HANG_SECONDS
            return Attempt(model, "timeout", waited, note=f"hang (injected, counted as {waited:.0f}s, not waited)")
        started = time.perf_counter()
        try:
            r = self.client.with_options(timeout=timeout_s or HANG_SECONDS).responses.create(
                model=model, instructions=INSTRUCTIONS, input=ticket[0], max_output_tokens=self.settings.max_output_tokens)
        except Exception as exc:  # noqa: BLE001 - real failures are classified, never raised
            name = type(exc).__name__
            outcome = ("rate_limit" if "RateLimit" in name else "timeout" if "Timeout" in name else "server_error")
            return Attempt(model, outcome, time.perf_counter() - started, note=f"{name}: {exc}"[:160])
        text = r.output_text or ""
        if fault == "malformed":
            text = text[: len(text) // 2]
        return Attempt(model, "ok", time.perf_counter() - started, r.usage.input_tokens, r.usage.output_tokens, text,
                       note="output cut in half (injected)" if fault == "malformed" else "")


# ------------------------------------------------------------------ the policy around each request
def parse_label(text: str) -> dict | None:
    try:
        return TicketLabel.model_validate_json(text.strip().removeprefix("```json").removesuffix("```").strip()).model_dump()
    except (ValidationError, ValueError):
        return None


def run_request(backend, request_id: int, ticket: tuple, policy: Policy, faults: Faults, settings: ModelSettings,
                rng: random.Random, sleep: Callable[[float], None] | None = None) -> RequestResult:
    """One request under one policy. Simulated time adds the backoff instead of sleeping."""
    attempts, seconds, cost = [], 0.0, 0.0
    models = [(settings.model, True)] + ([(policy.fallback_model, False)] if policy.fallback_model else [])
    for model, primary in models:
        tries = policy.max_retries + 1 if primary else 1
        for n in range(1, tries + 1):
            a = backend.attempt(model, ticket, rng, faults, policy.timeout_s, primary)
            if a.outcome == "ok":
                label = parse_label(a.text)
                if label is None:
                    a.outcome = "malformed" if policy.validate else "ok"
                    a.note = (a.note + "; " if a.note else "") + ("invalid JSON caught" if policy.validate
                                                                   else "invalid JSON passed on unchecked")
            attempts.append(a)
            seconds += a.seconds
            cost += settings.cost(a.input_tokens, a.output_tokens)
            if a.outcome == "ok":
                label = parse_label(a.text)
                status = "ok" if label else "silent_bad"
                return RequestResult(request_id, ticket[0], status, seconds, cost, attempts, not primary, label)
            if n < tries and a.outcome in RETRYABLE:
                wait = policy.backoff_s * 2 ** (n - 1) * (rng.uniform(0.5, 1.5) if policy.jitter else 1)
                seconds += wait
                (sleep or (lambda _s: None))(wait)
    return RequestResult(request_id, ticket[0], "failed", seconds, cost, attempts, len(models) > 1)


def run_batch(backend, n: int, policy: Policy, faults: Faults, settings: ModelSettings, seed: int = 7,
              progress: Callable[[int, int], None] | None = None) -> list[RequestResult]:
    """Request i draws its faults from its own seed, so both policies face the same first attempts."""
    results = []
    for i in range(n):
        rng = random.Random(seed * 100_003 + i)
        results.append(run_request(backend, i + 1, TICKETS[i % len(TICKETS)], policy, faults, settings, rng,
                                   sleep=time.sleep if backend.live else None))
        if progress:
            progress(i + 1, n)
    return results


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def summarize(results: list[RequestResult]) -> dict:
    n = len(results) or 1
    latencies = [r.seconds for r in results]
    return {
        "requests": len(results),
        "ok": sum(r.status == "ok" for r in results) / n,
        "silent_bad": sum(r.status == "silent_bad" for r in results) / n,
        "failed": sum(r.status == "failed" for r in results) / n,
        "p50": percentile(latencies, 0.5),
        "p95": percentile(latencies, 0.95),
        "cost": sum(r.cost for r in results),
        "attempts": sum(len(r.attempts) for r in results),
        "fallbacks": sum(r.used_fallback and r.status == "ok" for r in results),
    }


def request_rows(results: list[RequestResult]) -> list[dict]:
    return [{"Request": r.id, "Status": r.status, "Attempts": len(r.attempts), "Seconds": round(r.seconds, 2),
             "Fallback": "yes" if r.used_fallback else "", "Path": " → ".join(a.outcome for a in r.attempts),
             "Ticket": r.ticket} for r in results]


def attempt_rows(result: RequestResult) -> list[dict]:
    return [{"#": i + 1, "Model": a.model, "Injected": a.fault or "", "Outcome": a.outcome, "Seconds": round(a.seconds, 2),
             "Tokens": a.input_tokens + a.output_tokens, "Note": a.note, "Output": a.text[:80]}
            for i, a in enumerate(result.attempts)]
