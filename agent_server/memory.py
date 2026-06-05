"""Lakebase Postgres helpers for the FSISIM agent.

Mints SP-scoped OAuth tokens via the Databricks SDK and exposes:
- `get_pg_connection_string()` — libpq URI for ad-hoc psycopg connections
- `get_checkpointer()` — LangGraph PostgresSaver singleton with token refresh

The OAuth token lasts ~60 minutes. We cache for 50 minutes then re-mint.
"""
from __future__ import annotations
import os
import threading
import time
import urllib.parse
from typing import Any

from databricks.sdk import WorkspaceClient

_TOKEN_CACHE: dict[str, Any] = {"token": None, "expires_at": 0.0, "host": None, "user": None}
_TOKEN_LOCK = threading.Lock()
_TOKEN_TTL_SECONDS = 50 * 60  # refresh 10 min before the 60-min expiry


def _mint_credentials() -> dict[str, str]:
    """Refresh the cached Lakebase credentials. Caller holds _TOKEN_LOCK."""
    instance_name = os.environ.get("LAKEBASE_INSTANCE_NAME")
    if not instance_name:
        raise RuntimeError("LAKEBASE_INSTANCE_NAME env var is required")

    w = WorkspaceClient()
    instance = w.database.get_database_instance(name=instance_name)
    cred = w.database.generate_database_credential(
        request_id=f"fsisim-{int(time.time())}",
        instance_names=[instance_name],
    )
    me = w.current_user.me()

    return {
        "host": instance.read_write_dns,
        "user": me.user_name,
        "token": cred.token,
    }


def _get_credentials() -> dict[str, str]:
    """Return cached or freshly-minted credentials (thread-safe)."""
    now = time.time()
    if _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["expires_at"]:
        return {
            "host": _TOKEN_CACHE["host"],
            "user": _TOKEN_CACHE["user"],
            "token": _TOKEN_CACHE["token"],
        }
    with _TOKEN_LOCK:
        # Re-check after acquiring the lock to avoid double-mint.
        if _TOKEN_CACHE["token"] and time.time() < _TOKEN_CACHE["expires_at"]:
            return {
                "host": _TOKEN_CACHE["host"],
                "user": _TOKEN_CACHE["user"],
                "token": _TOKEN_CACHE["token"],
            }
        fresh = _mint_credentials()
        _TOKEN_CACHE.update(fresh)
        _TOKEN_CACHE["expires_at"] = time.time() + _TOKEN_TTL_SECONDS
        return fresh


def get_pg_connection_string() -> str:
    """Return a libpq-compatible postgresql:// URI for the Lakebase instance."""
    db_name = os.environ.get("LAKEBASE_DATABASE_NAME", "fsisim_chat")
    creds = _get_credentials()
    user = urllib.parse.quote(creds["user"], safe="")
    token = urllib.parse.quote(creds["token"], safe="")
    host = creds["host"]
    return f"postgresql://{user}:{token}@{host}:5432/{db_name}?sslmode=require"


_CHECKPOINTER: Any = None


def get_checkpointer():
    """Return a LangGraph PostgresSaver bound to Lakebase.

    Lazily constructs and caches the saver. The underlying connection pool
    re-resolves the OAuth token on each new connection, so token expiry is
    handled transparently as long as the pool recycles connections.
    """
    global _CHECKPOINTER
    if _CHECKPOINTER is not None:
        return _CHECKPOINTER

    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg_pool import ConnectionPool

    def _connect():
        return get_pg_connection_string()

    pool = ConnectionPool(
        conninfo=get_pg_connection_string(),
        min_size=1,
        max_size=4,
        kwargs={"autocommit": True, "prepare_threshold": 0},
        configure=lambda conn: None,
        reconnect_failed=lambda pool: None,
    )
    saver = PostgresSaver(pool)
    saver.setup()  # idempotent; creates checkpoint tables on first run
    _CHECKPOINTER = saver
    return _CHECKPOINTER
