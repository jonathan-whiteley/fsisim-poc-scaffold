"""Run mlflow.genai.evaluate against the deployed FSISIM agent.

Lifted from the agent-openai-agents-sdk template and adapted:
- Uses LangGraph autolog (template uses OpenAI autolog).
- Personas come from agent_server/personas.py (or a path passed in).
- Scorers tuned for technical Q&A (drops ConversationalSafety + UserFrustration).

Run via the DAB job (`scripts/run_eval.py`) or locally:
    uv run python -m agent_server.evaluate_agent
"""
from __future__ import annotations
import asyncio
import logging
from typing import Any


def _can_evaluate() -> bool:
    """Check if mlflow.genai is available in this environment."""
    try:
        import mlflow  # noqa: F401
        from mlflow.genai.agent_server import get_invoke_function  # noqa: F401
        from mlflow.genai.scorers import (  # noqa: F401
            Completeness,
            Fluency,
            RelevanceToQuery,
            Safety,
            ToolCallCorrectness,
        )
        from mlflow.genai.simulators import ConversationSimulator  # noqa: F401
        from mlflow.types.responses import ResponsesAgentRequest  # noqa: F401
    except Exception:
        return False
    return True


if _can_evaluate():
    import mlflow
    from mlflow.genai.agent_server import get_invoke_function
    from mlflow.genai.scorers import (
        Completeness,
        Fluency,
        RelevanceToQuery,
        Safety,
        ToolCallCorrectness,
    )
    from mlflow.genai.simulators import ConversationSimulator
    from mlflow.types.responses import ResponsesAgentRequest

    logging.getLogger("mlflow.utils.autologging_utils").setLevel(logging.ERROR)

    # Import the agent so its @invoke handler registers.
    from agent_server import agent  # noqa: F401

    def _load_personas(personas_module_path: str | None) -> list[dict]:
        """Load personas from a Python module path. Defaults to agent_server.personas."""
        if personas_module_path is None:
            from agent_server.personas import PERSONAS
            return PERSONAS
        import importlib
        mod = importlib.import_module(personas_module_path)
        return getattr(mod, "PERSONAS")

    def _build_predict_fn():
        """Return a sync `predict_fn(input, **kwargs) -> dict` over the @invoke handler."""
        invoke_fn = get_invoke_function()
        assert invoke_fn is not None, "No function registered with the @invoke decorator"

        if asyncio.iscoroutinefunction(invoke_fn):
            import nest_asyncio
            nest_asyncio.apply()

            def predict_fn(input: list[dict], **kwargs) -> dict[str, Any]:
                req = ResponsesAgentRequest(input=input)
                loop = asyncio.get_event_loop()
                response = loop.run_until_complete(invoke_fn(req))
                return response.model_dump()

            return predict_fn

        def predict_fn(input: list[dict], **kwargs) -> dict[str, Any]:
            req = ResponsesAgentRequest(input=input)
            response = invoke_fn(req)
            return response.model_dump()

        return predict_fn

    def evaluate(personas_module_path: str | None = None, max_turns: int = 5) -> None:
        """Run the eval and log results to the bound MLflow experiment."""
        personas = _load_personas(personas_module_path)
        simulator = ConversationSimulator(
            test_cases=personas,
            max_turns=max_turns,
            user_model="databricks:/databricks-claude-sonnet-4-5",
        )
        mlflow.genai.evaluate(
            data=simulator,
            predict_fn=_build_predict_fn(),
            scorers=[
                Completeness(),
                RelevanceToQuery(),
                ToolCallCorrectness(),
                Safety(),
                Fluency(),
            ],
        )

else:
    # Fallback stub when mlflow.genai is not available.
    def evaluate(personas_module_path: str | None = None, max_turns: int = 5) -> None:
        """Run the eval and log results to the bound MLflow experiment."""
        raise RuntimeError(
            "mlflow.genai is not available in this environment. "
            "Ensure mlflow[genai] is installed and genai submodule is present."
        )


if __name__ == "__main__":
    evaluate()
