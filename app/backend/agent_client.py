"""Thin client over the deployed Mosaic AI ResponsesAgent serving endpoint.

The endpoint accepts Responses-API payloads (`input=[{role,content}]`) and
returns `output=[{type:'message', content:[{type:'output_text', text}]}, ...]`.

Synchronous round-trip: we POST once and return a single JSON dict with the
flattened assistant text plus any tool calls/results the agent emitted.
"""
from __future__ import annotations
import os
import json
from typing import Any
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
        token = self.w.config.authenticate()
        return token if isinstance(token, dict) else {"Authorization": f"Bearer {token}"}

    async def chat(self, messages: list[dict]) -> dict[str, Any]:
        """POST messages to the agent endpoint and return a flattened response.

        Returns: {"text": str, "tool_calls": list[dict], "raw": dict | None, "error": str | None}
        """
        payload = {"input": [{"role": m["role"], "content": m["content"]} for m in messages]}
        print(f"[chat] POST {self.url}", flush=True)
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(self.url, headers=self._auth_header(), json=payload)
                print(f"[chat] status={resp.status_code}", flush=True)
                if resp.status_code >= 400:
                    err = resp.text[:500]
                    print(f"[chat] error: {err}", flush=True)
                    return {
                        "text": f"Agent endpoint returned {resp.status_code}.\n\n{err}",
                        "tool_calls": [],
                        "raw": None,
                        "error": f"http_{resp.status_code}",
                    }
                body = resp.json()
        except Exception as e:
            print(f"[chat] exception: {type(e).__name__}: {e}", flush=True)
            return {
                "text": f"Agent endpoint error: {type(e).__name__}: {e}",
                "tool_calls": [],
                "raw": None,
                "error": "exception",
            }

        texts: list[str] = []
        tool_calls: list[dict] = []
        for item in body.get("output", []) or []:
            itype = item.get("type")
            if itype == "function_call":
                tool_calls.append({
                    "name": item.get("name", ""),
                    "args": item.get("arguments", "") or "",
                })
            elif itype == "message":
                for part in item.get("content", []) or []:
                    if part.get("type") in ("output_text", "text"):
                        t = part.get("text", "")
                        if t:
                            texts.append(t)

        combined = "\n\n".join(texts).strip()
        if not combined:
            print(f"[chat] no text extracted; raw body head: {json.dumps(body)[:500]}", flush=True)
            combined = (
                "The agent returned a response in an unexpected shape. "
                "Raw output:\n\n```\n" + json.dumps(body, indent=2)[:1500] + "\n```"
            )

        print(f"[chat] returning text length={len(combined)}, tool_calls={len(tool_calls)}", flush=True)
        return {"text": combined, "tool_calls": tool_calls, "raw": None, "error": None}
