"""Mosaic AI Agent wired to two UC function tools.

This module is loaded by MLflow at deploy time and at predict time inside the
serving endpoint. The serialization contract is:
  - Top-level `AGENT` binding holds the constructed agent.
  - `mlflow.models.set_model(AGENT)` registers it with the MLflow pyfunc loader.

In the local test environment (no `databricks-langchain` / `langgraph`),
`build_agent()` returns None gracefully so `build_agent_config()` still works.
"""
from __future__ import annotations
from typing import Any, Generator

from config import Config

try:
    from agent.prompts import SYSTEM_PROMPT
except ModuleNotFoundError:
    from prompts import SYSTEM_PROMPT


def build_agent_config() -> dict[str, Any]:
    """Return the agent configuration dict derived from Config (and env vars)."""
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
        from mlflow.pyfunc import ResponsesAgent  # noqa: F401
    except Exception:
        return False
    return True


def build_agent():
    """Build the LangGraph ReAct agent wrapped in an MLflow ResponsesAgent.

    Returns None when runtime deps are missing (test env).
    """
    if not _can_build():
        return None

    from databricks_langchain import ChatDatabricks
    from databricks_langchain.uc_ai import UCFunctionToolkit
    from unitycatalog.ai.core.databricks import DatabricksFunctionClient
    from langgraph.prebuilt import create_react_agent
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    from mlflow.pyfunc import ResponsesAgent
    from mlflow.types.responses import ResponsesAgentRequest, ResponsesAgentResponse

    ac = build_agent_config()
    llm = ChatDatabricks(endpoint=ac["llm_endpoint"])
    # execution_mode='local' bypasses the spark session bootstrap so this
    # works in both the local conflict-y devloop and the deployed serving env.
    client = DatabricksFunctionClient(execution_mode="local")
    tk = UCFunctionToolkit(
        function_names=[fn["name"] for fn in ac["uc_functions"]],
        client=client,
    )
    graph = create_react_agent(llm, tk.tools, prompt=ac["system_prompt"])

    def _to_langchain(items):
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

    from mlflow.types.responses import ResponsesAgentStreamEvent

    class FsiSimAgent(ResponsesAgent):
        def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
            messages = _to_langchain(request.input)
            result = graph.invoke({"messages": messages})
            final = result["messages"][-1]
            text_item = self.create_text_output_item(text=str(final.content), id="msg-final")
            return ResponsesAgentResponse(output=[text_item])

        def predict_stream(self, request: ResponsesAgentRequest) -> Generator[ResponsesAgentStreamEvent, None, None]:
            messages = _to_langchain(request.input)
            counter = 0
            for event in graph.stream({"messages": messages}, stream_mode="updates"):
                for _, node_state in event.items():
                    for msg in node_state.get("messages", []) or []:
                        if getattr(msg, "content", None):
                            counter += 1
                            item = self.create_text_output_item(
                                text=str(msg.content), id=f"msg-{counter}",
                            )
                            yield ResponsesAgentStreamEvent(type="response.output_item.done", item=item)
                        for tc in getattr(msg, "tool_calls", None) or []:
                            counter += 1
                            call_id = tc.get("id") or f"tc-{counter}"
                            fn_item = self.create_function_call_item(
                                id=f"fc-{counter}",
                                call_id=call_id,
                                name=tc.get("name", ""),
                                arguments=str(tc.get("args", "")),
                            )
                            yield ResponsesAgentStreamEvent(type="response.output_item.done", item=fn_item)

    return FsiSimAgent()


if _can_build():
    AGENT = build_agent()
    import mlflow
    mlflow.models.set_model(AGENT)
else:
    AGENT = None
