"""User-enablable, real-service connectors for Mini Muse.

`CONNECTORS` is the list the UI renders; `build_registry` turns the user's choices into
a `ToolRegistry` the agent can take in place of the fake tools. Pass no registry and the
agent is unchanged (the default, and what tests and Week 6 use).
"""

from __future__ import annotations

from mini_muse.connectors.base import (
    Connector,
    ConnectorStatus,
    CredentialField,
    Mode,
)
from mini_muse.connectors.email_smtp import EmailConnector
from mini_muse.connectors.google_calendar import GoogleCalendarConnector
from mini_muse.connectors.registry import ToolRegistry, build_registry
from mini_muse.connectors.weather import WeatherConnector

# Order matches the course's tool sequence: weather, calendar, then email.
CONNECTORS: list[Connector] = [
    WeatherConnector(),
    GoogleCalendarConnector(),
    EmailConnector(),
]

__all__ = [
    "CONNECTORS",
    "Connector",
    "ConnectorStatus",
    "CredentialField",
    "Mode",
    "ToolRegistry",
    "build_registry",
]
