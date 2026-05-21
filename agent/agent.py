"""Mosaic AI Agent wired to two UC function tools.

Uses ResponsesAgent interface for streaming and AI Playground compatibility.
All heavy runtime imports (databricks_langchain, langgraph, databricks.agents,
mlflow) are deferred so this module can be imported in test environments that
only have the lightweight project deps installed. build_agent_config() always
works; build_agent() raises a clear RuntimeError when the agent stack is absent.
"""
from __future__ import annotations

from typing import Any

from config import Config
from agent.prompts import SYSTEM_PROMPT


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


def build_agent():
    """Construct the Mosaic AI Agent.

    Imports are deferred so this module can be imported (and
    build_agent_config() called) on machines that do not have the full
    Mosaic AI agent stack installed.
    """
    ac = build_agent_config()
    try:
        from databricks_langchain import ChatDatabricks, UCFunctionToolkit
        from langgraph.prebuilt import create_react_agent
        from databricks.agents import ResponsesAgent
    except ImportError as e:
        raise RuntimeError(
            f"Agent runtime deps missing ({e}). Install: "
            "'databricks-langchain langgraph databricks-agents'."
        ) from e

    llm = ChatDatabricks(endpoint=ac["llm_endpoint"])
    tk = UCFunctionToolkit(function_names=[fn["name"] for fn in ac["uc_functions"]])
    graph = create_react_agent(llm, tk.tools, state_modifier=ac["system_prompt"])
    return ResponsesAgent(graph)


# Module-level binding for MLflow logging.
# The actual agent is only built when the module is imported in an environment
# that has the runtime deps. In test environments without those deps, the lazy
# build_agent() raises a clear error when called, but build_agent_config()
# still works (which is all the tests need).
AGENT = None
try:
    AGENT = build_agent()
    try:
        import mlflow
        mlflow.models.set_model(AGENT)
    except ImportError:
        pass
except RuntimeError:
    pass
