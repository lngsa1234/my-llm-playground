"""Email connector: send real mail with the Gmail API over OAuth.

This replaces the earlier SMTP/app-password backend. The user clicks "Connect Gmail",
authorizes the `gmail.send` scope in a new browser tab, and a session-only token is
cached (never written to disk). `send_email` builds a MIME message, base64url-encodes
it, and calls `users().messages().send()`. It is approval-gated, like Week 5's
RISKY_TOOLS.

The hosted web OAuth reuses the same deployment secrets and redirect URL as Google
Calendar (GOOGLE_OAUTH_CLIENT_ID/SECRET/REDIRECT_URI). Because both connectors come
back through the same redirect, the signed `state` is tagged with CONNECTOR_KEY so each
connector only consumes the callback meant for it.

Live results are normalized to the fake tool's shape (`{"status": "sent", "to": ...}`),
and the sent message is mirrored into `world["emails_sent"]` so the trace and the Week 6
side-effect check see it. The google-* libraries are imported lazily so this module loads
even when they are not installed; the tools then return a clear error instead of crashing.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from email.message import EmailMessage
from typing import Callable

from mini_muse import week4_tools
from mini_muse.connectors import _session_store
from mini_muse.connectors.base import ConnectorStatus, CredentialField, Mode

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CONNECTOR_KEY = "gmail"  # tags the state so a shared redirect URL routes to this connector.
STATE_TTL_SECONDS = 1800  # 30 min: the user navigates back and re-opens the connector by hand.


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
    payload = f"{CONNECTOR_KEY}.{secrets.token_urlsafe(24)}.{int(time.time()) + STATE_TTL_SECONDS}"
    signature = hmac.new(config["client_secret"].encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def _state_failure_reason(state: str | None, config: dict) -> str | None:
    """Explain why a callback state is invalid, or return None when it is valid.

    The reason is surfaced in the UI so an operator can tell an expired link apart
    from a signature mismatch (usually a rotated GOOGLE_OAUTH_CLIENT_SECRET).
    """
    if not state:
        return "missing state"
    try:
        key, nonce, expires, signature = state.split(".")
    except (TypeError, ValueError):
        return "malformed state"
    if key != CONNECTOR_KEY:
        return "wrong connector"
    payload = f"{key}.{nonce}.{expires}"
    expected = hmac.new(config["client_secret"].encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return "signature mismatch"
    try:
        if int(expires) < time.time():
            return "link expired"
    except ValueError:
        return "malformed expiry"
    return None


def _valid_callback_state(state: str | None, config: dict) -> bool:
    return _state_failure_reason(state, config) is None


def _session_token() -> str | None:
    # Shared across sessions: the OAuth redirect lands in a fresh session (see _session_store).
    return _session_store.get_token(CONNECTOR_KEY)


def _save_session_token(token: str) -> None:
    _session_store.set_token(CONNECTOR_KEY, token)


def _load_credentials():
    """Load the session-only OAuth token. Returns Credentials or raises."""
    from google.oauth2.credentials import Credentials

    token = _session_token()
    if not token:
        raise RuntimeError("Not connected yet. Click 'Connect Gmail' first.")
    return Credentials.from_authorized_user_info(json.loads(token), SCOPES)


def _service():
    from googleapiclient.discovery import build

    return build("gmail", "v1", credentials=_load_credentials(), cache_discovery=False)


def connect(creds: dict) -> ConnectorStatus:
    """Start the hosted OAuth flow and return an authorization URL for the user to open."""
    del creds  # Gmail uses deployment secrets, not per-user credentials.
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError:
        return ConnectorStatus(False, "Install google-auth-oauthlib to connect.")

    web_config = _web_oauth_config()
    if not web_config:
        return ConnectorStatus(False, "Gmail requires hosted OAuth secrets (GOOGLE_OAUTH_* in Streamlit).")
    try:
        flow = Flow.from_client_config(
            {"web": {**web_config, "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                      "token_uri": "https://oauth2.googleapis.com/token"}},
            scopes=SCOPES, redirect_uri=web_config["redirect_uri"],
            autogenerate_code_verifier=False,
        )
        authorization_url, _ = flow.authorization_url(
            access_type="offline", prompt="consent", state=_callback_state(web_config)
        )
    except Exception as exc:  # noqa: BLE001
        return ConnectorStatus(False, f"Could not start Gmail sign-in: {exc}")
    return ConnectorStatus(False, "Continue to Google to authorize sending email.", authorization_url)


def handle_callback() -> ConnectorStatus | None:
    """Exchange a hosted OAuth callback code for a session-only token, if it is ours."""
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
        if not state or state.split(".")[0] != CONNECTOR_KEY:
            return None  # this redirect belongs to a different connector; let it handle the code.
        reason = _state_failure_reason(state, web_config)
        if reason:
            return ConnectorStatus(False, f"Gmail sign-in could not be verified ({reason}). Please try again.")
        flow = Flow.from_client_config(
            {"web": {**web_config, "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                      "token_uri": "https://oauth2.googleapis.com/token"}},
            scopes=SCOPES, state=state, redirect_uri=web_config["redirect_uri"],
            autogenerate_code_verifier=False,
        )
        flow.fetch_token(code=code)
        _save_session_token(flow.credentials.to_json())
        st.query_params.clear()
    except Exception as exc:  # noqa: BLE001
        return ConnectorStatus(False, f"Gmail sign-in failed: {exc}")
    return ConnectorStatus(True, "Connected to Gmail for this session.")


def _live_send_email(creds: dict) -> Callable:
    """Build a send_email bound to the Gmail session token. The returned fn never raises."""
    del creds

    def send_email(world, to, subject, body):
        message = EmailMessage()
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        try:
            service = _service()
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            service.users().messages().send(userId="me", body={"raw": raw}).execute()
        except Exception as exc:  # noqa: BLE001 - a live tool must never crash the agent loop
            return {"error": f"Could not send email: {exc}"}
        world.setdefault("emails_sent", []).append({"to": to, "subject": subject, "body": body})
        return {"status": "sent", "to": to}

    return send_email


class GmailConnector:
    name = "email"
    title = "Email (Gmail)"
    tool_names = ["send_email"]
    credentials: list[CredentialField] = []  # hosted uses deployment secrets; no per-user inputs
    action_label = "Connect Gmail"

    def run_action(self, creds: dict) -> ConnectorStatus:
        return connect(creds)

    def schemas(self) -> list[dict]:
        return [week4_tools.SCHEMAS[n] for n in self.tool_names]

    def functions(self, mode: Mode, creds: dict, *, world: dict) -> dict[str, Callable]:
        return {"send_email": _live_send_email(creds)}

    def readiness(self, mode: Mode, creds: dict) -> ConnectorStatus:
        if not _web_oauth_config():
            return ConnectorStatus(False, "Gmail requires hosted OAuth secrets (GOOGLE_OAUTH_* in Streamlit).")
        if _session_token():
            return ConnectorStatus(True, "Connected to Gmail for this session.")
        return ConnectorStatus(False, "Not connected yet. Click 'Connect Gmail'.")

    def risky_tools(self, mode: Mode) -> set[str]:
        return {"send_email"}  # approval-gated in both modes, like Week 5's RISKY_TOOLS

    def handle_callback(self, creds: dict) -> ConnectorStatus | None:
        del creds
        return handle_callback()
