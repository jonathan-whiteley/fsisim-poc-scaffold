# fsisim-poc-scaffold

A reference implementation of an issue resolution agent for flight simulator
maintenance. Synthetic data, two Mosaic AI Vector Search indexes, a Mosaic
AI Agent with two tools, and a React + FastAPI app deployed as a Databricks
App (Agents as Apps pattern).

## What this is (and isn't)

This is a scaffold with synthetic data. The point is to de-risk the
architecture end-to-end before real data lands, and to provide a working
Databricks pattern that can be forked and repointed at a production catalog.

It does NOT:
- Use real data
- Cover a full manual corpus (ships with 6 fabricated PDFs)
- Generate step-by-step troubleshooting outputs (the synthetic data only
  captures past resolutions)

## Architecture

```
User
  -> chat
React App  --HTTPS-->  FastAPI (Databricks App, single container)
                            |
                            |   /api/chat -> http://localhost:8000/invocations
                            v
                 mlflow.genai.agent_server.AgentServer
                            |
                            v
                 Mosaic AI Agent (ResponsesAgent)
                 |
                 +-- Tool: search_technical_manuals --> manual_knowledge_index (VS)
                 +-- Tool: search_past_issues       --> issue_history_index    (VS)
                            |
                            v
                 Sonnet 4.5 (Foundation Model API) synthesizes answer with citations
                            |
                            v
                 Lakebase Postgres (conversation memory, message feedback)
```

The agent runs in-process inside the Databricks App container; there is no
separate Model Serving endpoint.

## DAB variables

All deploy-time knobs live in `databricks.yml`. Defaults are tuned for the
DEFAULT (`jdub_demo`) workspace; overrides go on the `databricks bundle`
CLI via `--var` (or edit `databricks.yml` directly):

| Variable | Default | Purpose |
|---|---|---|
| `catalog` | `jdub_demo` | UC catalog for Delta tables + volumes + VS indexes |
| `schema` | `fsisim_issue_ai_gold` | UC schema within that catalog |
| `lakebase_instance_name` | `flightsafety-lakebase` | Lakebase Postgres instance name (provision once, outside DAB) |
| `lakebase_database_name` | `databricks_postgres` | Database inside that Lakebase instance |
| `eval_personas_file` | `agent_server.personas` | Python module path holding the PERSONAS list for the weekly eval job |
| `agent_app_name` | `fsisim-scaffold-dab` | Databricks App resource name (becomes part of the deployed URL) |

Override examples:

```bash
databricks bundle deploy --target dev \
  --var catalog=poc_data \
  --var lakebase_instance_name=fsisim-poc \
  --var agent_app_name=fsisim-scaffold
```

## Fresh-workspace deploy

Follow these steps top-to-bottom in a new workspace. Time estimates are
flagged on long-running steps so you know whether to walk away or watch.

### 0. Bootstrap the repo

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
pytest -q
```

### 1. Authenticate

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com
```

### 2. One-time provisioning (outside DAB)

The bundle assumes these already exist. None of them are created by
`databricks bundle deploy`:

**Catalog, schema, volume** (idempotent):

```bash
FSISIM_CATALOG=<catalog> FSISIM_SCHEMA=<schema> python -m infra.setup_catalog
```

**Vector Search endpoint + delta-sync indexes**:

```bash
# Requires the Delta tables to exist; you'll re-run this AFTER step 3.
FSISIM_CATALOG=<catalog> FSISIM_SCHEMA=<schema> python -m infra.setup_vector_search
```

**Lakebase Postgres instance** (provision via workspace UI or FEVM CLI).
Record the instance name; it becomes `lakebase_instance_name`. Allow
**~10-15 min** if your workspace has Lakebase quota; longer if quota
needs to be requested first. The DAB does not create this for you.

### 3. Generate data + indexes

```bash
python -m data_gen.write_issues          # ~6 min, ~1500 Sonnet calls via FM API
python -m data_gen.gen_manuals           # ~30 Sonnet calls, fast
python -m data_gen.parse_chunk_manuals   # ai_parse_document + ai_prep_search
python -m infra.setup_vector_search      # First sync ~5-10 min per index
# Apply UC function tools by running agent/tools.sql in Databricks SQL.
```

### 4. Build the React frontend

