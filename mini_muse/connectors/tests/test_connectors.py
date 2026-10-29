"""Offline tests for the connectors: schema strictness, the registry, and live paths.

Every live path is exercised with the real service stubbed out (no network, no Google
libraries required): the weather client, `smtplib`, and the Calendar `_service` are all
monkeypatched. The point is to prove the *normalization* and *approval gating*, not the
third-party SDKs.
"""

from __future__ import annotations

import pytest

from mini_muse import week4_tools
from mini_muse.connectors import CONNECTORS, build_registry
from mini_muse.connectors import email_smtp, google_calendar, weather
from mini_muse.world import new_world


# ------------------------------------------------------------------ schema strictness
def test_connector_tool_names_and_args_match_week4_schemas():
    """Each connector owns real SCHEMAS keys, with identical argument names (Week 6 grading)."""
    for conn in CONNECTORS:
        for name in conn.tool_names:
            assert name in week4_tools.SCHEMAS, f"{conn.name} exposes unknown tool {name!r}"
        for schema in conn.schemas():
            fname = schema["function"]["name"]
            assert schema == week4_tools.SCHEMAS[fname], f"{fname} schema drifted from week4_tools"


def test_every_schema_tool_is_covered_by_exactly_one_connector_or_is_a_builtin():
    owned = [name for conn in CONNECTORS for name in conn.tool_names]
    assert sorted(owned) == sorted(owned[:]) and len(owned) == len(set(owned)), "tools double-owned"
    from mini_muse.connectors.registry import BUILTIN_TOOLS

    assert set(owned) | set(BUILTIN_TOOLS) == set(week4_tools.ALL_TOOLS)


# ------------------------------------------------------------------ registry == default (simulated)
def test_all_simulated_registry_is_a_drop_in_for_week4_tools():
    world = new_world()
    reg = build_registry(CONNECTORS, {}, world=world)  # nothing enabled -> all simulated

    assert reg.names == week4_tools.ALL_TOOLS
    assert reg.schemas_for(week4_tools.ALL_TOOLS) == week4_tools.schemas(week4_tools.ALL_TOOLS)
    assert reg.schemas_for(week4_tools.CORE_TOOLS) == week4_tools.schemas(week4_tools.CORE_TOOLS)
    # No live backend => only send_email is risky, exactly like Week 5's RISKY_TOOLS.
    assert reg.risky == {"send_email"}


def test_simulated_execute_matches_week4_execute_for_every_tool():
    reg = build_registry(CONNECTORS, {}, world=new_world())
    cases = [
        ("get_weather", {"city": "Detroit"}),
        ("check_calendar", {"date": "2026-10-27"}),
        ("create_event", {"title": "Haircut", "date": "2026-10-27", "time": "14:00"}),
        ("lookup_contact", {"name": "Maya"}),
        ("send_email", {"to": "maya@example.com", "subject": "Hi", "body": "Hello"}),
        ("calculator", {"expression": "85 * 20 / 100"}),
    ]
    for name, args in cases:
        w_reg, w_ref = new_world(), new_world()
        assert reg.execute(w_reg, name, args) == week4_tools.execute(w_ref, name, args)
        assert w_reg == w_ref  # identical world mutations


def test_unknown_tool_and_bad_arguments_become_results_not_crashes():
    reg = build_registry(CONNECTORS, {}, world=new_world())
    assert "error" in reg.execute(new_world(), "nope", {})
    assert "error" in reg.execute(new_world(), "get_weather", {"wrong": "arg"})


# ------------------------------------------------------------------ live gating / fallback
def _ready_calendar(monkeypatch):
    """Make the calendar connector report live-ready without touching the filesystem."""
    monkeypatch.setattr(google_calendar, "_credentials_path", lambda creds: "x")
    monkeypatch.setattr(google_calendar, "_token_path", lambda creds: "y")
    import os

    monkeypatch.setattr(os.path, "exists", lambda path: True)


