"""Offline tests for the Week 7 reliability drill."""

import random
from types import SimpleNamespace

from labs.shared.settings import ModelSettings
from labs.week7_production import reliability as rel

SETTINGS = ModelSettings()
TICKET = rel.TICKETS[0]
NO_FAULTS = rel.Faults(0, 0, 0, 0, 0)


class Scripted:
    """A backend that returns attempts in order."""

    live = False

    def __init__(self, *attempts):
        self.attempts = list(attempts)

    def attempt(self, model, ticket, rng, faults, timeout_s, primary):
        outcome, text = self.attempts.pop(0)
        return rel.Attempt(model, outcome, 1.0, 100, 20, text)


GOOD = '{"category": "billing", "urgency": "high", "summary": "double charge"}'
BAD = '{"category": "billing", "urg'


def run(backend, policy):
    return rel.run_request(backend, 1, TICKET, policy, NO_FAULTS, SETTINGS, random.Random(1))


def test_naive_passes_broken_json_on_as_silent_bad():
    assert run(Scripted(("ok", BAD)), rel.NAIVE).status == "silent_bad"


def test_hardened_catches_broken_json_and_retries():
    r = run(Scripted(("ok", BAD), ("ok", GOOD)), rel.hardened(backoff_s=0))
    assert r.status == "ok" and [a.outcome for a in r.attempts] == ["malformed", "ok"]
    assert r.label["category"] == "billing"


def test_retries_then_fallback_then_failure():
    policy = rel.hardened(max_retries=1, backoff_s=0, fallback_model="backup")
    r = run(Scripted(("rate_limit", ""), ("server_error", ""), ("ok", GOOD)), policy)
    assert r.status == "ok" and r.used_fallback and r.attempts[-1].model == "backup"
    failed = run(Scripted(("rate_limit", ""), ("rate_limit", ""), ("timeout", "")), policy)
    assert failed.status == "failed" and len(failed.attempts) == 3


def test_backoff_doubles_and_is_added_to_simulated_time():
    policy = rel.Policy("p", max_retries=2, backoff_s=1.0, jitter=False)
    r = run(Scripted(("server_error", ""), ("server_error", ""), ("ok", GOOD)), policy)
    assert r.seconds == 3 * 1.0 + 1.0 + 2.0  # three attempts of 1 s, then waits of 1 s and 2 s


def test_simulated_hang_waits_for_server_without_timeout():
    hang_only = rel.Faults(0, 0, 1.0, 0, 0)
    backend = rel.SimulatedBackend()
    naive = rel.run_request(backend, 1, TICKET, rel.NAIVE, hang_only, SETTINGS, random.Random(1))
    assert naive.status == "failed" and naive.seconds == rel.HANG_SECONDS
    capped = rel.run_request(backend, 1, TICKET, rel.hardened(max_retries=0, timeout_s=5), hang_only, SETTINGS, random.Random(1))
    assert capped.seconds == 5


def test_hardened_beats_naive_on_the_same_faults():
    naive = rel.summarize(rel.run_batch(rel.SimulatedBackend(), 200, rel.NAIVE, rel.Faults(), SETTINGS))
    hard = rel.summarize(rel.run_batch(rel.SimulatedBackend(), 200, rel.hardened(), rel.Faults(), SETTINGS))
    assert hard["ok"] > naive["ok"] + 0.2 and hard["silent_bad"] == 0 < naive["silent_bad"]
    assert hard["p95"] < naive["p95"] and hard["cost"] > naive["cost"]


def test_same_seed_same_first_attempts():
    a = rel.run_batch(rel.SimulatedBackend(), 30, rel.NAIVE, rel.Faults(), SETTINGS, seed=3)
    b = rel.run_batch(rel.SimulatedBackend(), 30, rel.hardened(), rel.Faults(), SETTINGS, seed=3)
    assert [x.attempts[0].fault for x in a] == [y.attempts[0].fault for y in b]
    assert any(x.attempts[0].fault for x in a)


def test_live_backend_classifies_real_errors_and_injects_faults():
    class RateLimitError(Exception):
        pass

    def create(**kwargs):
        if kwargs["input"] == "boom":
            raise RateLimitError("slow down")
        return SimpleNamespace(output_text=GOOD, usage=SimpleNamespace(input_tokens=50, output_tokens=10))

    responses = SimpleNamespace(create=create)
    client = SimpleNamespace(with_options=lambda **_: SimpleNamespace(responses=responses))
    backend = rel.LiveBackend(SETTINGS, client=client)
    assert backend.attempt("m", ("boom",), random.Random(1), NO_FAULTS, 5, True).outcome == "rate_limit"
    ok = backend.attempt("m", TICKET, random.Random(1), NO_FAULTS, 5, True)
    assert ok.outcome == "ok" and rel.parse_label(ok.text)
    broken = backend.attempt("m", TICKET, random.Random(1), rel.Faults(0, 0, 0, 0, 1.0), 5, True)
    assert rel.parse_label(broken.text) is None


def test_percentile():
    assert rel.percentile([1, 2, 3, 4, 5], 0.5) == 3
    assert rel.percentile([], 0.95) == 0
