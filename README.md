# fsisim-poc-scaffold

A working, FlightSafety-branded reference implementation of the FSISIM
Technician Issue Resolution Agent. Mock data, two Mosaic AI Vector Search
indexes, a Mosaic AI Agent with two tools, and a React + FastAPI app
deployed as a Databricks App.

Companion docs (Obsidian vault):
- Spec: `~/Desktop/Vault/Work/Projects/fsisim-poc-scaffold/Project.md`
- Plan: `~/Desktop/Vault/Work/Projects/fsisim-poc-scaffold/Implementation-Plan.md`
- Architecture (customer-facing): `FSI SIM POC Solution Overview - May 14.docx`

## What this is (and isn't)

This is a SCAFFOLD with synthetic data. It exists so:

1. Matt's team has a working Databricks pattern to copy when he returns from vacation.
2. The architecture is de-risked end-to-end before real FSISIM data lands.
3. Stakeholders see concrete progress while the expectations reset is in flight.

It does NOT:
- Use real FSISIM data
- Cover the full 25 PDF manual corpus
- Run the MLflow Agent Evaluation harness (v2)
- Try to generate step-by-step troubleshooting outputs (the data only logs resolutions)

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
  databricks fs cp "$f" "dbfs:/Volumes/${FSISIM_CATALOG:-jdub_demo}/fsisim_issue_ai_gold/manuals/$(basename $f)" --overwrite
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

# 10. Build the frontend, then deploy the Databricks App
cd app/frontend && npm install && npm run build && cd ../..
databricks apps create fsisim-scaffold
databricks apps deploy fsisim-scaffold --source-code-path "$PWD/app"
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
|   |-- seed_samples.json    # Matt's 5 sample rows verbatim
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
|   |-- backend/
|   |   |-- main.py          # FastAPI: /api/health, /api/chat (SSE)
|   |   `-- agent_client.py
|   `-- frontend/
|       |-- src/
|       |   |-- theme.ts             # FS_NAVY #003865, FS_GOLD #FFB81C, Roboto
|       |   |-- App.tsx              # top bar + left rail + chat + footer
|       |   |-- api/chat.ts          # SSE generator
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
- All manual PDFs are watermarked SAMPLE / NOT REAL. Do NOT strip the watermark
  when forking; it's a hedge against the synthetic content being mistaken for
  real FlightSafety internal docs.
- The business-expectations gap (customer wants ordered troubleshooting steps,
  but the FSISIM data only captures resolutions) is mitigated in the system
  prompt and in the footer disclaimer, but the real fix is Matt and Sanjay
  resetting expectations with the business.

## Cost notes

- Issue data generation: ~1,500 Sonnet calls via FM API (~$5-10 in DBU).
- Manual PDF authoring: ~30 Sonnet calls (~$0.50).
- VS endpoint: STANDARD endpoint runs continuously; estimate ~$X per hour
  depending on workspace pricing. Stop the endpoint when not in use.
- Agent serving endpoint: same.

## Style

- No em or en dashes. Use colons, semicolons, parens.
- One source of truth: `config.py`. Never hardcode UC names elsewhere.
