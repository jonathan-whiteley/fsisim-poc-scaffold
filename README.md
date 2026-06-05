# fsisim-poc-scaffold

A reference implementation of an issue resolution agent for flight simulator
maintenance. Synthetic data, two Mosaic AI Vector Search indexes, a Mosaic
AI Agent with two tools, and a React + FastAPI app deployed as a Databricks
App.

## What this is (and isn't)

This is a scaffold with synthetic data. The point is to de-risk the
architecture end-to-end before real data lands, and to provide a working
Databricks pattern that can be forked and repointed at a production catalog.

It does NOT:
- Use real data
- Cover a full manual corpus (ships with 6 fabricated PDFs)
- Run the MLflow Agent Evaluation harness
- Generate step-by-step troubleshooting outputs (the synthetic data only
  captures past resolutions)

## Architecture

```
User
  -> chat
React App  --HTTPS-->  FastAPI (Databricks App)
                            |
                            v
                 Mosaic AI Agent (ResponsesAgent)
                 |
                 +-- Tool: search_technical_manuals --> manual_knowledge_index (VS)
                 +-- Tool: search_past_issues       --> issue_history_index    (VS)
                            |
                            v
                 Sonnet 4.5 (Foundation Model API) synthesizes answer with citations
```

## Quickstart

```bash
# 1. Bootstrap
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
pytest -q

# 2. Authenticate to your Databricks workspace
databricks auth login --host https://<your-workspace>.cloud.databricks.com

# 3. Provision UC (catalog, schema, volume) — one-time
python -m infra.setup_catalog

# 4-8. Generate data + indexes (unchanged)
python -m data_gen.write_issues
python -m data_gen.gen_manuals
python -m data_gen.parse_chunk_manuals
python -m infra.setup_vector_search
# Apply UC function tools via tools.sql (Databricks SQL)

# 9. Provision a Lakebase instance (one-time, outside DAB)
#    via the workspace UI or the FEVM CLI; record its name.
#    Default in databricks.yml: fsisim-poc

# 10. Build the React frontend
cd app/frontend && npm install && npm run build && cd ../..

# 11. Deploy the bundle (creates app, experiment, eval job)
databricks bundle validate
databricks bundle deploy --target dev

# 12. After first deploy: grant Lakebase permissions + create custom schema
APP_SP=$(databricks apps get fsisim-scaffold --output json | jq -r '.service_principal_client_id')
uv run python scripts/grant_lakebase_permissions.py "$APP_SP" \
  --memory-type langgraph --instance-name fsisim-poc
uv run python -m scripts.init_lakebase_schema

# 13. Smoke
uv run python -m scripts.smoke --app-url https://<app-host>
```

Per-deploy after the first:

```bash
cd app/frontend && npm run build && cd ../..
databricks bundle deploy --target dev
```

## Forking for production

Every UC name, endpoint name, and model name lives in `config.py`. To repoint
at the customer-facing catalog and workspace:

```bash
export FSISIM_CATALOG=poc_data
export FSISIM_VS_ENDPOINT=<your-vs-endpoint>
export FSISIM_LLM_ENDPOINT=databricks-claude-sonnet-4-5   # or your custom endpoint
```

Then re-run:
- `python -m infra.setup_catalog`
- `python -m infra.setup_vector_search`
- `python -m agent.deploy_agent`

Replace `data_gen/write_issues.py` and the manuals pipeline with whatever
real-data ingestion path you build. The agent code (`agent/agent.py`,
`agent/prompts.py`) and app code (`app/`) do not change; they read names
from `config.py` at runtime.

## Repo layout

```
.
|-- config.py                # source of truth for all UC/index/endpoint names
|-- pyproject.toml
|-- databricks.yml           # (optional) Databricks Asset Bundle
|-- infra/
|   |-- setup_catalog.py     # creates catalog, schema, volume
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
|-- agent/
|   |-- prompts.py           # SYSTEM_PROMPT with jargon-resolver + no-procedural-steps
|   |-- agent.py             # build_agent_config() + ResponsesAgent wrapper
|   |-- tools.sql            # UC function DDL for both search tools
|   `-- deploy_agent.py      # MLflow log_model + UC register + deploy
|-- app/
|   |-- app.yaml             # Databricks Apps manifest
|   |-- requirements.txt
|   |-- .databricksignore    # excludes node_modules + frontend source from deploys
|   |-- backend/
|   |   |-- main.py          # FastAPI: /api/health, /api/chat, /api/manuals, /api/_diag
|   |   `-- agent_client.py
|   `-- frontend/
|       |-- src/
|       |   |-- theme.ts             # FS_NAVY #003865, FS_GOLD #FFB81C, Roboto
|       |   |-- App.tsx              # top bar + left rail + chat
|       |   |-- api/chat.ts          # POST /api/chat client
|       |   `-- components/
|       |       |-- LeftRail.tsx
|       |       |-- ChatThread.tsx
|       |       |-- MessageBubble.tsx
|       |       |-- CitationPill.tsx
|       |       `-- CitationSlideOver.tsx
|       `-- vite.config.ts
`-- tests/                   # pytest suite (all unit tests, no live workspace)
```

## Known limitations

- `ai_prep_search` and reranking are Public Preview / Beta features. A workspace
  admin must enable them in the Previews page. If your region or workspace
  doesn't have them, the manuals pipeline falls back to plain `ai_parse_document`
  with hand-rolled chunking.
- The app uses Databricks Apps SSO; no separate auth layer.
- All manual PDFs are watermarked SAMPLE / NOT REAL. Do not strip the
  watermark when forking; it's a hedge against the synthetic content being
  mistaken for real internal docs.
- The synthetic data only captures past resolutions, not ordered
  troubleshooting steps. The agent surfaces prior resolutions rather than
  inventing a procedure.

## Cost notes

- Issue data generation: ~1,500 Sonnet calls via FM API (~$5-10 in DBU).
- Manual PDF authoring: ~30 Sonnet calls (~$0.50).
- VS endpoint: STANDARD endpoint runs continuously; estimate ~$X per hour
  depending on workspace pricing. Stop the endpoint when not in use.
- Agent serving endpoint: same.

## Style

- No em or en dashes. Use colons, semicolons, parens.
- One source of truth: `config.py`. Never hardcode UC names elsewhere.
