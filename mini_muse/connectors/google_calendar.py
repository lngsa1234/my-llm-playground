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

import json
import hashlib
import hmac
import secrets
import time
from pathlib import Path
from typing import Callable

from mini_muse import week4_tools
from mini_muse.connectors.base import ConnectorStatus, CredentialField, Mode

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
PROJECT_ROOT = Path(__file__).resolve().parents[2]

CREDENTIALS = [
    CredentialField("google_credentials_path", "OAuth client file", default="google_credentials.json",
                    help="Local development only. Streamlit Cloud uses deployment secrets instead."),
    CredentialField("google_token_path", "Token cache file", default="google_token.json",
                    help="Where the connector saves your consent token. Created on Connect."),
    CredentialField("google_calendar_id", "Calendar ID", default="primary",
                    help="'primary' is your main calendar."),
]


def _project_path(value: str) -> str:
    """Resolve user paths consistently when Streamlit starts from another directory."""
    path = Path(value).expanduser()
    return str(path if path.is_absolute() else PROJECT_ROOT / path)


def _token_path(creds: dict) -> str:
    return _project_path(str(creds.get("google_token_path", "") or "google_token.json").strip())


def _credentials_path(creds: dict) -> str:
    return _project_path(str(creds.get("google_credentials_path", "") or "google_credentials.json").strip())


def _calendar_id(creds: dict) -> str:
    return str(creds.get("google_calendar_id", "") or "primary").strip()


def _web_oauth_config() -> dict | None:
    """Read hosted OAuth settings without ever placing them in the UI or repository."""
    try:
        import streamlit as st

        client_id = st.secrets.get("GOOGLE_OAUTH_CLIENT_ID")
        client_secret = st.secrets.get("GOOGLE_OAUTH_CLIENT_SECRET")
        redirect_uri = st.secrets.get("GOOGLE_OAUTH_REDIRECT_URI")
    except Exception:  # Streamlit is optional for command-line use and tests.
        return None
    if not all((client_id, client_secret, redirect_uri)):
        return None
    return {"client_id": client_id, "client_secret": client_secret, "redirect_uri": redirect_uri}


def _callback_state(config: dict) -> str:
    """Create a short-lived, signed state that survives a Streamlit OAuth redirect."""
    payload = f"{secrets.token_urlsafe(24)}.{int(time.time()) + 600}"
    signature = hmac.new(config["client_secret"].encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def _valid_callback_state(state: str | None, config: dict) -> bool:
    if not state:
        return False
    try:
        nonce, expires, signature = state.rsplit(".", 2)
        payload = f"{nonce}.{expires}"
        expected = hmac.new(config["client_secret"].encode(), payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected) and int(expires) >= time.time()
    except (TypeError, ValueError):
        return False


def _session_token() -> str | None:
    try:
        import streamlit as st

        return st.session_state.get("google_calendar_token")
    except Exception:
        return None


def _save_session_token(token: str) -> None:
    import streamlit as st

    st.session_state["google_calendar_token"] = token


def _load_credentials(creds: dict):
    """Load (and refresh) the cached OAuth token. Returns Credentials or raises."""
    import os

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    session_token = _session_token()
    if session_token:
        return Credentials.from_authorized_user_info(json.loads(session_token), SCOPES)

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
    """Start OAuth, using Streamlit Secrets for hosted deployments when configured."""
    import os

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        return ConnectorStatus(False, "Install google-auth-oauthlib to connect.")

    web_config = _web_oauth_config()
    if web_config:
        try:
            import streamlit as st
            from google_auth_oauthlib.flow import Flow

            flow = Flow.from_client_config(
                {"web": {**web_config, "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                          "token_uri": "https://oauth2.googleapis.com/token"}},
                scopes=SCOPES, redirect_uri=web_config["redirect_uri"],
            )
            authorization_url, _ = flow.authorization_url(
                access_type="offline", prompt="consent", state=_callback_state(web_config)
            )
        except Exception as exc:  # noqa: BLE001
            return ConnectorStatus(False, f"Could not start Google sign-in: {exc}")
        return ConnectorStatus(False, "Continue to Google to authorize calendar access.", authorization_url)

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


def handle_callback() -> ConnectorStatus | None:
    """Exchange a hosted OAuth callback code for a session-only token, if present."""
    web_config = _web_oauth_config()
    if not web_config:
        return None
    try:
        import streamlit as st
        from google_auth_oauthlib.flow import Flow

        code = st.query_params.get("code")
        if not code:
            return None
        state = st.query_params.get("state")
        if not _valid_callback_state(state, web_config):
            return ConnectorStatus(False, "Google sign-in could not be verified. Please try again.")
        flow = Flow.from_client_config(
            {"web": {**web_config, "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                      "token_uri": "https://oauth2.googleapis.com/token"}},
            scopes=SCOPES, state=state, redirect_uri=web_config["redirect_uri"],
        )
        flow.fetch_token(code=code)
        _save_session_token(flow.credentials.to_json())
        st.query_params.clear()
    except Exception as exc:  # noqa: BLE001
        return ConnectorStatus(False, f"Google sign-in failed: {exc}")
    return ConnectorStatus(True, "Connected to Google Calendar for this session.")


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
    action_label = "Connect Google Calendar"

    def run_action(self, creds: dict) -> ConnectorStatus:
        return connect(creds)

    def schemas(self) -> list[dict]:
        return [week4_tools.SCHEMAS[n] for n in self.tool_names]

    def functions(self, mode: Mode, creds: dict, *, world: dict) -> dict[str, Callable]:
        return {"check_calendar": _live_check_calendar(creds),
                "create_event": _live_create_event(creds)}

    def readiness(self, mode: Mode, creds: dict) -> ConnectorStatus:
        import os

        if _web_oauth_config():
            if _session_token():
                return ConnectorStatus(True, "Connected to Google Calendar for this session.")
            return ConnectorStatus(False, "Not connected yet. Click 'Connect Google Calendar'.")
        if not os.path.exists(_credentials_path(creds)):
            return ConnectorStatus(False, f"OAuth client file not found: {_credentials_path(creds)}")
        if not os.path.exists(_token_path(creds)):
            return ConnectorStatus(False, "Not connected yet. Click 'Connect Google Calendar'.")
        return ConnectorStatus(True, "Connected to Google Calendar.")

    def risky_tools(self, mode: Mode) -> set[str]:
        return {"create_event"}

    def handle_callback(self, creds: dict) -> ConnectorStatus | None:
        del creds
        return handle_callback()