def test_live_email_makes_send_email_risky():
    sel = {"email": {"enabled": True, "mode": "live",
                     "creds": {"smtp_host": "h", "smtp_port": "587",
                               "smtp_username": "u", "smtp_app_password": "p"}}}
    reg = build_registry(CONNECTORS, sel, world=new_world())
    assert "send_email" in reg.risky


def test_live_calendar_makes_create_event_risky_when_ready(monkeypatch):
    _ready_calendar(monkeypatch)
    sel = {"calendar": {"enabled": True, "mode": "live", "creds": {}}}
    reg = build_registry(CONNECTORS, sel, world=new_world())
    assert "create_event" in reg.risky


def test_live_requested_but_not_ready_falls_back_to_simulated(monkeypatch):
    # Calendar: creds/token files do not exist -> readiness is False -> simulated.
    import os

    monkeypatch.setattr(os.path, "exists", lambda path: False)
    sel = {"calendar": {"enabled": True, "mode": "live", "creds": {}}}
    reg = build_registry(CONNECTORS, sel, world=new_world())
    assert "create_event" not in reg.risky  # simulated create_event is not gated


# ------------------------------------------------------------------ weather (live, stubbed)
def test_weather_live_normalizes_to_the_fake_shape(monkeypatch):
    monkeypatch.setattr(
        "labs.week4_tool_calling.weather.get_weather",
        lambda city: {"location": "Detroit", "state": "Michigan", "country": "US",
                      "temperature_f": 54.3, "feels_like_f": 49.0},
    )
    result = weather._live_get_weather(new_world(), "Detroit")
    assert result == {"city": "Detroit, Michigan", "temp_f": 54,
                      "feels_like_f": 49.0, "conditions": "cold"}


def test_weather_live_passes_through_service_errors(monkeypatch):
    monkeypatch.setattr("labs.week4_tool_calling.weather.get_weather",
                        lambda city: {"error": "Location not found."})
    assert weather._live_get_weather(new_world(), "asdf") == {"error": "Location not found."}


def test_weather_live_never_raises(monkeypatch):
    def boom(city):
        raise RuntimeError("network down")

    monkeypatch.setattr("labs.week4_tool_calling.weather.get_weather", boom)
    result = weather._live_get_weather(new_world(), "Detroit")
    assert "error" in result  # caught, not raised


# ------------------------------------------------------------------ email (live, stubbed smtp)
class _FakeSMTP:
    """Stands in for smtplib.SMTP / SMTP_SSL. Records what it was asked to send."""

    sent: list = []
    logins: list = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port = host, port

    def starttls(self):
        pass

    def login(self, username, password):
        _FakeSMTP.logins.append((username, password))

    def send_message(self, message):
        _FakeSMTP.sent.append(message)

    def quit(self):
        pass


@pytest.fixture
def smtp(monkeypatch):
    _FakeSMTP.sent, _FakeSMTP.logins = [], []
    monkeypatch.setattr(email_smtp.smtplib, "SMTP", _FakeSMTP)
    monkeypatch.setattr(email_smtp.smtplib, "SMTP_SSL", _FakeSMTP)
    return _FakeSMTP


def _email_creds():
    return {"smtp_host": "smtp.example.com", "smtp_port": "587",
            "smtp_username": "me@example.com", "smtp_app_password": "secret",
            "smtp_from": "me@example.com"}


def test_email_live_send_mirrors_into_world_and_normalizes(smtp):
    world = new_world()
    send = email_smtp._live_send_email(_email_creds())
    result = send(world, "maya@example.com", "Lunch?", "Noon tomorrow")
    assert result == {"status": "sent", "to": "maya@example.com"}
    assert world["emails_sent"] == [{"to": "maya@example.com", "subject": "Lunch?", "body": "Noon tomorrow"}]
    assert len(smtp.sent) == 1 and smtp.sent[0]["To"] == "maya@example.com"
    assert smtp.logins == [("me@example.com", "secret")]


