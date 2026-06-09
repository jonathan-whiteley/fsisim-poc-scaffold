"""FSISIM agent: retrieval-then-synthesize, no UC tool execution.

Earlier this agent used LangGraph ReAct + UCFunctionToolkit to call SQL
table-functions. That path needs databricks-connect at runtime and the
version matrix doesn't reconcile in the Apps container. This file instead:

1. Reads the user's last turn from the request.
2. Queries the past-issues and manual-knowledge Vector Search indexes
   directly via the Databricks SDK.
3. Builds a single ChatDatabricks call with the retrieved context injected
   into the system prompt.
4. Returns the assistant text.

Conversation memory comes from the FastAPI relay (routes.py) which loads
prior turns from `agent_server.messages` before calling @invoke.
"""
from __future__ import annotations
import logging
from typing import Any, AsyncGenerator

import mlflow
from mlflow.genai.agent_server import invoke, stream
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
)

from config import Config
from agent_server.prompts import SYSTEM_PROMPT
from agent_server.utils import get_session_id

logger = logging.getLogger(__name__)

mlflow.langchain.autolog()
logging.getLogger("mlflow.utils.autologging_utils").setLevel(logging.ERROR)


def build_agent_config() -> dict[str, Any]:
    """Return the agent configuration dict derived from Config + env vars."""
    cfg = Config()
    return {
        "llm_endpoint": cfg.llm_endpoint,
        "uc_functions": [
            {"name": cfg.search_past_issues_fqn},
            {"name": cfg.search_technical_manuals_fqn},
        ],
        "system_prompt": SYSTEM_PROMPT,
    }


_W = None


def _get_w():
    """Lazily construct the WorkspaceClient; cache for reuse."""
    global _W
    if _W is None:
        from databricks.sdk import WorkspaceClient
        _W = WorkspaceClient()
    return _W


def _call_llm(messages: list[dict]) -> tuple[str, dict]:
    """Call the LLM serving endpoint directly via SDK.

    Returns (text, usage_dict). usage_dict has prompt_tokens / completion_tokens /
    total_tokens when the endpoint reports them; otherwise empty.
    """
    from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

    cfg = Config()
    w = _get_w()

    role_map = {
        "system": ChatMessageRole.SYSTEM,
        "user": ChatMessageRole.USER,
        "assistant": ChatMessageRole.ASSISTANT,
    }
    chat_messages = [
        ChatMessage(role=role_map.get(m["role"], ChatMessageRole.USER), content=m["content"])
        for m in messages
    ]

    resp = w.serving_endpoints.query(name=cfg.llm_endpoint, messages=chat_messages)
    text = ""
    if resp.choices and len(resp.choices) > 0:
        msg = resp.choices[0].message
        text = (msg.content if hasattr(msg, "content") else None) or ""

    usage: dict = {}
    u = getattr(resp, "usage", None)
    if u is not None:
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            val = getattr(u, key, None)
            if val is not None:
                usage[key] = int(val)
    return text, usage


def _retrieve_context(query: str) -> str:
    """Query both Vector Search indexes for the user's last turn.

    Returns a single markdown block to inject into the system prompt.
    Empty string if both queries fail (the agent still responds, just
    without retrieved context).
    """
    cfg = Config()
    w = _get_w()
    parts: list[str] = []

    try:
        ix = w.vector_search_indexes.query_index(
            index_name=cfg.issue_index_fqn,
            query_text=query,
            columns=["issue_id", "issue_type", "sim_name",
                     "note_type_description", "composite_text"],
            num_results=3,
            query_type="HYBRID",
        )
        rows = (ix.result.data_array if ix.result else []) or []
        if rows:
            issues_md = []
            for r in rows:
                issues_md.append(
                    f"- Issue #{r[0]} ({r[1]} on {r[2]}, note: {r[3]}):\n"
                    f"  {(r[4] or '')[:500]}"
                )
            parts.append("## Similar past issues\n" + "\n".join(issues_md))
    except Exception as e:
        logger.warning("issue VS query failed: %s: %s", type(e).__name__, e)

    try:
        ix = w.vector_search_indexes.query_index(
            index_name=cfg.manual_index_fqn,
            query_text=query,
            columns=["source_pdf", "page_first", "page_last", "chunk_to_retrieve"],
            num_results=3,
            query_type="HYBRID",
        )
        rows = (ix.result.data_array if ix.result else []) or []
        if rows:
            manuals_md = []
            for r in rows:
                src = r[0] or ""
                fn = src.split("/")[-1] if src else "manual"
                manuals_md.append(
                    f"- {fn} p.{r[1]}-{r[2]}:\n"
                    f"  {(r[3] or '')[:500]}"
                )
            parts.append("## Relevant manual excerpts\n" + "\n".join(manuals_md))
    except Exception as e:
        logger.warning("manual VS query failed: %s: %s", type(e).__name__, e)

    if not parts:
        return ""
    return "\n\n---\n# Retrieved context\n" + "\n\n".join(parts) + "\n---\n"