```bash
cd app/frontend && npm install && npm run build && cd ../..
# Fresh checkout npm install: ~2-3 min. Subsequent rebuilds: ~10s.
```

`databricks.yml` has `sync.include: app/frontend/dist/**` so the built
bundle ships even though `.gitignore` excludes `dist/`.

### 5. Deploy the bundle

```bash
databricks bundle validate
databricks bundle deploy --target dev
# First deploy: ~5 min upload + ~5-10 min container start.
# Subsequent deploys (code-only): ~1-2 min.
```

This creates the MLflow experiment, the App resource, and the weekly eval
job. In `dev` mode the experiment name is prefixed with `[dev <user>]`
(standard DAB behavior); the prod target writes to the unprefixed name.

### 6. Run the bundle's eval job (optional, smoke-only)

```bash
databricks bundle run fsisim_eval --target dev
```

### 7. Grant the App SP access to Lakebase + init schema

`databricks bundle deploy` creates the App but does NOT grant its service
principal access to Lakebase (Lakebase ACLs are out-of-band). Discover the
SP, then grant + init:

```bash
APP=$(databricks bundle summary --target dev --output json \
  | jq -r '.resources.apps.fsisim_scaffold.name')

APP_SP=$(databricks apps get "$APP" --output json \
  | jq -r '.service_principal_client_id')

uv run python scripts/grant_lakebase_permissions.py "$APP_SP" \
  --memory-type langgraph \
  --instance-name <lakebase_instance_name>

uv run python -m scripts.init_lakebase_schema
```

`init_lakebase_schema` creates the `agent_server` schema plus the
`messages` and `message_feedback` tables.

> **Heads up:** the DAB `database` resource binding for Lakebase requires
> a **workspace-admin deployer**. If you're not an admin, skip the binding
> and pass `LAKEBASE_INSTANCE_NAME` / `LAKEBASE_DATABASE_NAME` directly via
> `app.yaml` env (already wired in this repo).

### 8. Smoke

```bash
APP_URL=$(databricks apps get "$APP" --output json | jq -r '.url')
uv run python -m scripts.smoke --app-url "$APP_URL"
```

The smoke posts a chat message, posts thumbs-up feedback against the
returned `assistant_message_id`, and lists threads. All three must return
2xx.

## Discovery commands

The deployer needs these handy:

```bash
# App service principal (input to grant_lakebase_permissions.py):
databricks apps get <agent_app_name> --output json | jq -r '.service_principal_client_id'

# App URL (input to scripts/smoke.py and your browser):
databricks apps get <agent_app_name> --output json | jq -r '.url'

# SQL warehouse used by grant SQL statements (defaults to first RUNNING):
databricks warehouses list
```

## Per-deploy after the first

```bash
cd app/frontend && npm run build && cd ../..
databricks bundle deploy --target dev
# ~1-2 min when only code changes.
```

If you change the Lakebase schema, re-run `scripts/init_lakebase_schema`.
If you reset the Lakebase instance, re-run both `grant_lakebase_permissions`
and `init_lakebase_schema`.

## How tracing + feedback connect

- `/api/chat` posts to AgentServer's `/invocations` endpoint on
  `localhost:8000` (single-container deploy). AgentServer wraps the call in
  an MLflow trace and returns the `trace_id` via the `mlflow-trace-id`
  response header (with `x-mlflow-trace-id` and `custom_outputs.trace_id`
  as fallbacks).
- The app persists `mlflow_trace_id` on the assistant row in
  `agent_server.messages` keyed by the same `assistant_message_id` the UI
  shows.
- `/api/feedback` looks up `mlflow_trace_id` from that row by
  `message_id`, writes a thumb in `agent_server.message_feedback`
  (Lakebase mirror so the UI can re-render without an MLflow round-trip),
  and calls `mlflow.log_feedback` to attach an Assessment to the original
  trace.

So a thumb in the UI lands on the exact MLflow trace the assistant turn
produced. The dev-mode `[dev <user>]` experiment prefix means your traces
won't collide with another deployer's in the same workspace.

## Forking for production

Every UC name, endpoint name, and model name lives in `config.py` or as a
DAB variable. To repoint at a customer-facing catalog and workspace:

