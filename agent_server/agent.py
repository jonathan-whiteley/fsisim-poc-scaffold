"""FSISIM agent: LangGraph ReAct + Lakebase memory, exposed via @invoke / @stream.

Module-level side effects on import (intentional; matches the template):
- mlflow.langchain.autolog() so every LangGraph call emits an MLflow trace
- @invoke / @stream decorators register the handlers with the AgentServer

The LangGraph graph itself is rebuilt per request to attach the right
checkpoint thread; the underlying ChatDatabricks + UC toolkit are cached.
"""
from __future__ import annotations
import logging
from typing import Any, AsyncGenerator

from config import Config
from agent_server.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


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


def _can_build() -> bool:
    try:
        import databricks_langchain  # noqa: F401
        import langgraph  # noqa: F401
        from mlflow.genai.agent_server import invoke  # noqa: F401
    except Exception:
        return False
    return True


# Module-level cache: ChatDatabricks + tools are heavy to construct.
_LLM = None
_TOOLS = None


def _build_llm_and_tools():
    """Build the LLM client and UC function tools once; cache for reuse."""
    global _LLM, _TOOLS
    if _LLM is not None and _TOOLS is not None:
        return _LLM, _TOOLS

    from databricks_langchain import ChatDatabricks
    from databricks_langchain.uc_ai import UCFunctionToolkit
    from unitycatalog.ai.core.databricks import DatabricksFunctionClient

    ac = build_agent_config()
    _LLM = ChatDatabricks(endpoint=ac["llm_endpoint"])
    try:
        client = DatabricksFunctionClient(execution_mode="serverless")
    except Exception:
        client = DatabricksFunctionClient(execution_mode="local")
    tk = UCFunctionToolkit(
        function_names=[fn["name"] for fn in ac["uc_functions"]],
        client=client,
    )
    _TOOLS = tk.tools
    return _LLM, _TOOLS


def _build_graph_for_thread(thread_id: str):
    """Construct a LangGraph ReAct agent attached to the Lakebase checkpoint
    for `thread_id`. The graph is cheap to build; the LLM + tools are cached.
    """
    from agent_server.memory import get_checkpointer
    from langgraph.prebuilt import create_react_agent

    ac = build_agent_config()
    llm, tools = _build_llm_and_tools()
    saver = get_checkpointer()
    return create_react_agent(llm, tools, prompt=ac["system_prompt"], checkpointer=saver)


if _can_build():
    import mlflow
    from mlflow.genai.agent_server import invoke, stream
    from mlflow.types.responses import (
        ResponsesAgentRequest,
        ResponsesAgentResponse,
        ResponsesAgentStreamEvent,
    )

    mlflow.langchain.autolog()
    logging.getLogger("mlflow.utils.autologging_utils").setLevel(logging.ERROR)

    from agent_server.utils import get_session_id

    def _to_langchain(items):
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

    @invoke()
    def invoke_handler(request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        """Synchronous chat handler.

        Reads thread_id from custom_inputs, tags the MLflow trace with it,
        runs the LangGraph ReAct agent, and returns the final assistant turn.
        LangGraph's PostgresSaver persists the conversation state.
        """
        thread_id = get_session_id(request) or "default"
        mlflow.update_current_trace(
            metadata={"mlflow.trace.session": thread_id},
        )
        graph = _build_graph_for_thread(thread_id)
        messages = _to_langchain(request.input)
        result = graph.invoke(
            {"messages": messages},
            config={"configurable": {"thread_id": thread_id}},
        )
        final = result["messages"][-1]
        from mlflow.types.responses import ResponsesAgentResponse  # local import for clarity
        return ResponsesAgentResponse(
            output=[{"type": "message", "id": "msg-final",
                      "content": [{"type": "output_text", "text": str(final.content)}]}]
        )

    @stream()
    async def stream_handler(
        request: ResponsesAgentRequest,
    ) -> AsyncGenerator[ResponsesAgentStreamEvent, None]:
        """Streaming handler -- registered for future use by the React UI.

        v1 React client doesn't consume the stream; we expose it so future
        work can switch without redeploying the agent.
        """
        thread_id = get_session_id(request) or "default"
        mlflow.update_current_trace(
            metadata={"mlflow.trace.session": thread_id},
        )
        graph = _build_graph_for_thread(thread_id)
        messages = _to_langchain(request.input)
        counter = 0
        for event in graph.stream(
            {"messages": messages},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="updates",
        ):
            for _, node_state in event.items():
                for msg in node_state.get("messages", []) or []:
                    if getattr(msg, "content", None):
                        counter += 1
                        yield ResponsesAgentStreamEvent(
                            type="response.output_item.done",
                            item={
                                "type": "message",
                                "id": f"msg-{counter}",
                                "content": [{"type": "output_text", "text": str(msg.content)}],
                            },
                        )
