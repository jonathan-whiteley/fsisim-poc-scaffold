"""FSISIM AgentServer entrypoint.

Wires together:
- mlflow.genai.agent_server.AgentServer (provides /invocations + auto-tracing)
- agent_server.agent (registers @invoke / @stream)
- agent_server.routes (custom /api/* routes)
- app/frontend/dist/ (React SPA static files)
- setup_mlflow_git_based_version_tracking (git SHA -> MLflow version tag)
"""
from __future__ import annotations
from pathlib import Path

from dotenv import load_dotenv
from mlflow.genai.agent_server import AgentServer, setup_mlflow_git_based_version_tracking

# Load .env before importing agent so MLflow + Lakebase env are available.
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

# Import the agent so @invoke / @stream register with the server.
import agent_server.agent  # noqa: E402
from agent_server.routes import router as custom_router  # noqa: E402

agent_server = AgentServer("ResponsesAgent", enable_chat_proxy=False)
app = agent_server.app

# Mount custom FastAPI routes (threads, chat, feedback, manuals, health, diag).
app.include_router(custom_router)

# Serve the built React SPA (if present) at the root.
_frontend_dist = Path(__file__).parent.parent / "app" / "frontend" / "dist"
if _frontend_dist.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")

setup_mlflow_git_based_version_tracking()


def main() -> None:
    """Entrypoint invoked by `uv run start-app` (defined in pyproject [project.scripts])."""
    agent_server.run(app_import_string="agent_server.start_server:app")
