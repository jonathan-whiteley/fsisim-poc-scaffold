"""FastAPI backend for the FSISIM scaffold app."""
from __future__ import annotations
import os
import urllib.parse
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import httpx

from backend.agent_client import AgentClient
from databricks.sdk import WorkspaceClient

app = FastAPI(title="FSISIM Issue Resolution Agent (Scaffold)")
_client: AgentClient | None = None
_w: WorkspaceClient | None = None

CATALOG = os.environ.get("FSISIM_CATALOG", "jdub_demo")
SCHEMA = os.environ.get("FSISIM_SCHEMA", "fsisim_issue_ai_gold")
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/manuals"
ALLOWED_FILE = lambda name: name.endswith(".pdf") and "/" not in name and ".." not in name


def get_client() -> AgentClient:
    global _client
    if _client is None:
        _client = AgentClient()
    return _client


def get_w() -> WorkspaceClient:
    global _w
    if _w is None:
        _w = WorkspaceClient()
    return _w


class ChatRequest(BaseModel):
    messages: list[dict]


@app.get("/api/health")
async def health():
    return {"ok": True}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    result = await get_client().chat(req.messages)
    return JSONResponse(result)


@app.get("/api/manuals/{filename}")
async def manual(filename: str):
    """Return a manual PDF from the UC volume.

    Bypasses databricks-sdk 0.30.0 `files.download().contents.read()` quirk
    (returns empty bytes for binary streams) by hitting the Files API
    directly with httpx, using the SDK's auth headers.

    On failure, returns text/plain (not PDF) so the browser shows the error
    instead of Chrome's generic "Failed to load PDF document." viewer error.
    """
    if not ALLOWED_FILE(filename):
        return PlainTextResponse("Invalid filename", status_code=400)
    path = f"{VOLUME_PATH}/{filename}"
    print(f"[manuals] GET filename={filename} path={path}", flush=True)
    w = get_w()
    encoded_path = urllib.parse.quote(path)  # safe='/' by default; matches SDK behavior
    url = f"{w.config.host}/api/2.0/fs/files{encoded_path}"
    try:
        auth_headers = w.config.authenticate()  # Dict[str, str], includes Authorization
    except Exception as e:
        msg = f"SDK auth failed: {type(e).__name__}: {e}"
        print(f"[manuals] {msg}", flush=True)
        return PlainTextResponse(msg, status_code=500)
    headers = {**auth_headers, "Accept": "application/octet-stream"}
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            r = await client.get(url, headers=headers)
    except Exception as e:
        msg = f"httpx fetch failed: {type(e).__name__}: {e}"
        print(f"[manuals] {msg}", flush=True)
        return PlainTextResponse(msg, status_code=502)
    ct = r.headers.get("content-type", "")
    print(f"[manuals] httpx status={r.status_code} bytes={len(r.content)} ct={ct}", flush=True)
    if r.status_code != 200:
        body_preview = r.text[:400] if "text" in ct or "json" in ct else f"<{len(r.content)} binary bytes>"
        msg = f"Files API {r.status_code} from {url}\n\n{body_preview}"
        return PlainTextResponse(msg, status_code=r.status_code)
    if not r.content.startswith(b"%PDF"):
        # Defensive: prevent Chrome's "Failed to load PDF" by surfacing the actual bytes.
        msg = f"Files API returned non-PDF bytes (ct={ct}, len={len(r.content)}):\n\n{r.text[:400]}"
        return PlainTextResponse(msg, status_code=502)
    return Response(
        content=r.content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@app.get("/api/_diag")
async def diag():
    """Diagnostic: confirm the app SP can see the volume and list contents."""
    out: dict = {"volume_path": VOLUME_PATH, "ok": False, "items": [], "error": None}
    try:
        w = get_w()
        items = list(w.files.list_directory_contents(VOLUME_PATH))
        out["items"] = [{"name": it.name, "size": it.file_size, "is_dir": it.is_directory} for it in items]
        out["ok"] = True
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    return JSONResponse(out)


# Mount the built React frontend. When running locally without a built
# frontend, this mount is skipped so Vite's dev server can proxy /api here.
_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
