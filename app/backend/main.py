"""FastAPI backend for the FSISIM scaffold app."""
from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.agent_client import AgentClient

app = FastAPI(title="FSISIM Issue Resolution Agent (Scaffold)")
_client: AgentClient | None = None


def get_client() -> AgentClient:
    global _client
    if _client is None:
        _client = AgentClient()
    return _client


class ChatRequest(BaseModel):
    messages: list[dict]


@app.get("/api/health")
async def health():
    return {"ok": True}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    client = get_client()
    result = await client.chat(req.messages)
    return JSONResponse(result)


# Mount the built React frontend. When running locally without a built
# frontend, this mount is skipped so Vite's dev server can proxy /api here.
_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