```bash
databricks bundle deploy --target prod \
  --var catalog=poc_data \
  --var schema=<your-schema> \
  --var lakebase_instance_name=<your-lakebase> \
  --var agent_app_name=<your-app>

export FSISIM_VS_ENDPOINT=<your-vs-endpoint>
export FSISIM_LLM_ENDPOINT=databricks-claude-sonnet-4-5   # or your custom endpoint
```

Then re-run:
- `python -m infra.setup_catalog`
- `python -m infra.setup_vector_search`

Replace `data_gen/write_issues.py` and the manuals pipeline with whatever
real-data ingestion path you build. The agent code (`agent_server/agent.py`,
`agent_server/prompts.py`) and app code (`app/`) do not change; they read
names from `config.py` and env vars at runtime.

## Repo layout

```
.
|-- config.py                # source of truth for UC/index/endpoint names
|-- databricks.yml           # DAB variables + app + experiment + eval job
|-- pyproject.toml
|-- app.yaml                 # Databricks Apps manifest (env passthrough)
|-- infra/
|   |-- setup_catalog.py     # catalog + schema + volume (idempotent)
|   `-- setup_vector_search.py
|-- data_gen/
|   |-- schema.py            # PySpark schema for g001_issue (28 cols)
|   |-- value_domains.py     # categorical pools (sim names, systems, etc.)
|   |-- seed_samples.json    # 5 seed sample rows
|   |-- note_authoring.py    # NoteAuthor: one call per note via FM API
|   |-- gen_issues.py        # IssueGenerator with seed-determinism + arc logic
|   |-- write_issues.py      # parallel LLM authoring + parquet + CTAS to Delta
|   |-- gen_manuals.py       # 6 watermarked PDF manuals, FM API authored
|   `-- parse_chunk_manuals.py  # ai_parse_document + ai_prep_search
|-- agent_server/
|   |-- agent.py             # @invoke handler, MLflow tracing + Lakebase memory
|   |-- routes.py            # FastAPI routes mounted on AgentServer
|   |-- memory.py            # Lakebase OAuth-token-refresh PG helpers
|   |-- prompts.py           # SYSTEM_PROMPT
|   |-- personas.py          # eval personas (input to scripts/run_eval.py)
|   |-- evaluate_agent.py    # mlflow.genai.evaluate harness
|   `-- start_server.py      # AgentServer factory + custom-router mount
|-- agent/
|   `-- tools.sql            # UC function DDL for both search tools
|-- app/
|   |-- backend/
|   |   |-- main.py          # legacy (Task 11 routed through AgentServer)
|   |   `-- agent_client.py
|   `-- frontend/
|       |-- src/
|       |   |-- theme.ts             # FS_NAVY #003865, FS_GOLD #FFB81C, Roboto
|       |   |-- App.tsx              # top bar + left rail + chat
|       |   |-- api/chat.ts          # POST /api/chat client
|       |   `-- components/          # ChatThread, MessageBubble, Citation*
|       `-- vite.config.ts
|-- scripts/
|   |-- grant_lakebase_permissions.py
|   |-- init_lakebase_schema.py
|   |-- run_eval.py          # DAB job entrypoint
|   `-- smoke.py             # post-deploy smoke check
`-- tests/                   # pytest suite (unit only, no live workspace)
```

## Known limitations

- `ai_prep_search` and reranking are Public Preview / Beta. A workspace
  admin must enable them in the Previews page. If unavailable, the manuals
  pipeline falls back to plain `ai_parse_document` with hand-rolled chunking.
- The app uses Databricks Apps SSO; no separate auth layer.
- All manual PDFs are watermarked SAMPLE / NOT REAL. Do not strip the
  watermark; it's a hedge against synthetic content being mistaken for
  real internal docs.
- The synthetic data only captures past resolutions, not ordered
  troubleshooting steps. The agent surfaces prior resolutions rather than
  inventing a procedure.

## Cost notes

- Issue data generation: ~1,500 Sonnet calls via FM API (~$5-10 in DBU).
- Manual PDF authoring: ~30 Sonnet calls (~$0.50).
- VS endpoint: STANDARD endpoint runs continuously. Stop it when not in use.
- App + AgentServer: pay-per-request inside the App container (no separate
  Model Serving endpoint).

## Style

- No em or en dashes. Use colons, semicolons, parens.
- One source of truth: `config.py` for UC names; `databricks.yml` for
  deploy-time variables. Never hardcode either elsewhere.
