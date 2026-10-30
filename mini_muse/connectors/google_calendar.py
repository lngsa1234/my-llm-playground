"""Google Calendar connector: read and create real events, or use the fake calendar.

Live mode uses the Google Calendar API (OAuth 2.0, scope calendar.events). The user
creates an OAuth client in Google Cloud, downloads its `credentials.json`, and clicks
"Connect Google Calendar" once; that opens a browser for consent and caches a
`token.json`. Both files live at user-set paths and are .gitignore'd. The one-time
consent runs `InstalledAppFlow.run_local_server` outside the agent loop, never inside it.

`check_calendar` has no side effects. `create_event` is approval-gated.
Live results are normalized to the fake shapes (`{"date", "events":[{"title","time"}]}`
and `{"status":"created", ...}`), and mirrored into `world` so the trace stays consistent.

The google-* libraries are imported lazily, so this module loads even when they are not
installed; the tools then return a clear error instead of crashing.
"""

from __future__ import annotations

from typing import Callable

from mini_muse import week4_tools
from mini_muse.connectors.base import ConnectorStatus, CredentialField, Mode

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

CREDENTIALS = [
    CredentialField("google_mcp_access_token", "Google MCP OAuth access token", secret=True,
                    help="OAuth token for an AI-powered-agent client configured for Google Calendar MCP."),
    CredentialField("google_calendar_id", "Calendar ID", default="primary",
                    help="'primary' is your main calendar."),
]

MCP_ENDPOINT = "https://calendarmcp.googleapis.com/mcp/v1"


def _mcp_call(creds: dict, tool: str, arguments: dict) -> dict:
    """Call Google's remote Calendar MCP server over Streamable HTTP."""
    import requests

    token = str(creds.get("google_mcp_access_token", "")).strip()
    try:
        response = requests.post(MCP_ENDPOINT, headers={"Authorization": f"Bearer {token}",
                                 "Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
                                 json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                       "params": {"name": tool, "arguments": arguments}}, timeout=30)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Google Calendar MCP unavailable: {exc}"}
    if "error" in payload:
        return {"error": str(payload["error"])}
    result = payload.get("result", {})
    return result.get("structuredContent") or result


def _mcp_check_calendar(creds: dict):
    def check_calendar(world, date):
        data = _mcp_call(creds, "list_events", {"calendarId": _calendar_id(creds),
                         "startTime": f"{date}T00:00:00", "endTime": f"{date}T23:59:59"})
        if "error" in data:
            return data
        return {"date": date, "events": [{"title": e.get("summary", "(no title)"),
                 "time": (e.get("start", {}).get("dateTime", "")[11:16])} for e in data.get("events", [])]}
    return check_calendar


def _mcp_create_event(creds: dict):
    def create_event(world, title, date, time):
        end_hour = f"{(int(time[:2]) + 1) % 24:02d}{time[2:]}"
        data = _mcp_call(creds, "create_event", {"calendarId": _calendar_id(creds), "event": {
            "summary": title, "start": {"dateTime": f"{date}T{time}:00"},
            "end": {"dateTime": f"{date}T{end_hour}:00"}}})
        if "error" in data:
            return data
        event = {"status": "created", "title": title, "date": date, "time": time}
        world.setdefault("events_created", []).append({k: event[k] for k in ("title", "date", "time")})
        return event
    return create_event


def _token_path(creds: dict) -> str:
    return str(creds.get("google_token_path", "") or "google_token.json").strip()


def _credentials_path(creds: dict) -> str:
    return str(creds.get("google_credentials_path", "") or "google_credentials.json").strip()


def _calendar_id(creds: dict) -> str:
    return str(creds.get("google_calendar_id", "") or "primary").strip()


def _load_credentials(creds: dict):
    """Load (and refresh) the cached OAuth token. Returns Credentials or raises."""
    import os

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    token = _token_path(creds)
    if not os.path.exists(token):
        raise FileNotFoundError("Not connected yet. Click 'Connect Google Calendar' first.")
    cred = Credentials.from_authorized_user_file(token, SCOPES)
    if not cred.valid and cred.expired and cred.refresh_token:
        cred.refresh(Request())
        with open(token, "w", encoding="utf-8") as handle:
            handle.write(cred.to_json())
    return cred