def _to_chat_dicts(items) -> list[dict]:
    """Convert ResponsesAgentRequest.input items to plain {role, content} dicts."""
    out = []
    for m in items:
        role = m.role if hasattr(m, "role") else m.get("role")
        content = m.content if hasattr(m, "content") else m.get("content")
        if role in ("user", "assistant", "system") and content:
            out.append({"role": role, "content": content})
    return out


def _last_user_text(items) -> str:
    """Return the content of the most recent user turn (empty if none)."""
    for m in reversed(items):
        role = m.role if hasattr(m, "role") else m.get("role")
        if role == "user":
            content = m.content if hasattr(m, "content") else m.get("content")
            return content or ""
    return ""


import re as _re

_TOOL_CALL_PATTERNS = [
    # XML-style tool tags like <search_past_issues>...</search_past_issues>
    _re.compile(r"<\s*search_(?:past_issues|technical_manuals)\b[^>]*>.*?</\s*search_[^>]+>",
                _re.DOTALL | _re.IGNORECASE),
    # Fence ```tool_code ... ```
    _re.compile(r"```tool_code\b.*?```", _re.DOTALL),
    # Bare opener (sometimes the model emits only the open tag)
    _re.compile(r"<\s*search_(?:past_issues|technical_manuals)\b[^>]*>\s*", _re.IGNORECASE),
]


def _strip_tool_call_leak(text: str) -> str:
    """Belt-and-suspenders: scrub any tool-call XML/fence the LLM leaks despite the prompt."""
    for pat in _TOOL_CALL_PATTERNS:
        text = pat.sub("", text)
    return text.strip()


@invoke()
def invoke_handler(request: ResponsesAgentRequest) -> ResponsesAgentResponse:
    """Retrieval-augmented single-turn synthesis.

    Wrapped in an mlflow.start_span so each turn emits a trace into the
    bound MLflow experiment. The trace_id is returned via custom_outputs
    so the FastAPI relay can persist it on the assistant message; that's
    what lets /api/feedback attach an Assessment to the right trace.
    """
    thread_id = get_session_id(request) or "default"
    last_user = _last_user_text(request.input)

    with mlflow.start_span(name="fsisim_chat_turn") as span:
        span.set_attributes({
            "thread_id": thread_id,
            "user_email": (request.custom_inputs or {}).get("user_email", ""),
            "input_chars": len(last_user),
        })
        try:
            mlflow.update_current_trace(metadata={"mlflow.trace.session": thread_id})
        except Exception:
            pass

        context_block = _retrieve_context(last_user) if last_user else ""
        messages = [{"role": "system", "content": SYSTEM_PROMPT + context_block}]
        messages.extend(_to_chat_dicts(request.input))

        # Record the inputs MLflow shows in the Request column.
        span.set_inputs({
            "thread_id": thread_id,
            "last_user_message": last_user,
            "retrieved_context_chars": len(context_block),
            "history_turns": len(messages) - 1,
        })

        raw_text, usage = _call_llm(messages)
        text = _strip_tool_call_leak(raw_text or "")

        # Record the outputs MLflow shows in the Response column.
        span.set_outputs({"assistant_text": text})

        # Token usage drives the Tokens column. MLflow looks for these specific
        # attribute names (OpenTelemetry GenAI semantic conventions).
        if usage:
            if "prompt_tokens" in usage:
                span.set_attribute("llm.token_count.prompt", usage["prompt_tokens"])
                span.set_attribute("mlflow.usage.prompt_tokens", usage["prompt_tokens"])
            if "completion_tokens" in usage:
                span.set_attribute("llm.token_count.completion", usage["completion_tokens"])
                span.set_attribute("mlflow.usage.completion_tokens", usage["completion_tokens"])
            if "total_tokens" in usage:
                span.set_attribute("llm.token_count.total", usage["total_tokens"])
                span.set_attribute("mlflow.usage.total_tokens", usage["total_tokens"])

        span.set_attribute("output_chars", len(text))

        trace_id = getattr(span, "trace_id", None) or getattr(span, "request_id", None)

    return ResponsesAgentResponse(
        output=[{"type": "message", "id": "msg-final",
                  "content": [{"type": "output_text", "text": text or "(no response)"}]}],
        custom_outputs={"trace_id": trace_id},
    )


@stream()
async def stream_handler(
    request: ResponsesAgentRequest,
) -> AsyncGenerator[ResponsesAgentStreamEvent, None]:
    """Streaming handler -- v1 React client doesn't consume the stream.

    For Agents-as-Apps with the SDK serving_endpoints.query() path, we don't
    have a clean per-chunk streaming API at hand. Yield a single item with
    the full response so the stream contract is honored.
    """
    thread_id = get_session_id(request) or "default"
    try:
        mlflow.update_current_trace(metadata={"mlflow.trace.session": thread_id})
    except Exception:
        pass

    last_user = _last_user_text(request.input)
    context_block = _retrieve_context(last_user) if last_user else ""

    messages = [{"role": "system", "content": SYSTEM_PROMPT + context_block}]
    messages.extend(_to_chat_dicts(request.input))

    text, _ = _call_llm(messages)

    yield ResponsesAgentStreamEvent(
        type="response.output_item.done",
        item={
            "type": "message",
            "id": "msg-final",
            "content": [{"type": "output_text", "text": str(text or "(no response)")}],
        },
    )
