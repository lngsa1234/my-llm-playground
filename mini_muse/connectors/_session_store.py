"""A tiny in-memory store for OAuth tokens that survives Streamlit's OAuth redirects.

Why this exists: hosted Google OAuth sends the browser to Google in a new tab and
redirects back to the app root, which Streamlit serves as a *fresh session* each time
(see the note in app.py). A token kept in `st.session_state` therefore lands in whichever
throwaway session finished that one OAuth dance, so connecting Calendar and then Gmail
leaves their tokens in two different sessions and neither connector sees the other as
connected.

This module keeps tokens in a plain module-level dict instead. A module is imported once
per Python process, so the dict is shared across every Streamlit session in that process
and the tokens persist across the redirects. Tokens stay in memory only and are never
written to disk.

Caveat: because the store is process-wide, it is not isolated between users on a shared
multi-user deployment. That is acceptable for this course, where each participant runs
their own instance; do not reuse it as-is for a public multi-tenant app.
"""

from __future__ import annotations

_TOKENS: dict[str, str] = {}
_ENABLED: set[str] = set()          # connectors the user turned on (survives the OAuth redirect)
_RETURN_PAGE: dict[str, str] = {}   # the page to land on after Google sends the browser back


def get_token(key: str) -> str | None:
    """Return the cached OAuth token for `key` (e.g. "calendar", "gmail"), or None."""
    return _TOKENS.get(key)


def set_token(key: str, token: str) -> None:
    """Cache an OAuth token for `key`, shared across sessions in this process."""
    _TOKENS[key] = token


def clear_token(key: str) -> None:
    """Forget the cached token for `key`, so the connector asks the user to sign in again."""
    _TOKENS.pop(key, None)


def is_auth_error(exc: Exception) -> bool:
    """True when Google rejected the token itself (expired, revoked or missing a scope).

    Because the store outlives sessions, a dead token would otherwise keep the connector
    showing "Connected" while every call fails, and "Connect" would never reach Google.
    """
    if type(exc).__name__ == "RefreshError":  # google.auth: refresh token expired or revoked
        return True
    status = getattr(getattr(exc, "resp", None), "status", None)  # googleapiclient HttpError
    text = str(exc).lower()
    if status == 401 or "invalid_grant" in text:
        return True
    return status == 403 and "insufficient" in text  # consent given without this scope


def enable(name: str) -> None:
    """Remember that the user turned connector `name` on, across the OAuth redirect."""
    _ENABLED.add(name)


def disable(name: str) -> None:
    _ENABLED.discard(name)


def is_enabled(name: str) -> bool:
    return name in _ENABLED


def set_return_page(page: str | None) -> None:
    """Remember where the user clicked Connect, so the redirect can bring them back there."""
    if page:
        _RETURN_PAGE["page"] = page


def pop_return_page() -> str | None:
    return _RETURN_PAGE.pop("page", None)