def _service(creds: dict):
    from googleapiclient.discovery import build

    return build("calendar", "v3", credentials=_load_credentials(creds), cache_discovery=False)


def connect(creds: dict) -> ConnectorStatus:
    """Run the one-time OAuth consent in a local browser and cache the token."""
    import os

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        return ConnectorStatus(False, "Install google-auth-oauthlib to connect.")

    client_file = _credentials_path(creds)
    if not os.path.exists(client_file):
        return ConnectorStatus(False, f"OAuth client file not found: {client_file}")
    try:
        flow = InstalledAppFlow.from_client_secrets_file(client_file, SCOPES)
        cred = flow.run_local_server(port=0)
        with open(_token_path(creds), "w", encoding="utf-8") as handle:
            handle.write(cred.to_json())
    except Exception as exc:  # noqa: BLE001
        return ConnectorStatus(False, f"Consent failed: {exc}")
    return ConnectorStatus(True, "Connected. Token cached.")


def _live_check_calendar(creds: dict) -> Callable:
    def check_calendar(world, date):
        try:
            service = _service(creds)
            response = service.events().list(
                calendarId=_calendar_id(creds),
                timeMin=f"{date}T00:00:00Z", timeMax=f"{date}T23:59:59Z",
                singleEvents=True, orderBy="startTime").execute()
        except Exception as exc:  # noqa: BLE001 - never crash the agent loop
            return {"error": f"Calendar unavailable: {exc}"}
        events = []
        for item in response.get("items", []):
            start = item.get("start", {})
            when = start.get("dateTime") or start.get("date") or ""
            time = when[11:16] if "T" in when else ""  # the HH:MM out of an RFC3339 timestamp
            events.append({"title": item.get("summary", "(no title)"), "time": time})
        return {"date": date, "events": events}

    return check_calendar


def _live_create_event(creds: dict) -> Callable:
    def create_event(world, title, date, time):
        try:
            service = _service(creds)
            calendar_id = _calendar_id(creds)
            try:
                tz = service.calendars().get(calendarId=calendar_id).execute().get("timeZone", "UTC")
            except Exception:  # noqa: BLE001 - fall back to UTC if the lookup fails
                tz = "UTC"
            end_hour = f"{(int(time[:2]) + 1) % 24:02d}{time[2:]}" if len(time) == 5 and time[:2].isdigit() else time
            body = {"summary": title,
                    "start": {"dateTime": f"{date}T{time}:00", "timeZone": tz},
                    "end": {"dateTime": f"{date}T{end_hour}:00", "timeZone": tz}}
            service.events().insert(calendarId=calendar_id, body=body).execute()
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Could not create event: {exc}"}
        event = {"title": title, "date": date, "time": time}
        world.setdefault("calendar", {}).setdefault(date, []).append({"title": title, "time": time})
        world.setdefault("events_created", []).append(event)
        return {"status": "created", **event}

    return create_event


class GoogleCalendarConnector:
    name = "calendar"
    title = "Google Calendar"
    tool_names = ["check_calendar", "create_event"]
    credentials = CREDENTIALS

    def schemas(self) -> list[dict]:
        return [week4_tools.SCHEMAS[n] for n in self.tool_names]

    def functions(self, mode: Mode, creds: dict, *, world: dict) -> dict[str, Callable]:
        return {"check_calendar": _mcp_check_calendar(creds),
                "create_event": _mcp_create_event(creds)}

    def readiness(self, mode: Mode, creds: dict) -> ConnectorStatus:
        if not str(creds.get("google_mcp_access_token", "")).strip():
            return ConnectorStatus(False, "Enter a Google Calendar MCP OAuth access token.")
        return ConnectorStatus(True, "Google Calendar MCP is ready.")

    def risky_tools(self, mode: Mode) -> set[str]:
        return {"create_event"}
