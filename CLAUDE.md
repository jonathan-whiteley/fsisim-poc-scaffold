# Project Context

Catalog default: `jdub_demo` (configurable in `config.py`, override via `FSISIM_CATALOG`).

This is a scaffold build with synthetic data, not a customer-facing POC.
Fork and repoint the catalog when adopting it for production data.

Deploy model: Agents as Apps. The agent runs in-process inside the Databricks
App container (FastAPI + `mlflow.genai.agent_server.AgentServer`), not as a
separate Model Serving endpoint. Lakebase provides conversation memory via
LangGraph's `PostgresSaver`. Deploys use `databricks bundle deploy`.

Style:
- No em or en dashes. Use colons, semicolons, parens.
- Single config file (`config.py`) is the source of truth for catalog/schema/index names.
- Lakebase config lives in env vars (LAKEBASE_INSTANCE_NAME, LAKEBASE_DATABASE_NAME).
