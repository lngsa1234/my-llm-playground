"""The connector contract: one interface for a real service with a fake fallback.

A connector is like a Claude/ChatGPT connector: the user turns it on in the UI and
the agent gains real tools. Every connector offers the *same tools* in two backends:

    live        the real service (Open-Meteo, SMTP, Google Calendar)

The tool names and argument names a connector exposes MUST match
`mini_muse.week4_tools.SCHEMAS`, so the Week 6 golden dataset still grades the agent
no matter which backend is behind each tool.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Protocol, runtime_checkable

Mode = Literal["live"]


@dataclass(frozen=True)
class CredentialField:
    """One input the UI renders for a connector (e.g. an SMTP host or app password)."""

    key: str                 # session_state suffix and creds-dict key
    label: str               # what the UI shows
    secret: bool = False     # render as a password field, and never echo back
    placeholder: str = ""
    help: str = ""
    default: str = ""


@dataclass(frozen=True)
class ConnectorStatus:
    """Whether a connector is ready to use in the chosen mode, and a one-line reason."""

    ready: bool
    detail: str = ""
    authorization_url: str | None = None


@runtime_checkable
class Connector(Protocol):
    """A real service the agent can use.

    Implementations keep tool functions as `fn(world, **args) -> dict`. Live functions
    ignore `world` and MUST NOT raise: catch everything and return `{"error": ...}`,
    because the Week 7 Runtime only retries `TransientError` and lets anything else crash
    the loop. Live results are normalized to the fake-tool shapes so the model and the
    Week 6 grading stay consistent.
    """

    name: str                           # internal id, e.g. "weather"
    title: str                          # display name, e.g. "Weather"
    tool_names: list[str]               # the SCHEMAS keys this connector owns
    credentials: list[CredentialField]  # inputs the UI collects for live mode

    def schemas(self) -> list[dict]:
        """The tool schemas this connector exposes (a subset of week4_tools.SCHEMAS)."""
        ...

    def functions(self, mode: Mode, creds: dict, *, world: dict) -> dict[str, Callable]:
        """Map each tool name to the callable for this backend: `fn(world, **args) -> dict`."""
        ...

    def readiness(self, mode: Mode, creds: dict) -> ConnectorStatus:
        """Can the connector run with the supplied credentials?"""
        ...

    def risky_tools(self, mode: Mode) -> set[str]:
        """Tools that need the user's approval before running in this mode."""
        ...
