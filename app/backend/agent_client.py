"""Thin client over the deployed Mosaic AI ResponsesAgent serving endpoint.

The endpoint accepts Responses-API payloads (`input=[{role,content}]`) and
returns `output=[{type:'message', content:[{type:'output_text', text}]}, ...]`.

Synchronous round-trip: we POST once and return a single JSON dict with the
flattened assistant text plus a fresh manual citation lookup for the user's
last turn (the agent already searches manuals internally, but predict() does
not surface those tool calls, so we re-issue a direct vector_search call to
populate citation pills).
"""
from __future__ import annotations
import os
import json
from typing import Any
import httpx

from databricks.sdk import WorkspaceClient


CATALOG = os.environ.get("FSISIM_CATALOG", "jdub_demo")
SCHEMA = os.environ.get("FSISIM_SCHEMA", "fsisim_issue_ai_gold")
MANUAL_INDEX = f"{CATALOG}.{SCHEMA}.manual_knowledge_index"
ISSUE_INDEX = f"{CATALOG}.{SCHEMA}.issue_history_index"


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

        Returns:
          {
            "text": str,
            "manual_citations": [
              {"source_pdf": str, "page_first": int, "page_last": int,
               "preview": str, "filename": str, "title": str}
            ],
            "issue_citations": [
              {"issue_id": int, "issue_type": str, "sim_name": str,
               "note_type": str, "preview": str}
            ],
            "error": str | None,
          }
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
                    return _err(f"Agent endpoint returned {resp.status_code}.\n\n{err}", f"http_{resp.status_code}")
                body = resp.json()
        except Exception as e:
            print(f"[chat] exception: {type(e).__name__}: {e}", flush=True)
            return _err(f"Agent endpoint error: {type(e).__name__}: {e}", "exception")

        texts: list[str] = []
        for item in body.get("output", []) or []:
            if item.get("type") == "message":
                for part in item.get("content", []) or []:
                    if part.get("type") in ("output_text", "text"):
                        t = part.get("text", "")
                        if t:
                            texts.append(t)

        combined = "\n\n".join(texts).strip()
        if not combined:
            print(f"[chat] no text extracted; raw body head: {json.dumps(body)[:500]}", flush=True)
            combined = (
                "The agent returned a response in an unexpected shape. Raw output:\n\n```\n"
                + json.dumps(body, indent=2)[:1500] + "\n```"
            )

        # Surface citations by re-querying the VS indexes for the user's last turn.
        last_user_msg = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        manual_citations = await self._query_manuals(last_user_msg) if last_user_msg else []
        issue_citations = await self._query_issues(last_user_msg) if last_user_msg else []

        print(
            f"[chat] text length={len(combined)}, manual_citations={len(manual_citations)}, "
            f"issue_citations={len(issue_citations)}",
            flush=True,
        )
        return {
            "text": combined,
            "manual_citations": manual_citations,
            "issue_citations": issue_citations,
            "error": None,
        }

    async def _query_manuals(self, query: str) -> list[dict]:
        try:
            ix = self.w.vector_search_indexes.query_index(
                index_name=MANUAL_INDEX,
                query_text=query,
                columns=["source_pdf", "page_first", "page_last", "chunk_to_retrieve"],
                num_results=3,
                query_type="HYBRID",
            )
            rows = (ix.result.data_array if ix.result else []) or []
            out = []
            for r in rows:
                source_pdf = r[0] or ""
                filename = source_pdf.split("/")[-1] if source_pdf else ""
                title = filename.replace(".pdf", "").replace("_", " ").title()
                out.append({
                    "source_pdf": source_pdf,
                    "filename": filename,
                    "title": title,
                    "page_first": int(r[1] or 0),
                    "page_last": int(r[2] or 0),
                    "preview": (r[3] or "")[:600],
                })
            return out
        except Exception as e:
            print(f"[chat] manual VS query failed: {type(e).__name__}: {e}", flush=True)
            return []

    async def _query_issues(self, query: str) -> list[dict]:
        try:
            ix = self.w.vector_search_indexes.query_index(
                index_name=ISSUE_INDEX,
                query_text=query,
                columns=["issue_id", "issue_type", "sim_name", "note_type_description", "composite_text"],
                num_results=3,
                query_type="HYBRID",
            )
            rows = (ix.result.data_array if ix.result else []) or []
            out = []
            for r in rows:
                out.append({
                    "issue_id": int(r[0] or 0),
                    "issue_type": r[1] or "",
                    "sim_name": r[2] or "",
                    "note_type": r[3] or "",
                    "preview": (r[4] or "")[:600],
                })
            return out
        except Exception as e:
            print(f"[chat] issue VS query failed: {type(e).__name__}: {e}", flush=True)
            return []


def _err(text: str, code: str) -> dict[str, Any]:
    return {"text": text, "manual_citations": [], "issue_citations": [], "error": code}
