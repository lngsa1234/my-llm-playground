"""Email connector: send real mail over SMTP, or write to the fake outbox.

Live mode uses the stdlib `smtplib` with an app password the user enters in the UI
(STARTTLS on 587, implicit TLS on 465). `send_email` is always approval-gated, in both
modes, matching Week 5's RISKY_TOOLS. `lookup_contact` stays simulated for now: it reads
the fake world's contact book, so the email flow still works end to end.

Live results are normalized to the fake tool's shape (`{"status": "sent", "to": ...}`),
and the sent message is also mirrored into `world["emails_sent"]` so the trace and the
Week 6 side-effect check see it.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Callable

from mini_muse import week4_tools
from mini_muse.connectors.base import ConnectorStatus, CredentialField, Mode

SMTP_TIMEOUT_S = 15

CREDENTIALS = [
    CredentialField("smtp_host", "SMTP host", placeholder="smtp.gmail.com",
                    help="Your provider's outgoing mail server."),
    CredentialField("smtp_port", "SMTP port", default="587",
                    help="587 for STARTTLS, 465 for implicit TLS."),
    CredentialField("smtp_username", "Username", placeholder="you@gmail.com"),
    CredentialField("smtp_app_password", "App password", secret=True,
                    help="An app-specific password, not your main account password."),
    CredentialField("smtp_from", "From address", placeholder="you@gmail.com",
                    help="Defaults to the username if blank."),
]


def _missing(creds: dict) -> list[str]:
    return [f.label for f in CREDENTIALS
            if f.key != "smtp_from" and not str(creds.get(f.key, "")).strip()]


def _connection(creds: dict):
    """Open and log in to the SMTP server. Caller must close it. May raise."""
    host = str(creds.get("smtp_host", "")).strip()
    port = int(str(creds.get("smtp_port", "587")).strip() or "587")
    username = str(creds.get("smtp_username", "")).strip()
    password = str(creds.get("smtp_app_password", "")).strip()
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=SMTP_TIMEOUT_S)
    else:
        server = smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT_S)
        server.starttls()
    server.login(username, password)
    return server


def _live_send_email(creds: dict) -> Callable:
    """Build a send_email bound to these credentials. The returned fn never raises."""

    def send_email(world, to, subject, body):
        sender = str(creds.get("smtp_from", "")).strip() or str(creds.get("smtp_username", "")).strip()
        message = EmailMessage()
        message["From"] = sender
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        try:
            server = _connection(creds)
            try:
                server.send_message(message)
            finally:
                server.quit()
        except Exception as exc:  # noqa: BLE001 - a live tool must never crash the agent loop
            return {"error": f"Could not send email: {exc}"}
        world.setdefault("emails_sent", []).append({"to": to, "subject": subject, "body": body})
        return {"status": "sent", "to": to}

    return send_email


def test_connection(creds: dict) -> ConnectorStatus:
    """Log in and out without sending, so the user can check credentials from the UI."""
    missing = _missing(creds)
    if missing:
        return ConnectorStatus(False, "Missing: " + ", ".join(missing))
    try:
        server = _connection(creds)
        server.quit()
    except Exception as exc:  # noqa: BLE001
        return ConnectorStatus(False, f"Login failed: {exc}")
    return ConnectorStatus(True, "Logged in successfully.")


class EmailConnector:
    name = "email"
    title = "Email (SMTP)"
    tool_names = ["lookup_contact", "send_email"]
    credentials = CREDENTIALS
    action_label = "Test connection"

    def run_action(self, creds: dict) -> ConnectorStatus:
        return test_connection(creds)

    def schemas(self) -> list[dict]:
        return [week4_tools.SCHEMAS[n] for n in self.tool_names]

    def functions(self, mode: Mode, creds: dict, *, world: dict) -> dict[str, Callable]:
        # lookup_contact stays simulated (reads the fake contact book) in both modes.
        fns: dict[str, Callable] = {"lookup_contact": week4_tools.lookup_contact}
        fns["send_email"] = _live_send_email(creds) if mode == "live" else week4_tools.send_email
        return fns

    def readiness(self, mode: Mode, creds: dict) -> ConnectorStatus:
        if mode != "live":
            return ConnectorStatus(True, "Simulated outbox (nothing really sent).")
        missing = _missing(creds)
        if missing:
            return ConnectorStatus(False, "Missing: " + ", ".join(missing))
        return ConnectorStatus(True, "Ready to send via SMTP (test the connection to be sure).")

    def risky_tools(self, mode: Mode) -> set[str]:
        return {"send_email"}  # approval-gated in both modes, like Week 5's RISKY_TOOLS
