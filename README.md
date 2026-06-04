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

# 3. Provision UC (catalog, schema, volume)
python -m infra.setup_catalog

# 4. Generate issue data (~6 min, calls Sonnet 1.5K times via FM API)
python -m data_gen.write_issues

# 5. Generate manual PDFs (~6 docs, ~1 min) and upload to volume
python -m data_gen.gen_manuals
for f in generated_manuals/*.pdf; do
  databricks fs cp "$f" "dbfs:/Volumes/${FSISIM_CATALOG:-your_catalog}/fsisim_issue_ai_gold/manuals/$(basename $f)" --overwrite
done

# 6. Parse and chunk manuals (requires ai_prep_search Beta enabled)
python -m data_gen.parse_chunk_manuals

# 7. Vector Search endpoint and both indexes (re-run after step 6 to add manual index)
python -m infra.setup_vector_search

# 8. UC function tools
python -c "from agent.tools import apply; apply()"   # if you wired tools.sql to a Python helper
# OR use the SQL file directly via databricks sql query.

# 9. Deploy the agent as a serving endpoint
python -m agent.deploy_agent

# 10. Build the frontend locally
cd app/frontend && npm install && npm run build && cd ../..

# 11. Create the Databricks App (first time only)
databricks apps create fsisim-scaffold

# 12. Sync source to the workspace. app/.databricksignore excludes
#     node_modules, frontend/src, package.json, etc., so only backend/,
#     app.yaml, requirements.txt, and frontend/dist/ end up in the
#     workspace path.
databricks sync ./app /Workspace/Users/<your-email>/fsisim-scaffold --watch=false

# 13. Push the built frontend dist/ directly (databricks sync respects the root
#     .gitignore which excludes dist/, so it must be uploaded out-of-band)
databricks workspace delete \
  /Workspace/Users/<your-email>/fsisim-scaffold/frontend/dist --recursive 2>/dev/null
databricks workspace import-dir \
  ./app/frontend/dist \
  /Workspace/Users/<your-email>/fsisim-scaffold/frontend/dist \
  --overwrite

# 14. Deploy
databricks apps deploy fsisim-scaffold \
  --source-code-path /Workspace/Users/<your-email>/fsisim-scaffold
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
