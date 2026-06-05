"""FastAPI router for FSISIM custom endpoints.

Mounted by agent_server/start_server.py onto the AgentServer's FastAPI app.

Endpoints:
- GET  /api/health             — liveness
- GET  /api/manuals/{filename} — proxy UC Volume PDFs (migrated from app/backend/main.py)
- GET  /api/_diag              — SP volume listing (migrated)
- POST /api/chat               — added in Task 11
- GET  /api/threads            — added in Task 10
- GET  /api/threads/{id}       — added in Task 10
- POST /api/feedback           — added in Task 12
"""
from __future__ import annotations
import os
import urllib.parse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from agent_server.utils import get_user_email

import httpx

router = APIRouter()


CATALOG = os.environ.get("FSISIM_CATALOG", "jdub_demo")
SCHEMA = os.environ.get("FSISIM_SCHEMA", "fsisim_issue_ai_gold")
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/manuals"


def _allowed_filename(name: str) -> bool:
    return name.endswith(".pdf") and "/" not in name and ".." not in name


_W = None


def _get_w():
    global _W
    if _W is None:
        from databricks.sdk import WorkspaceClient
        _W = WorkspaceClient()
    return _W


@router.get("/api/health")
async def health():
    return {"ok": True}


@router.get("/api/manuals/{filename}")
async def manual(filename: str):
    """Return a manual PDF from the UC volume. text/plain on errors."""
    if not _allowed_filename(filename):
        return PlainTextResponse("Invalid filename", status_code=400)
    path = f"{VOLUME_PATH}/{filename}"
    w = _get_w()
    encoded_path = urllib.parse.quote(path)
    url = f"{w.config.host}/api/2.0/fs/files{encoded_path}"
    try:
        auth_headers = w.config.authenticate()
    except Exception as e:
        return PlainTextResponse(
            f"SDK auth failed: {type(e).__name__}: {e}", status_code=500
        )
    headers = {**auth_headers, "Accept": "application/octet-stream"}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url, headers=headers)
    except Exception as e:
        return PlainTextResponse(
            f"httpx fetch failed: {type(e).__name__}: {e}", status_code=502
        )
    ct = r.headers.get("content-type", "")
    if r.status_code != 200:
        body_preview = r.text[:400] if "text" in ct or "json" in ct else f"<{len(r.content)} bytes>"
        return PlainTextResponse(
            f"Files API {r.status_code} from {url}\n\n{body_preview}",
            status_code=r.status_code,
        )
    if not r.content.startswith(b"%PDF"):
        return PlainTextResponse(
            f"Files API returned non-PDF bytes (ct={ct}, len={len(r.content)}):\n\n{r.text[:400]}",
            status_code=502,
        )
    return Response(
        content=r.content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/api/_diag")
async def diag():
    out: dict = {"volume_path": VOLUME_PATH, "ok": False, "items": [], "error": None}
    try:
        w = _get_w()
        items = list(w.files.list_directory_contents(VOLUME_PATH))
        out["items"] = [
            {"name": it.name, "size": it.file_size, "is_dir": it.is_directory}
            for it in items
        ]
        out["ok"] = True
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    return JSONResponse(out)


def _fetch_user_threads(user_email: str) -> list[dict]:
    """Read the 10 most-recent threads for this user from agent_server.messages.

    AgentServer's `messages` table doesn't have an explicit `thread_id` column
    in every schema; the session id is stored in `messages.session_id`. We
    derive (thread_id, title, updated_at) by aggregating over session_id.
    """
    import psycopg
    from agent_server.memory import get_pg_connection_string

    sql = """
        SELECT
            m.session_id        AS thread_id,
            -- Title = first user turn's content, truncated; fallback to thread id
            COALESCE(
              substring(
                (SELECT content FROM agent_server.messages mm
                 WHERE mm.session_id = m.session_id AND mm.role = 'user'
                 ORDER BY mm.created_at ASC LIMIT 1)
                FROM 1 FOR 60),
              m.session_id
            ) AS title,
            MAX(m.created_at)    AS updated_at
        FROM agent_server.messages m
        WHERE m.user_email = %s
        GROUP BY m.session_id
        ORDER BY updated_at DESC
        LIMIT 10
    """
    with psycopg.connect(get_pg_connection_string(), autocommit=True) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(sql, (user_email,))
            rows = cur.fetchall()
    for r in rows:
        if r.get("updated_at") is not None:
            r["updated_at"] = r["updated_at"].isoformat()
    return rows


def _fetch_thread_owner(thread_id: str) -> str | None:
    import psycopg
    from agent_server.memory import get_pg_connection_string
    with psycopg.connect(get_pg_connection_string(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_email FROM agent_server.messages WHERE session_id = %s LIMIT 1",
                (thread_id,),
            )
            row = cur.fetchone()
    return row[0] if row else None


def _fetch_thread_messages(thread_id: str) -> list[dict]:
    import psycopg
    from agent_server.memory import get_pg_connection_string
    sql = """
        SELECT
            id, role, content, created_at,
            mlflow_trace_id
        FROM agent_server.messages
        WHERE session_id = %s
        ORDER BY created_at ASC
    """
    with psycopg.connect(get_pg_connection_string(), autocommit=True) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(sql, (thread_id,))
            rows = cur.fetchall()
    for r in rows:
        if r.get("created_at") is not None:
            r["created_at"] = r["created_at"].isoformat()
    return rows


@router.get("/api/threads")
async def list_threads(request: Request):
    email = get_user_email(request)
    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")
    return {"threads": _fetch_user_threads(email)}


@router.get("/api/threads/{thread_id}")
async def get_thread(thread_id: str, request: Request):
    email = get_user_email(request)
    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")
    owner = _fetch_thread_owner(thread_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    if owner != email:
        raise HTTPException(status_code=403, detail="Not your thread")
    return {"thread_id": thread_id, "messages": _fetch_thread_messages(thread_id)}