def test_email_live_never_raises_on_failure(monkeypatch):
    def boom(*a, **k):
        raise OSError("connection refused")

    monkeypatch.setattr(email_smtp, "_connection", boom)
    world = new_world()
    result = email_smtp._live_send_email(_email_creds())(world, "x@y.com", "s", "b")
    assert "error" in result
    assert world["emails_sent"] == []  # nothing recorded on failure


def test_email_send_is_risky_in_both_modes():
    conn = email_smtp.EmailConnector()
    assert conn.risky_tools("simulated") == {"send_email"}
    assert conn.risky_tools("live") == {"send_email"}


def test_email_readiness_reports_missing_credentials():
    conn = email_smtp.EmailConnector()
    status = conn.readiness("live", {"smtp_host": "h"})
    assert not status.ready and "Missing" in status.detail
    assert conn.readiness("simulated", {}).ready


# ------------------------------------------------------------------ calendar (live, stubbed service)
class _Result:
    """A tiny stand-in for a Google API request: execute() returns a fixed payload."""

    def __init__(self, payload):
        self._payload = payload

    def execute(self):
        return self._payload


class _FakeEvents:
    def __init__(self, service):
        self.service = service

    def list(self, **kwargs):
        self.service.list_kwargs = kwargs
        return _Result({"items": self.service.items})

    def insert(self, calendarId, body):
        self.service.inserted.append({"calendarId": calendarId, "body": body})
        return _Result({"id": "evt1"})


class _FakeCalendars:
    def get(self, calendarId):
        return _Result({"timeZone": "America/Detroit"})


class _FakeService:
    def __init__(self, items=None):
        self.items = items or []
        self.inserted = []
        self.list_kwargs = None

    def events(self):
        return _FakeEvents(self)

    def calendars(self):
        return _FakeCalendars()


def test_calendar_live_check_normalizes_events(monkeypatch):
    items = [
        {"summary": "Standup", "start": {"dateTime": "2026-10-27T09:30:00-04:00"}},
        {"summary": "All day", "start": {"date": "2026-10-27"}},
    ]
    monkeypatch.setattr(google_calendar, "_service", lambda creds: _FakeService(items))
    check = google_calendar._live_check_calendar({})
    result = check(new_world(), "2026-10-27")
    assert result == {"date": "2026-10-27", "events": [
        {"title": "Standup", "time": "09:30"},
        {"title": "All day", "time": ""},
    ]}


def test_calendar_live_check_never_raises(monkeypatch):
    def boom(creds):
        raise RuntimeError("no token")

    monkeypatch.setattr(google_calendar, "_service", boom)
    result = google_calendar._live_check_calendar({})(new_world(), "2026-10-27")
    assert "error" in result


def test_calendar_live_create_event_mirrors_world(monkeypatch):
    service = _FakeService()
    monkeypatch.setattr(google_calendar, "_service", lambda creds: service)

    world = new_world()
    create = google_calendar._live_create_event({})
    result = create(world, "Haircut", "2026-10-27", "14:00")
    assert result == {"status": "created", "title": "Haircut", "date": "2026-10-27", "time": "14:00"}
    assert world["events_created"] == [{"title": "Haircut", "date": "2026-10-27", "time": "14:00"}]
    assert world["calendar"]["2026-10-27"][-1] == {"title": "Haircut", "time": "14:00"}
    assert service.inserted and service.inserted[0]["body"]["summary"] == "Haircut"


def test_calendar_live_create_event_never_raises(monkeypatch):
    monkeypatch.setattr(google_calendar, "_service",
                        lambda creds: (_ for _ in ()).throw(RuntimeError("boom")))
    result = google_calendar._live_create_event({})(new_world(), "T", "2026-10-27", "14:00")
    assert "error" in result


def test_calendar_risky_only_live():
    conn = google_calendar.GoogleCalendarConnector()
    assert conn.risky_tools("live") == {"create_event"}
    assert conn.risky_tools("simulated") == set()
