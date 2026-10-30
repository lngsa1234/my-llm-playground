"""Offline tests for the connectors: schema strictness, the registry, and live paths.

Every live path is exercised with the real service stubbed out (no network, no Google
libraries required): the weather client and the Gmail/Calendar `_service` builders are all
monkeypatched. The point is to prove the *normalization* and *approval gating*, not the
third-party SDKs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mini_muse import week4_tools
from mini_muse.connectors import CONNECTORS, build_registry
from mini_muse.connectors import gmail, google_calendar, weather
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

    # Contact lookup and note search are absent: Mini Muse no longer uses bundled fake data.
    assert set(owned) | set(BUILTIN_TOOLS) == set(week4_tools.ALL_TOOLS) - {"lookup_contact", "search_notes"}


# ------------------------------------------------------------------ live-only registry
def test_empty_registry_exposes_only_offline_builtins():
    world = new_world()
    reg = build_registry(CONNECTORS, {}, world=world)

    assert reg.names == ["calculator"]
    assert reg.schemas_for(week4_tools.ALL_TOOLS) == week4_tools.schemas(["calculator"])
    assert reg.risky == set()


def test_empty_registry_does_not_fall_back_to_fake_tools():
    reg = build_registry(CONNECTORS, {}, world=new_world())
    assert "error" in reg.execute(new_world(), "get_weather", {"city": "Detroit"})
    assert reg.execute(new_world(), "calculator", {"expression": "85 * 20 / 100"}) == {"expression": "85 * 20 / 100", "result": 17.0}


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


def _ready_gmail(monkeypatch):
    """Make the Gmail connector report live-ready without touching Streamlit or the network."""
    monkeypatch.setattr(gmail, "_web_oauth_config",
                        lambda: {"client_id": "x", "client_secret": "y", "redirect_uri": "z"})
    monkeypatch.setattr(gmail, "_session_token", lambda: "tok")


def test_live_email_makes_send_email_risky(monkeypatch):
    _ready_gmail(monkeypatch)
    sel = {"email": {"enabled": True, "mode": "live", "creds": {}}}
    reg = build_registry(CONNECTORS, sel, world=new_world())
    assert "send_email" in reg.risky


def test_live_calendar_makes_create_event_risky_when_ready(monkeypatch):
    _ready_calendar(monkeypatch)
    sel = {"calendar": {"enabled": True, "mode": "live", "creds": {}}}
    reg = build_registry(CONNECTORS, sel, world=new_world())
    assert "create_event" in reg.risky


def test_live_requested_but_not_ready_is_not_exposed(monkeypatch):
    import os

    monkeypatch.setattr(os.path, "exists", lambda path: False)
    sel = {"calendar": {"enabled": True, "mode": "live", "creds": {}}}
    reg = build_registry(CONNECTORS, sel, world=new_world())
    assert "create_event" not in reg.names


def test_calendar_default_paths_are_relative_to_project_not_process_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    assert google_calendar._credentials_path({}) == str(
        google_calendar.PROJECT_ROOT / "google_credentials.json"
    )
    assert google_calendar._token_path({}) == str(google_calendar.PROJECT_ROOT / "google_token.json")


def test_calendar_expands_user_supplied_paths():
    path = Path("~/private-google-client.json").expanduser()
    assert google_calendar._credentials_path({"google_credentials_path": "~/private-google-client.json"}) == str(path)


def test_hosted_oauth_callback_state_survives_a_redirect(monkeypatch):
    config = {"client_secret": "not-a-real-secret"}
    monkeypatch.setattr(google_calendar.time, "time", lambda: 1_000)

    state = google_calendar._callback_state(config)

    assert google_calendar._valid_callback_state(state, config)
    assert not google_calendar._valid_callback_state(state + "x", config)


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


# ------------------------------------------------------------------ email (Gmail API, stubbed service)
class _FakeMessages:
    def __init__(self, service):
        self.service = service

    def send(self, userId, body):
        self.service.sent.append({"userId": userId, "body": body})
        return _Result({"id": "msg1"})


class _FakeUsers:
    def __init__(self, service):
        self.service = service

    def messages(self):
        return _FakeMessages(self.service)


class _FakeGmailService:
    def __init__(self):
        self.sent = []

    def users(self):
        return _FakeUsers(self)


def test_gmail_live_send_mirrors_into_world_and_normalizes(monkeypatch):
    service = _FakeGmailService()
    monkeypatch.setattr(gmail, "_service", lambda: service)

    world = new_world()
    send = gmail._live_send_email({})
    result = send(world, "maya@example.com", "Lunch?", "Noon tomorrow")
    assert result == {"status": "sent", "to": "maya@example.com"}
    assert world["emails_sent"] == [{"to": "maya@example.com", "subject": "Lunch?", "body": "Noon tomorrow"}]
    assert len(service.sent) == 1 and service.sent[0]["userId"] == "me"
    assert "raw" in service.sent[0]["body"]  # a base64url-encoded MIME message


def test_gmail_live_never_raises_on_failure(monkeypatch):
    monkeypatch.setattr(gmail, "_service",
                        lambda: (_ for _ in ()).throw(RuntimeError("no token")))
    world = new_world()
    result = gmail._live_send_email({})(world, "x@y.com", "s", "b")
    assert "error" in result
    assert world["emails_sent"] == []  # nothing recorded on failure


def test_gmail_send_is_risky():
    conn = gmail.GmailConnector()
    assert conn.risky_tools("live") == {"send_email"}


def test_gmail_readiness_requires_connection(monkeypatch):
    monkeypatch.setattr(gmail, "_web_oauth_config",
                        lambda: {"client_id": "x", "client_secret": "y", "redirect_uri": "z"})
    monkeypatch.setattr(gmail, "_session_token", lambda: None)
    assert not gmail.GmailConnector().readiness("live", {}).ready
    monkeypatch.setattr(gmail, "_session_token", lambda: "tok")
    assert gmail.GmailConnector().readiness("live", {}).ready


def test_gmail_readiness_without_hosted_secrets_is_not_ready(monkeypatch):
    monkeypatch.setattr(gmail, "_web_oauth_config", lambda: None)
    assert not gmail.GmailConnector().readiness("live", {}).ready


def test_gmail_callback_state_is_tagged_and_survives_a_redirect(monkeypatch):
    config = {"client_secret": "not-a-real-secret"}
    monkeypatch.setattr(gmail.time, "time", lambda: 1_000)

    state = gmail._callback_state(config)

    assert state.split(".")[0] == "gmail"  # tagged so the shared redirect routes correctly
    assert gmail._valid_callback_state(state, config)
    assert not gmail._valid_callback_state(state + "x", config)
    # A calendar-tagged state must not validate as a Gmail callback.
    assert not gmail._valid_callback_state("calendar." + state.split(".", 1)[1], config)


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


def test_calendar_create_event_is_risky():
    conn = google_calendar.GoogleCalendarConnector()
    assert conn.risky_tools("live") == {"create_event"}
