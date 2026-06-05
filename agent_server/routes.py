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

    Returns [] if the agent_server.messages table doesn't exist yet (it's
    populated by AgentServer's /invocations pipeline; this app calls @invoke
    directly so the table may stay empty in v1).
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
    try:
        with psycopg.connect(get_pg_connection_string(), autocommit=True) as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(sql, (user_email,))
                rows = cur.fetchall()
        for r in rows:
            if r.get("updated_at") is not None:
                r["updated_at"] = r["updated_at"].isoformat()
        return rows
    except psycopg.errors.UndefinedTable:
        return []


def _fetch_thread_owner(thread_id: str) -> str | None:
    import psycopg
    from agent_server.memory import get_pg_connection_string
    try:
        with psycopg.connect(get_pg_connection_string(), autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_email FROM agent_server.messages WHERE session_id = %s LIMIT 1",
                    (thread_id,),
                )
                row = cur.fetchone()
        return row[0] if row else None
    except psycopg.errors.UndefinedTable:
        return None


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
    try:
        with psycopg.connect(get_pg_connection_string(), autocommit=True) as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(sql, (thread_id,))
                rows = cur.fetchall()
        for r in rows:
            if r.get("created_at") is not None:
                r["created_at"] = r["created_at"].isoformat()
        return rows
    except psycopg.errors.UndefinedTable:
        return []


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


import uuid

from pydantic import BaseModel
from mlflow.types.responses import ResponsesAgentRequest


class ChatRequest(BaseModel):
    content: str
    thread_id: str | None = None


def _call_invoke(req: ResponsesAgentRequest):
    """Indirection so tests can mock the in-process @invoke call."""
    from mlflow.genai.agent_server import get_invoke_function
    fn = get_invoke_function()
    if fn is None:
        raise RuntimeError("@invoke handler not registered (agent_server.agent not imported)")
    return fn(req)


def _reissue_citations(user_message: str) -> dict:
    """Re-query VS indexes for manual + issue citations (existing logic).

    Lives in routes.py so the chat response can be assembled in one place.
    Returns {"manual_citations": [...], "issue_citations": [...]}.
    """
    w = _get_w()

    cat = os.environ.get("FSISIM_CATALOG", CATALOG)
    schm = os.environ.get("FSISIM_SCHEMA", SCHEMA)
    manual_idx = f"{cat}.{schm}.manual_knowledge_index"
    issue_idx = f"{cat}.{schm}.issue_history_index"

    manual_citations: list[dict] = []
    try:
        ix = w.vector_search_indexes.query_index(
            index_name=manual_idx, query_text=user_message,
            columns=["source_pdf", "page_first", "page_last", "chunk_to_retrieve"],
            num_results=3, query_type="HYBRID",
        )
        for r in (ix.result.data_array if ix.result else []) or []:
            source_pdf = r[0] or ""
            filename = source_pdf.split("/")[-1] if source_pdf else ""
            title = filename.replace(".pdf", "").replace("_", " ").title()
            manual_citations.append({
                "source_pdf": source_pdf, "filename": filename, "title": title,
                "page_first": int(r[1] or 0), "page_last": int(r[2] or 0),
                "preview": (r[3] or "")[:600],
            })
    except Exception:
        pass

    issue_citations: list[dict] = []
    try:
        ix = w.vector_search_indexes.query_index(
            index_name=issue_idx, query_text=user_message,
            columns=["issue_id", "issue_type", "sim_name",
                     "note_type_description", "composite_text"],
            num_results=3, query_type="HYBRID",
        )
        for r in (ix.result.data_array if ix.result else []) or []:
            issue_citations.append({
                "issue_id": int(r[0] or 0),
                "issue_type": r[1] or "",
                "sim_name": r[2] or "",
                "note_type": r[3] or "",
                "preview": (r[4] or "")[:600],
            })
    except Exception:
        pass

    return {"manual_citations": manual_citations, "issue_citations": issue_citations}


