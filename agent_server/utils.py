"""Identity + session helpers for the FSISIM Agents-as-Apps server."""
from __future__ import annotations
from typing import Any


def get_user_email(request: Any) -> str | None:
    """Pull the authenticated user's email from the X-Forwarded-Email header.

    Databricks Apps inject this header on every request after SSO. Returns None
    when the header is absent (local dev without the App proxy).
    """
    headers = getattr(request, "headers", {}) or {}
    return headers.get("X-Forwarded-Email")


def get_session_id(request: Any) -> str | None:
    """Read the thread_id out of the ResponsesAgentRequest custom_inputs dict.

    Used by @invoke to tag the MLflow trace with the conversation thread.
    Returns None when the caller did not provide a thread_id.
    """
    custom = getattr(request, "custom_inputs", None) or {}
    return custom.get("thread_id")
