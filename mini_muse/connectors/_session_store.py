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


def get_token(key: str) -> str | None:
    """Return the cached OAuth token for `key` (e.g. "calendar", "gmail"), or None."""
    return _TOKENS.get(key)


def set_token(key: str, token: str) -> None:
    """Cache an OAuth token for `key`, shared across sessions in this process."""
    _TOKENS[key] = token
