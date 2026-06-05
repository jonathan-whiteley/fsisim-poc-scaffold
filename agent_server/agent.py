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


_LLM = None
_W = None


def _get_llm():
    """Lazily construct ChatDatabricks; cache for reuse."""
    global _LLM
    if _LLM is None:
        from databricks_langchain import ChatDatabricks
        _LLM = ChatDatabricks(endpoint=Config().llm_endpoint)
    return _LLM


def _get_w():
    """Lazily construct the WorkspaceClient; cache for reuse."""
    global _W
    if _W is None:
        from databricks.sdk import WorkspaceClient
        _W = WorkspaceClient()
    return _W


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


def _to_langchain(items):
    """Convert ResponsesAgentRequest.input items to LangChain message objects."""
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    out = []
    for m in items:
        role = m.role if hasattr(m, "role") else m.get("role")
        content = m.content if hasattr(m, "content") else m.get("content")
        if role == "user":
            out.append(HumanMessage(content=content))
        elif role == "assistant":
            out.append(AIMessage(content=content))
        elif role == "system":
            out.append(SystemMessage(content=content))
    return out


def _last_user_text(items) -> str:
    """Return the content of the most recent user turn (empty if none)."""
    for m in reversed(items):
        role = m.role if hasattr(m, "role") else m.get("role")
        if role == "user":
            content = m.content if hasattr(m, "content") else m.get("content")
            return content or ""
    return ""


@invoke()
def invoke_handler(request: ResponsesAgentRequest) -> ResponsesAgentResponse:
    """Retrieval-augmented single-turn synthesis."""
    from langchain_core.messages import SystemMessage

    thread_id = get_session_id(request) or "default"
    try:
        mlflow.update_current_trace(metadata={"mlflow.trace.session": thread_id})
    except Exception:
        pass  # no active trace in some contexts

    last_user = _last_user_text(request.input)
    context_block = _retrieve_context(last_user) if last_user else ""
    system_msg = SystemMessage(content=SYSTEM_PROMPT + context_block)

    history = _to_langchain(request.input)
    messages = [system_msg] + history

    llm = _get_llm()
    response = llm.invoke(messages)
    text = response.content if hasattr(response, "content") else str(response)
    if isinstance(text, list):
        text = "".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in text
        )

    return ResponsesAgentResponse(
        output=[{"type": "message", "id": "msg-final",
                  "content": [{"type": "output_text", "text": str(text)}]}]
    )


@stream()
async def stream_handler(
    request: ResponsesAgentRequest,
) -> AsyncGenerator[ResponsesAgentStreamEvent, None]:
    """Streaming handler -- v1 React client doesn't consume it; kept for parity."""
    from langchain_core.messages import SystemMessage

    thread_id = get_session_id(request) or "default"
    try:
        mlflow.update_current_trace(metadata={"mlflow.trace.session": thread_id})
    except Exception:
        pass

    last_user = _last_user_text(request.input)
    context_block = _retrieve_context(last_user) if last_user else ""
    system_msg = SystemMessage(content=SYSTEM_PROMPT + context_block)
    messages = [system_msg] + _to_langchain(request.input)

    llm = _get_llm()
    counter = 0
    for chunk in llm.stream(messages):
        text = chunk.content if hasattr(chunk, "content") else str(chunk)
        if text:
            counter += 1
            yield ResponsesAgentStreamEvent(
                type="response.output_item.done",
                item={
                    "type": "message",
                    "id": f"msg-{counter}",
                    "content": [{"type": "output_text", "text": str(text)}],
                },
            )
