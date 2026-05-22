"""Thin client over the deployed Mosaic AI ResponsesAgent serving endpoint.

The endpoint accepts Responses-API payloads (`input=[{role, content}]`) and
returns a Responses-API object (`output=[{type:'message', content:[{type:'output_text', text}]}]`).

We non-stream the call (single round trip) and surface the assistant text plus
any tool-call records to the frontend as a small ordered sequence of events.
"""
from __future__ import annotations
import os
import json
from typing import AsyncIterator
import httpx

from databricks.sdk import WorkspaceClient


class AgentClient:
    def __init__(self, endpoint_name: str | None = None):
        self.endpoint = endpoint_name or os.environ.get("AGENT_ENDPOINT_NAME")
        if not self.endpoint:
            raise RuntimeError("AGENT_ENDPOINT_NAME env var not set")
        self.w = WorkspaceClient()
        self.host = self.w.config.host.rstrip("/")
        self.url = f"{self.host}/serving-endpoints/{self.endpoint}/invocations"

    def _auth_header(self) -> dict[str, str]:
        # WorkspaceClient handles whatever auth path (OAuth, PAT, SP) is configured.
        token = self.w.config.authenticate()
        # `authenticate()` returns dict-like { 'Authorization': 'Bearer ...' }
        return token if isinstance(token, dict) else {"Authorization": f"Bearer {token}"}

    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[dict]:
        """Yield response events. Each event is {'type': 'text'|'tool_call', 'content': ...}.

        Non-streaming under the hood; we POST once and break the response into
        ordered text + tool_call events so the frontend can render citation
        pills next to the assistant message.
        """
        payload = {"input": [{"role": m["role"], "content": m["content"]} for m in messages]}
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(self.url, headers=self._auth_header(), json=payload)
                resp.raise_for_status()
                body = resp.json()
        except httpx.HTTPStatusError as e:
            yield {"type": "text", "content": f"[agent endpoint returned {e.response.status_code}: {e.response.text[:300]}]"}
            return
        except Exception as e:
            yield {"type": "text", "content": f"[agent endpoint error: {type(e).__name__}: {e}]"}
            return

        for item in body.get("output", []) or []:
            itype = item.get("type")
            if itype == "function_call":
                yield {
                    "type": "tool_call",
                    "content": {
                        "name": item.get("name", ""),
                        "args": item.get("arguments", "") or "",
                    },
                }
            elif itype == "function_call_output":
                # Tool result: stash on the most recent tool_call by streaming it
                # as a synthetic event the frontend can correlate.
                yield {
                    "type": "tool_result",
                    "content": {
                        "call_id": item.get("call_id", ""),
                        "output": item.get("output", ""),
                    },
                }
            elif itype == "message":
                for part in item.get("content", []) or []:
                    if part.get("type") in ("output_text", "text"):
                        text = part.get("text", "")
                        if text:
                            yield {"type": "text", "content": text}
