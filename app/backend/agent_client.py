"""Thin client over the deployed Mosaic AI agent serving endpoint."""
from __future__ import annotations
import os
import json
from typing import AsyncIterator, Iterable
from databricks.sdk import WorkspaceClient


class AgentClient:
    def __init__(self, endpoint_name: str | None = None):
        self.endpoint = endpoint_name or os.environ.get("AGENT_ENDPOINT_NAME")
        if not self.endpoint:
            raise RuntimeError("AGENT_ENDPOINT_NAME env var not set")
        self.w = WorkspaceClient()

    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[dict]:
        """Yield agent response chunks. Each chunk is {'type': 'text'|'tool_call', 'content': ...}.

        The Databricks serving endpoint for a Mosaic AI ResponsesAgent emits an
        OpenAI-compatible streaming format. We translate it into our simpler
        two-event shape so the frontend doesn't need to know the OpenAI schema.
        """
        # The SDK's streaming surface for serving endpoints is synchronous; iterate
        # the result and yield to async context.
        stream = self.w.serving_endpoints.query(
            name=self.endpoint,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            # Some chunks carry text deltas; others carry tool-call events.
            # Be defensive about shape variation across SDK versions.
            try:
                if hasattr(chunk, "choices") and chunk.choices:
                    delta = chunk.choices[0].delta
                    if getattr(delta, "content", None):
                        yield {"type": "text", "content": delta.content}
                    for tc in getattr(delta, "tool_calls", []) or []:
                        fn = getattr(tc, "function", None)
                        if fn:
                            yield {
                                "type": "tool_call",
                                "content": {
                                    "name": getattr(fn, "name", ""),
                                    "args": getattr(fn, "arguments", "") or "",
                                },
                            }
                # Tool results may arrive on the message object directly
                elif isinstance(chunk, dict):
                    if "content" in chunk and isinstance(chunk["content"], str):
                        yield {"type": "text", "content": chunk["content"]}
            except Exception as e:
                yield {"type": "text", "content": f"\n[client error: {type(e).__name__}: {e}]"}