from typing import Literal


class FeedbackRequest(BaseModel):
    message_id: str
    rating: Literal["up", "down"]
    comment: str | None = None


def _lookup_trace_id(message_id: str) -> str | None:
    """Look up the MLflow trace_id for an assistant message.

    Returns None if the messages table doesn't exist yet (AgentServer
    populates it via /invocations; we currently call @invoke directly so
    nothing fills this table). Feedback still gets stored in Lakebase
    via _upsert_feedback; we just skip the MLflow assessment link.
    """
    import psycopg
    from agent_server.memory import get_pg_connection_string
    try:
        with psycopg.connect(get_pg_connection_string(), autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT mlflow_trace_id FROM agent_server.messages WHERE id = %s",
                    (message_id,),
                )
                row = cur.fetchone()
        return row[0] if row else None
    except psycopg.errors.UndefinedTable:
        return None


def _upsert_feedback(message_id: str, rating: str, comment: str | None,
                     user_email: str, trace_id: str | None) -> None:
    import psycopg
    from agent_server.memory import get_pg_connection_string
    sql = """
        INSERT INTO agent_server.message_feedback
          (message_id, rating, comment, user_email, mlflow_trace_id, updated_at)
        VALUES (%s, %s, %s, %s, %s, now())
        ON CONFLICT (message_id) DO UPDATE SET
          rating = EXCLUDED.rating,
          comment = EXCLUDED.comment,
          mlflow_trace_id = EXCLUDED.mlflow_trace_id,
          updated_at = now()
    """
    with psycopg.connect(get_pg_connection_string(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (message_id, rating, comment, user_email, trace_id))


def _log_mlflow_feedback(trace_id: str, rating: str, comment: str | None) -> None:
    import mlflow
    # mlflow.log_feedback writes an Assessment to the trace.
    mlflow.log_feedback(
        trace_id=trace_id,
        name="thumbs",
        value=rating,
        rationale=comment,
    )


@router.post("/api/feedback")
async def feedback(req: FeedbackRequest, request: Request):
    email = get_user_email(request)
    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")

    trace_id = _lookup_trace_id(req.message_id)
    _upsert_feedback(req.message_id, req.rating, req.comment, email, trace_id)

    if trace_id:
        try:
            _log_mlflow_feedback(trace_id, req.rating, req.comment)
        except Exception:
            # Lakebase mirror is enough for app-side render; log + continue.
            import logging
            logging.getLogger(__name__).warning(
                "mlflow.log_feedback failed for message_id=%s", req.message_id,
                exc_info=True,
            )

    return {"ok": True, "message_id": req.message_id, "rating": req.rating}


@router.post("/api/chat")
async def chat(req: ChatRequest, request: Request):
    email = get_user_email(request)
    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")

    thread_id = req.thread_id or str(uuid.uuid4())

    agent_req = ResponsesAgentRequest(
        input=[{"role": "user", "content": req.content}],
        custom_inputs={"thread_id": thread_id, "user_email": email},
    )

    response = _call_invoke(agent_req)

    text = ""
    assistant_message_id = ""
    for item in response.output:
        if isinstance(item, dict):
            content = item.get("content", [])
            assistant_message_id = item.get("id", assistant_message_id)
        else:
            content = getattr(item, "content", [])
            assistant_message_id = getattr(item, "id", assistant_message_id)
        for part in content:
            ptype = part.get("type") if isinstance(part, dict) else getattr(part, "type", None)
            ptext = part.get("text") if isinstance(part, dict) else getattr(part, "text", None)
            if ptype in ("output_text", "text") and ptext:
                text += ptext

    citations = _reissue_citations(req.content)

    return {
        "thread_id": thread_id,
        "text": text or "(no response)",
        "manual_citations": citations["manual_citations"],
        "issue_citations": citations["issue_citations"],
        "assistant_message_id": assistant_message_id,
    }
