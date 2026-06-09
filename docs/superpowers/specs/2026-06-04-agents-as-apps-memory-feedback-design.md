# Agents as Apps + Lakebase memory + thumbs feedback + MLflow eval

**Status**: Approved (brainstorm phase complete; implementation plan pending)
**Branch**: `feat/agents-as-apps-memory-feedback`
**Worktree**: `.worktrees/agents-as-apps-memory-feedback`
**Author**: Jonathan Whiteley
**Date**: 2026-06-04

## Goal

Add three production-readiness features to the FSISIM scaffold, in one branch, by adopting the Databricks "Agents as Apps" pattern (per `databricks/app-templates/agent-openai-agents-sdk`):

1. **Lakebase-backed conversation memory** so users can resume prior threads and the agent can reason across turns.
2. **Thumbs up/down feedback** logged as MLflow trace assessments (source of truth) and mirrored to Lakebase for app-side rendering.
3. **Tied MLflow experiment + automatic tracing + git-based agent version tracking**, plus an `mlflow.genai.evaluate` harness with FSISIM-specific personas.

Bundle the work as a DAB-native deploy so future changes ship through `databricks bundle deploy` instead of the sync + workspace import-dir + apps deploy dance.

## Non-goals

- Streaming responses in the React UI (the agent supports it, but the React thread doesn't render streamed chunks today; can come later).
- SME-driven labeling via the MLflow Review App (not supported for Apps-deployed agents per docs; would require Labeling Sessions, out of scope).
- Multi-tenant scaling (single-team demo; one App, one Lakebase instance).
- A separate Model Serving deployment of the agent (we accept the "agent is in-process" tradeoff documented in the design discussion). Future work can add a Model Serving "publish" step if other consumers need to call the agent.

## Architecture

```
                          Databricks Apps SSO
                          (X-Forwarded-Email)
                                 |
                                 v
                          React app  (thread sidebar, thumbs UI, citation pills)
                                 |
                                 v
              FastAPI process (Agents as Apps container)
              ┌────────────────────────────────────────────────────────┐
              │                                                        │
              │   AgentServer("ResponsesAgent", enable_chat_proxy=False)
              │     │                                                  │
              │     ├── @invoke()  ── LangGraph ReAct agent            │
              │     │                  + PostgresSaver (Lakebase)      │
              │     │                  + UC function tools (existing)  │
              │     │                                                  │
              │     └── @stream()  (defined but not used by React v1)  │
              │                                                        │
              │   Custom routes:                                       │
              │     GET  /api/threads          -> Lakebase             │
              │     GET  /api/threads/{id}     -> Lakebase             │
              │     POST /api/chat             -> @invoke fn (in-proc) │
              │     POST /api/feedback         -> MLflow + Lakebase    │
              │     GET  /api/manuals/{name}   -> Files API (existing) │
              │     GET  /api/_diag            -> (existing)           │
              │     /static/*                  -> app/frontend/dist/   │
              │                                                        │
              └────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                          Lakebase Postgres
                          ┌────────────────────────────────────────┐
                          │ public.*         (LangGraph checkpoints) │
                          │ agent_server.responses                   │
                          │ agent_server.messages                    │
                          │ agent_server.message_feedback (NEW)      │
                          └────────────────────────────────────────┘

                          MLflow experiment
                          ┌────────────────────────────────────────┐
                          │ Traces (auto via langchain.autolog)     │
                          │ Trace metadata: session=thread_id       │
                          │ Trace assessments (feedback)            │
                          │ Git SHA version tags                    │
                          └────────────────────────────────────────┘

                          UC Vector Search (existing, unchanged)
                          ┌────────────────────────────────────────┐
                          │ manual_knowledge_index                  │
                          │ issue_history_index                     │
                          └────────────────────────────────────────┘
```

### Key choices

- **In-process agent**: the LangGraph ReAct agent runs inside the FastAPI container, not as a separate Model Serving endpoint. Tradeoff: agent scales with the App; agent isn't reusable by other consumers without a future publish step. Acceptable for a scaffold; documented in non-goals.
- **AgentServer wrapper from `mlflow.genai.agent_server`**: provides FastAPI scaffolding, the `@invoke`/`@stream` decorator pattern, and integrates auto-tracing. `enable_chat_proxy=False` because we serve our own React UI.
- **MLflow experiment as a DAB resource**: `databricks.yml` declares `resources.experiment.fsisim_agent`; the App's `MLFLOW_EXPERIMENT_ID` env var uses `valueFrom: experiment`. No manual experiment ID config; reproducible across targets.
- **Git-based agent versioning** via `setup_mlflow_git_based_version_tracking()`. Replaces the older `mlflow.register_model` + `databricks.agents.deploy` flow. We do NOT register the agent to UC; if a future consumer needs that, a `mlflow.pyfunc.log_model` step can be added to the eval job.
- **LangGraph PostgresSaver** for conversation state. Checkpoint tables (`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`, `checkpoint_migrations`, `store`, `store_vectors`, `store_migrations`, `vector_migrations`) are created automatically by LangGraph on first connect.
- **`agent_server.responses` + `agent_server.messages`** are managed by the AgentServer itself (per template's `grant_lakebase_permissions.py`). We read from these for the `/api/threads` and `/api/threads/{id}` routes.
- **Feedback source of truth**: MLflow trace assessment (via `mlflow.log_feedback`). Lakebase mirror (`agent_server.message_feedback`) is a denormalized read-cache so the React app re-renders thumb state without round-tripping to MLflow on every page load.
- **Identity**: Databricks Apps inject `X-Forwarded-Email` and `X-Forwarded-User`; never trust client-supplied user IDs.

## Components

### 1. `agent_server/` (new module, replaces `agent/` and `app/backend/agent_client.py`)

```
agent_server/
├── __init__.py
├── agent.py                @invoke / @stream wrapping LangGraph ReAct + PostgresSaver
├── memory.py               Lakebase connection (SP OAuth, conn pool), exposes a PostgresSaver factory
├── personas.py             FSISIM eval personas (parameterizable path)
├── evaluate_agent.py       mlflow.genai.evaluate + ConversationSimulator
├── routes.py               custom FastAPI routes (/api/threads, /api/chat, /api/feedback)
├── start_server.py         AgentServer instantiation + route mounting + static serving
└── utils.py                session_id, user identity, citation re-query
```

- `agent.py` is the only file that ResponsesAgent code lives in. It imports memory + tools and defines `@invoke()` (sync handler) and `@stream()` (defined but unused by v1 React client).
- `memory.py` exposes `get_saver() -> PostgresSaver`. The connection uses `WorkspaceClient().database.generate_database_credential()` for OAuth (SP-scoped; valid ~50 min). Connection pool: `psycopg_pool.ConnectionPool` with a token-refresh hook.
- `routes.py` is mounted by `start_server.py` onto the AgentServer's FastAPI app. The `/api/chat` route calls the `@invoke`-registered function directly (no HTTP self-call).
- `personas.py`: list of `{goal, persona, simulation_guidelines}` dicts (the template's shape), e.g. "FlightSafety technician troubleshooting a hydraulic pressure drop on takeoff", "FMS VNAV jargon clarification", "Motion platform fault code 47B".

### 2. Lakebase schema additions

LangGraph checkpoint tables (`public.*`) and AgentServer tables (`agent_server.responses`, `agent_server.messages`) are auto-created. We add ONE custom table:

```sql
CREATE SCHEMA IF NOT EXISTS agent_server;

CREATE TABLE agent_server.message_feedback (
  message_id      text PRIMARY KEY,            -- AgentServer message id; also lives in agent_server.messages
  rating          text NOT NULL CHECK (rating IN ('up','down')),
  comment         text,
  user_email      text NOT NULL,
  mlflow_trace_id text,                        -- joins back to MLflow trace
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX message_feedback_user_idx ON agent_server.message_feedback(user_email, created_at DESC);
```

Provisioning: a thin script `scripts/init_lakebase_schema.py` runs `CREATE SCHEMA / CREATE TABLE IF NOT EXISTS`. Called once after bundle deploy.

### 3. `databricks.yml` (new DAB root)

```yaml
bundle:
  name: fsisim_poc_scaffold

variables:
  catalog:
    default: jdub_demo
  schema:
    default: fsisim_issue_ai_gold
  lakebase_instance_name:
    default: fsisim-poc
  lakebase_database_name:
    default: fsisim_chat
  eval_personas_file:
    default: agent_server/personas.py

resources:
  apps:
    fsisim_scaffold:
      name: fsisim-scaffold
      description: FSISIM Issue Resolution Agent (synthetic data)
      source_code_path: ./
      config:
        command: ["uv", "run", "start-app"]
        env:
          - name: MLFLOW_TRACKING_URI
            value: "databricks"
          - name: MLFLOW_REGISTRY_URI
            value: "databricks-uc"
          - name: MLFLOW_EXPERIMENT_ID
            value_from: "experiment"
          - name: LAKEBASE_INSTANCE_NAME
            value: ${var.lakebase_instance_name}
          - name: LAKEBASE_DATABASE_NAME
            value: ${var.lakebase_database_name}
          - name: LAKEBASE_AGENT_MEMORY_SCHEMA
            value: "agent_server"
          - name: FSISIM_CATALOG
            value: ${var.catalog}
          - name: FSISIM_SCHEMA
            value: ${var.schema}
      resources:
        - name: experiment
          experiment:
            permission: CAN_MANAGE

  jobs:
    fsisim_eval:
      name: fsisim-eval
      schedule:
        quartz_cron_expression: "0 0 7 ? * MON"   # Mondays 07:00 UTC
        timezone_id: UTC
      tasks:
        - task_key: evaluate
          spark_python_task:
            python_file: scripts/run_eval.py
            parameters:
              - "--personas-file"
              - ${var.eval_personas_file}

targets:
  dev:
    mode: development
    default: true
  prod:
    mode: production
```

The Lakebase instance itself: provisioned via the FEVM `mcp__plugin_fe-ai-tools_fe-vending-machine` MCP, NOT via DAB (Lakebase is not yet a DAB-managed resource in this workspace as of 2026-06). Documented in the implementation plan as a one-time setup step.

### 4. React UI changes

- `LeftRail.tsx`: today it's a placeholder. Becomes a thread list:
  ```
  [+ New chat]
  ── Threads ─────────────
   Hydraulic pressure drop (today)
   FMS VNAV question (yesterday)
   Motion platform 47B (last week)
  ```
  Driven by `GET /api/threads`. Clicking a row loads via `GET /api/threads/{id}` and replaces the chat state.
- `ChatThread.tsx`: accepts `threadId` prop; loads messages on mount; `/api/chat` POST includes `thread_id` in the body.
- `MessageBubble.tsx`: thumbs up/down icons on assistant bubbles. Click fires `POST /api/feedback`; visually locks in the rating. Initial state is pre-populated from `agent_server.message_feedback` on thread load.

### 5. MLflow plumbing — minimal custom code

- `start_server.py` calls `setup_mlflow_git_based_version_tracking()` at import time.
- `agent.py` calls `mlflow.langchain.autolog()` at import time.
- Each `@invoke()` call:
  - Auto-emits a trace.
  - Adds session metadata via `mlflow.update_current_trace(metadata={"mlflow.trace.session": thread_id, "user_email": email})`.
  - Persists LangGraph state via PostgresSaver (no manual code; LangGraph handles it).
- Feedback route calls `mlflow.log_feedback(trace_id=..., name="thumbs", value=rating, rationale=comment)`.

### 6. Eval harness

- `agent_server/evaluate_agent.py` lifted from template; `test_cases` replaced with `personas` loaded from `${var.eval_personas_file}`.
- Scorers: `Completeness`, `RelevanceToQuery`, `ToolCallCorrectness`, `Safety`, `Fluency`. We drop `ConversationalSafety` and `UserFrustration` (overkill for technical Q&A).
- `scripts/run_eval.py` (NEW): thin wrapper that loads the personas file, calls `evaluate_agent.evaluate()`. Designed to run as a DAB job task.
- Runs weekly per the DAB schedule; results land in the MLflow experiment under "evaluations".

### Scripts overview

| Script | Origin | Purpose |
|---|---|---|
| `scripts/grant_lakebase_permissions.py` | lifted from template (verbatim) | Grant the app SP `USAGE` + table grants on Lakebase memory tables. Run once after first deploy |
| `scripts/init_lakebase_schema.py` | NEW (fsisim-specific) | `CREATE SCHEMA agent_server`, `CREATE TABLE agent_server.message_feedback`. Idempotent. Run once before first chat |
| `scripts/run_eval.py` | NEW | DAB job entrypoint for the weekly eval |
| `scripts/start_app.py` | lifted from template (adapted) | Local dev runner; lets `uv run start-app` work both locally and in the deployed App |
| `scripts/smoke.py` | NEW | Post-deploy smoke test; chats once, thumbs up, verifies trace assessment |

## Data flow

### Chat turn (new conversation)

```
React: POST /api/chat { content: "hydraulic pressure drop on takeoff" }
       (no thread_id -> backend creates one)

FastAPI: validates X-Forwarded-Email; mints thread_id (uuid);
         calls @invoke registered fn with custom_inputs={thread_id, user_email}

@invoke: mlflow.langchain.autolog started trace
         mlflow.update_current_trace(metadata={"mlflow.trace.session": thread_id, "user_email": ...})
         PostgresSaver loads thread state (empty for new thread)
         LangGraph ReAct: tool calls search_past_issues + search_technical_manuals
         LangGraph synthesizes response
         PostgresSaver commits new checkpoint
         Returns ResponsesAgentResponse with output text + custom_outputs={message_id, assistant_message_id}

FastAPI: re-queries VS indexes for citations (existing logic)
         Returns { thread_id, text, manual_citations, issue_citations,
                   user_message_id, assistant_message_id }

React: renders text + citations + thumbs (initially blank);
       updates URL to /chat/{thread_id} (deep-linkable)
```

### Chat turn (resume existing thread)

```
React: page load -> GET /api/threads/{id}
       Renders prior messages + their thumb states
       User types new turn -> POST /api/chat { thread_id, content }
       Same as above; LangGraph PostgresSaver hydrates prior state.
```

### Thumbs click

```
React: POST /api/feedback { message_id: "abc", rating: "up" }

FastAPI: SELECT mlflow_trace_id FROM agent_server.messages WHERE id = 'abc'
         mlflow.log_feedback(trace_id=trace_id, name="thumbs",
                              value="up", rationale=None, source_run_id=...)
         INSERT INTO agent_server.message_feedback ... ON CONFLICT (message_id) DO UPDATE ...
         Returns 200

React: locks in rating visually (already done optimistically; rolls back on 4xx/5xx)
```

## Error handling

| Failure | Behavior |
|---|---|
| Lakebase unreachable on `/api/chat` | 503; React shows banner "Memory backend offline; chat unavailable". No silent fallback to stateless; we want failures visible |
| Lakebase unreachable on `/api/threads` | 503; sidebar shows banner; new chats still work (just no resume) |
| MLflow `log_feedback` fails on `/api/feedback` | Write to Lakebase, log warning, return 200. Lakebase is enough for app-side render; eventual consistency with MLflow is acceptable |
| LangGraph PostgresSaver token expiry mid-request | Connection pool's token-refresh hook re-mints; one retry on failure |
| Agent timeout >60s | 504; React shows retry button |
| Citation re-query VS failure | Return chat text without citations + log warning |
| `X-Forwarded-Email` header missing (impossible in production Apps, but for safety) | 401; React shows "Authentication required" |
| Manual PDF fetch failure | Existing behavior: text/plain error message in new tab |

## Testing

| Layer | What | How |
|---|---|---|
| Unit | FastAPI routes | `tests/test_routes.py` with mocked `@invoke` fn + mocked Lakebase pool |
| Unit | Memory helpers | `tests/test_memory.py` for connection lifecycle + token refresh |
| Unit | Eval personas valid | `tests/test_personas.py` confirms each persona has required keys + non-empty values |
| Integration | LangGraph + PostgresSaver | `tests/integration/test_checkpoint.py` runs a 2-turn conversation against a local Postgres container (CI-only) |
| Integration | `/api/feedback` writes to both sinks | Mock MLflow; real local Postgres |
| Smoke | Full chat flow against deployed app | `scripts/smoke.py` POSTs a chat, verifies citations + assistant_message_id; thumbs up; verifies trace assessment in MLflow |
| Eval | `mlflow.genai.evaluate` with personas | `databricks bundle run fsisim_eval` |

CI changes: GitHub Actions workflow adds a step that spins up a Postgres container for integration tests. Unit tests stay fast (no external deps).

## Deployment

Replacing the current sync + workspace import-dir + apps deploy flow with:

```bash
# One-time per workspace:
databricks bundle init       # only if databricks.yml missing
# Provision Lakebase via FEVM (one-time; not in DAB)
uv run scripts/init_lakebase_schema.py
uv run scripts/grant_lakebase_permissions.py <app-sp-client-id> --memory-type langgraph --instance-name fsisim-poc

# Per deploy:
cd app/frontend && npm run build && cd ../..
databricks bundle validate
databricks bundle deploy --target dev
databricks bundle run fsisim_eval --target dev   # optional smoke
```

`README.md` is updated to reflect this flow. The "Deploy gotchas" section (already removed in main) does not return; the bundle handles ordering and the build context.

## Open questions (for implementation phase)

1. **Lakebase instance creation**: confirm whether FEVM `create_addon` supports Lakebase autoscaling, or if we need a provisioned instance via the workspace UI. Implementation plan picks one based on workspace state.
2. **`mlflow.log_feedback` exact signature in current MLflow version**: docs in flux between `update_assessments` (older) and `log_feedback` (newer). Confirm at impl time.
3. **AgentServer's `agent_server.responses` schema**: do we need to read `messages` table or `responses` table for `/api/threads/{id}`? Confirm with the template's source. If both exist, document the join.
4. **`@invoke()` decorator custom_outputs support**: this design assumes the `@invoke` decorator passes through `ResponsesAgentResponse.custom_outputs` (e.g., to surface `assistant_message_id` to the frontend). The template's example doesn't show this. Confirm at impl time; fallback is to add a custom FastAPI route that wraps the invoke call and adds the field.
5. **CI**: the project has no CI workflow today. Integration tests requiring a local Postgres container are spec'd but treated as "local-only" unless we explicitly add a `.github/workflows/test.yml` in this branch. Decision deferred to implementation plan.

## What this design explicitly cuts

- Streaming responses in React (the agent supports it; React doesn't render yet; can add later)
- UC `register_model` of the agent (git-based version tracking replaces it)
- Custom `threads`/`messages` SQL tables (use AgentServer's built-ins)
- Custom MLflow `start_run`/`start_span` calls (autolog replaces them)
- A separate Model Serving deployment of the agent (in-process only for v1)
- MLflow Review App integration (not supported for Apps-deployed agents)
- ConversationalSafety + UserFrustration scorers (overkill for technical Q&A; can re-add per persona later)

## Reference

- Databricks "Author an agent" docs: https://docs.databricks.com/aws/en/generative-ai/agent-framework/author-agent
- Template repo: https://github.com/databricks/app-templates/tree/main/agent-openai-agents-sdk
- Templates catalog: https://developers.databricks.com/templates
