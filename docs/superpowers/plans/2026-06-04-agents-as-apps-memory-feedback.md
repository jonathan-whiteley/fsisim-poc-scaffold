# Agents as Apps + Lakebase memory + thumbs feedback + MLflow eval — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the FSISIM scaffold to the Agents-as-Apps pattern with Lakebase-backed conversation memory, thumbs feedback wired to MLflow trace assessments, automatic tracing, and a weekly `mlflow.genai.evaluate` job — all deployed via `databricks bundle deploy`.

**Architecture:** Replace the separate Model Serving agent + FastAPI relay with a single FastAPI process that runs `mlflow.genai.agent_server.AgentServer`. The agent uses `@invoke`/`@stream` decorators wrapping LangGraph + a `PostgresSaver` checkpoint that writes to Lakebase. Our React SPA replaces the built-in chat UI (`enable_chat_proxy=False`). MLflow experiment is a DAB resource auto-bound to the App; `mlflow.langchain.autolog()` emits traces; `setup_mlflow_git_based_version_tracking()` versions deploys.

**Tech Stack:** FastAPI + `mlflow.genai.agent_server`, LangGraph + `langgraph.checkpoint.postgres.PostgresSaver`, `psycopg[binary]` + `psycopg_pool`, Lakebase Postgres (SP OAuth via `WorkspaceClient`), MLflow 3.0+ (`mlflow.langchain.autolog`, `mlflow.log_feedback`, `mlflow.genai.evaluate` + `ConversationSimulator`), Databricks Asset Bundles, React 18 + MUI (existing).

**Spec:** `docs/superpowers/specs/2026-06-04-agents-as-apps-memory-feedback-design.md`

---

## File structure

| Path | Status | Responsibility |
|---|---|---|
| `databricks.yml` | NEW | DAB root: bundle name, variables, App + experiment + job resources, dev/prod targets |
| `app.yaml` | MODIFY | App command updated to `["uv", "run", "start-app"]`; env vars for MLflow + Lakebase |
| `pyproject.toml` | MODIFY | Add `mlflow>=3.0`, `databricks-agents>=1.0`, `databricks-langchain`, `langgraph`, `langgraph-checkpoint-postgres`, `psycopg[binary]`, `psycopg_pool`. Add `[project.scripts] start-app = "agent_server.start_server:main"` |
| `agent_server/__init__.py` | NEW | Empty (package marker) |
| `agent_server/utils.py` | NEW | `get_user_email(request) -> str`, `get_session_id(request) -> str | None` |
| `agent_server/memory.py` | NEW | `get_pg_connection_string()` (mints SP OAuth token), `get_checkpointer() -> PostgresSaver` (singleton with token refresh) |
| `agent_server/agent.py` | NEW | `mlflow.langchain.autolog()`; builds LangGraph ReAct agent; `@invoke()` and `@stream()` handlers |
| `agent_server/personas.py` | NEW | FSISIM eval personas (list of dicts) |
| `agent_server/evaluate_agent.py` | NEW | `evaluate()` function that runs `mlflow.genai.evaluate` against personas |
| `agent_server/routes.py` | NEW | FastAPI routes: `GET /api/threads`, `GET /api/threads/{id}`, `POST /api/chat`, `POST /api/feedback`. `GET /api/manuals/{filename}` moves here from `app/backend/main.py` |
| `agent_server/start_server.py` | NEW | `AgentServer("ResponsesAgent", enable_chat_proxy=False)`, mounts `routes.router`, mounts `app/frontend/dist/` as static, `setup_mlflow_git_based_version_tracking()`, `main()` entrypoint |
| `scripts/__init__.py` | NEW | Empty |
| `scripts/grant_lakebase_permissions.py` | NEW (from template) | Grant app SP permissions on Lakebase memory + custom schema |
| `scripts/init_lakebase_schema.py` | NEW | `CREATE SCHEMA agent_server; CREATE TABLE agent_server.message_feedback ...` (idempotent) |
| `scripts/run_eval.py` | NEW | DAB job entrypoint; loads personas file path from argv; calls `evaluate_agent.evaluate()` |
| `scripts/smoke.py` | NEW | Post-deploy smoke test |
| `tests/test_routes.py` | NEW | Pytest unit tests for routes (mocked agent + Lakebase) |
| `tests/test_memory.py` | NEW | Pytest unit tests for memory helpers (mocked Workspace SDK) |
| `tests/test_personas.py` | NEW | Sanity check: each persona has required keys + non-empty values |
| `app/frontend/src/components/LeftRail.tsx` | MODIFY | Thread list with "New chat" button, calls `GET /api/threads` |
| `app/frontend/src/components/MessageBubble.tsx` | MODIFY | Thumbs up/down icons on assistant bubbles |
| `app/frontend/src/components/ChatThread.tsx` | MODIFY | Accept `threadId` prop, load via `GET /api/threads/{id}`, pass thread_id on chat POST |
| `app/frontend/src/App.tsx` | MODIFY | Manage `threadId` state, wire LeftRail's onClick to setThreadId |
| `app/frontend/src/api/chat.ts` | MODIFY | Add `listThreads()`, `getThread(id)`, `postFeedback(message_id, rating)` |
| `agent/` | DELETE | Migrated into `agent_server/` |
| `app/backend/` | DELETE | `main.py` routes migrated to `agent_server/routes.py`; `agent_client.py` no longer needed |
| `tests/test_agent_*.py`, `tests/test_config.py` | UPDATE | Re-target tests to new module paths |
| `README.md` | MODIFY | Replace Quickstart section with `databricks bundle deploy` flow |
| `CLAUDE.md` | MODIFY | Note: agent runs in-process via Agents as Apps; one-source-of-truth still `config.py` |

---

## Task list

### Task 1: Add new dependencies to pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update pyproject.toml dependencies**

Replace the `dependencies = [...]` array with:

```toml
dependencies = [
  "databricks-sdk>=0.30.0",
  "databricks-vectorsearch>=0.40",
  "databricks-agents>=1.0.0",
  "databricks-langchain>=0.19.0",
  "langgraph>=1.2.0",
  "langgraph-checkpoint-postgres>=2.0.0",
  "langchain-classic>=1.0.0",
  "langchain-core>=1.4.0",
  "mlflow>=3.0.0",
  "psycopg[binary]>=3.2.0",
  "psycopg_pool>=3.2.0",
  "pyspark>=3.5.0",
  "pyarrow>=15.0.0",
  "weasyprint>=62.3",
  "markdown>=3.6",
  "fastapi>=0.115.0",
  "uvicorn>=0.32.0",
  "pydantic>=2.9.0",
  "python-dotenv>=1.0.1",
  "httpx>=0.27.0",
]
```

Add a `[project.scripts]` section below `[project.optional-dependencies]`:

```toml
[project.scripts]
start-app = "agent_server.start_server:main"
```

- [ ] **Step 2: Verify pyproject parses**

Run: `python -c "import tomllib; tomllib.loads(open('pyproject.toml','rb').read().decode())"`
Expected: no output (success). Error means TOML syntax issue.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore(deps): add Agents-as-Apps + LangGraph PostgresSaver deps"
```

---

### Task 2: Scaffold the agent_server package

**Files:**
- Create: `agent_server/__init__.py`
- Create: `agent_server/utils.py`
- Create: `tests/test_utils.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_utils.py`:

```python
"""Tests for agent_server.utils — identity and session helpers."""
from unittest.mock import MagicMock

from agent_server.utils import get_user_email, get_session_id


def test_get_user_email_reads_forwarded_header():
    request = MagicMock()
    request.headers = {"X-Forwarded-Email": "tech@flightsafety.com"}
    assert get_user_email(request) == "tech@flightsafety.com"


def test_get_user_email_returns_none_when_missing():
    request = MagicMock()
    request.headers = {}
    assert get_user_email(request) is None


def test_get_session_id_reads_custom_inputs():
    req = MagicMock()
    req.custom_inputs = {"thread_id": "abc-123"}
    assert get_session_id(req) == "abc-123"


def test_get_session_id_returns_none_when_missing():
    req = MagicMock()
    req.custom_inputs = {}
    assert get_session_id(req) is None


def test_get_session_id_handles_none_custom_inputs():
    req = MagicMock()
    req.custom_inputs = None
    assert get_session_id(req) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_utils.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent_server'`

- [ ] **Step 3: Create the package + utils**

Create `agent_server/__init__.py` (empty file).

Create `agent_server/utils.py`:

```python
"""Identity + session helpers for the FSISIM Agents-as-Apps server."""
from __future__ import annotations
from typing import Any


def get_user_email(request: Any) -> str | None:
    """Pull the authenticated user's email from the X-Forwarded-Email header.

    Databricks Apps inject this header on every request after SSO. Returns None
    when the header is absent (local dev without the App proxy).
    """
    headers = getattr(request, "headers", {}) or {}
    return headers.get("X-Forwarded-Email")


def get_session_id(request: Any) -> str | None:
    """Read the thread_id out of the ResponsesAgentRequest custom_inputs dict.

    Used by @invoke to tag the MLflow trace with the conversation thread.
    Returns None when the caller did not provide a thread_id.
    """
    custom = getattr(request, "custom_inputs", None) or {}
    return custom.get("thread_id")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_utils.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add agent_server/__init__.py agent_server/utils.py tests/test_utils.py
git commit -m "feat(agent_server): scaffold package with identity + session helpers"
```

---

### Task 3: Lakebase connection helper with SP OAuth + token refresh

**Files:**
- Create: `agent_server/memory.py`
- Create: `tests/test_memory.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_memory.py`:

```python
"""Tests for agent_server.memory — Lakebase connection string + token refresh."""
import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("LAKEBASE_INSTANCE_NAME", "fsisim-poc")
    monkeypatch.setenv("LAKEBASE_DATABASE_NAME", "fsisim_chat")
    return monkeypatch


def test_get_pg_connection_string_uses_sdk_to_mint_token(env):
    """Returns a libpq-compatible URI with the freshly-minted OAuth password."""
    from agent_server import memory

    fake_cred = MagicMock()
    fake_cred.token = "oauth-token-xyz"
    fake_instance = MagicMock()
    fake_instance.read_write_dns = "instance.cloud.databricks.com"
    fake_instance.name = "fsisim-poc"

    fake_w = MagicMock()
    fake_w.database.get_database_instance.return_value = fake_instance
    fake_w.database.generate_database_credential.return_value = fake_cred
    fake_w.current_user.me.return_value.user_name = "app-sp@example.com"

    with patch("agent_server.memory.WorkspaceClient", return_value=fake_w):
        uri = memory.get_pg_connection_string()

    assert "instance.cloud.databricks.com" in uri
    assert "oauth-token-xyz" in uri
    assert "fsisim_chat" in uri
    assert "sslmode=require" in uri


def test_get_pg_connection_string_raises_without_env(monkeypatch):
    monkeypatch.delenv("LAKEBASE_INSTANCE_NAME", raising=False)
    from agent_server import memory
    importlib_reload(memory)
    with pytest.raises(RuntimeError, match="LAKEBASE_INSTANCE_NAME"):
        memory.get_pg_connection_string()


def importlib_reload(mod):
    import importlib
    importlib.reload(mod)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_memory.py -v`
Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Create the memory module**

Create `agent_server/memory.py`:

```python
"""Lakebase Postgres helpers for the FSISIM agent.

Mints SP-scoped OAuth tokens via the Databricks SDK and exposes:
- `get_pg_connection_string()` — libpq URI for ad-hoc psycopg connections
- `get_checkpointer()` — LangGraph PostgresSaver singleton with token refresh

The OAuth token lasts ~60 minutes. We cache for 50 minutes then re-mint.
"""
from __future__ import annotations
import os
import threading
import time
import urllib.parse
from typing import Any

_TOKEN_CACHE: dict[str, Any] = {"token": None, "expires_at": 0.0, "host": None, "user": None}
_TOKEN_LOCK = threading.Lock()
_TOKEN_TTL_SECONDS = 50 * 60  # refresh 10 min before the 60-min expiry


def _mint_credentials() -> dict[str, str]:
    """Refresh the cached Lakebase credentials. Caller holds _TOKEN_LOCK."""
    from databricks.sdk import WorkspaceClient

    instance_name = os.environ.get("LAKEBASE_INSTANCE_NAME")
    if not instance_name:
        raise RuntimeError("LAKEBASE_INSTANCE_NAME env var is required")

    w = WorkspaceClient()
    instance = w.database.get_database_instance(name=instance_name)
    cred = w.database.generate_database_credential(
        request_id=f"fsisim-{int(time.time())}",
        instance_names=[instance_name],
    )
    me = w.current_user.me()

    return {
        "host": instance.read_write_dns,
        "user": me.user_name,
        "token": cred.token,
    }


def _get_credentials() -> dict[str, str]:
    """Return cached or freshly-minted credentials (thread-safe)."""
    now = time.time()
    if _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["expires_at"]:
        return {
            "host": _TOKEN_CACHE["host"],
            "user": _TOKEN_CACHE["user"],
            "token": _TOKEN_CACHE["token"],
        }
    with _TOKEN_LOCK:
        # Re-check after acquiring the lock to avoid double-mint.
        if _TOKEN_CACHE["token"] and time.time() < _TOKEN_CACHE["expires_at"]:
            return {
                "host": _TOKEN_CACHE["host"],
                "user": _TOKEN_CACHE["user"],
                "token": _TOKEN_CACHE["token"],
            }
        fresh = _mint_credentials()
        _TOKEN_CACHE.update(fresh)
        _TOKEN_CACHE["expires_at"] = time.time() + _TOKEN_TTL_SECONDS
        return fresh


def get_pg_connection_string() -> str:
    """Return a libpq-compatible postgresql:// URI for the Lakebase instance."""
    db_name = os.environ.get("LAKEBASE_DATABASE_NAME", "fsisim_chat")
    creds = _get_credentials()
    user = urllib.parse.quote(creds["user"], safe="")
    token = urllib.parse.quote(creds["token"], safe="")
    host = creds["host"]
    return f"postgresql://{user}:{token}@{host}:5432/{db_name}?sslmode=require"


_CHECKPOINTER: Any = None


def get_checkpointer():
    """Return a LangGraph PostgresSaver bound to Lakebase.

    Lazily constructs and caches the saver. The underlying connection pool
    re-resolves the OAuth token on each new connection, so token expiry is
    handled transparently as long as the pool recycles connections.
    """
    global _CHECKPOINTER
    if _CHECKPOINTER is not None:
        return _CHECKPOINTER

    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg_pool import ConnectionPool

    def _connect():
        return get_pg_connection_string()

    pool = ConnectionPool(
        conninfo=get_pg_connection_string(),
        min_size=1,
        max_size=4,
        kwargs={"autocommit": True, "prepare_threshold": 0},
        configure=lambda conn: None,
        reconnect_failed=lambda pool: None,
    )
    saver = PostgresSaver(pool)
    saver.setup()  # idempotent; creates checkpoint tables on first run
    _CHECKPOINTER = saver
    return _CHECKPOINTER
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_memory.py -v`
Expected: 2 passed.

If `get_pg_connection_string_raises_without_env` fails because the cache survives across tests, add `monkeypatch.setattr(memory, "_TOKEN_CACHE", {"token": None, "expires_at": 0.0, "host": None, "user": None})` to that test.

- [ ] **Step 5: Commit**

```bash
git add agent_server/memory.py tests/test_memory.py
git commit -m "feat(agent_server): Lakebase connection + LangGraph PostgresSaver factory"
```

---

### Task 4: Adapt the LangGraph agent into `agent_server/agent.py` with `@invoke`/`@stream`

**Files:**
- Create: `agent_server/agent.py`
- Create: `tests/test_agent_module.py`
- Reference for migration: `agent/agent.py` (existing), `agent/prompts.py` (existing)

- [ ] **Step 1: Write the failing test**

Create `tests/test_agent_module.py`:

```python
"""Tests that agent_server.agent exposes a working invoke handler."""
from unittest.mock import MagicMock, patch

import pytest


def test_build_agent_config_returns_required_keys():
    """The config dict must include llm_endpoint, uc_functions, system_prompt."""
    from agent_server import agent

    cfg = agent.build_agent_config()
    assert "llm_endpoint" in cfg
    assert "uc_functions" in cfg
    assert "system_prompt" in cfg
    assert isinstance(cfg["uc_functions"], list)
    assert len(cfg["uc_functions"]) == 2  # search_past_issues + search_technical_manuals


def test_agent_module_registers_autolog():
    """Importing agent should trigger mlflow.langchain.autolog (or noop in test env)."""
    # This test confirms the module imports without ImportError when LangGraph deps
    # are absent; in production they'd be present.
    from agent_server import agent  # noqa: F401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent_module.py -v`
Expected: FAIL — `agent_server.agent` does not exist.

- [ ] **Step 3: Create the agent module**

Create `agent_server/agent.py`:

```python
"""FSISIM agent: LangGraph ReAct + Lakebase memory, exposed via @invoke / @stream.

Module-level side effects on import (intentional; matches the template):
- mlflow.langchain.autolog() so every LangGraph call emits an MLflow trace
- @invoke / @stream decorators register the handlers with the AgentServer

The LangGraph graph itself is rebuilt per request to attach the right
checkpoint thread; the underlying ChatDatabricks + UC toolkit are cached.
"""
from __future__ import annotations
import logging
from typing import Any, AsyncGenerator

from config import Config

logger = logging.getLogger(__name__)

try:
    from agent_server.prompts import SYSTEM_PROMPT
except ModuleNotFoundError:
    # Fallback: load from the legacy agent/ path during migration
    from agent.prompts import SYSTEM_PROMPT  # type: ignore


def build_agent_config() -> dict[str, Any]:
    """Return the agent configuration dict derived from Config + env vars."""
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
        from mlflow.genai.agent_server import invoke  # noqa: F401
    except Exception:
        return False
    return True


# Module-level cache: ChatDatabricks + tools are heavy to construct.
_LLM = None
_TOOLS = None


def _build_llm_and_tools():
    """Build the LLM client and UC function tools once; cache for reuse."""
    global _LLM, _TOOLS
    if _LLM is not None and _TOOLS is not None:
        return _LLM, _TOOLS

    from databricks_langchain import ChatDatabricks
    from databricks_langchain.uc_ai import UCFunctionToolkit
    from unitycatalog.ai.core.databricks import DatabricksFunctionClient

    ac = build_agent_config()
    _LLM = ChatDatabricks(endpoint=ac["llm_endpoint"])
    try:
        client = DatabricksFunctionClient(execution_mode="serverless")
    except Exception:
        client = DatabricksFunctionClient(execution_mode="local")
    tk = UCFunctionToolkit(
        function_names=[fn["name"] for fn in ac["uc_functions"]],
        client=client,
    )
    _TOOLS = tk.tools
    return _LLM, _TOOLS


def _build_graph_for_thread(thread_id: str):
    """Construct a LangGraph ReAct agent attached to the Lakebase checkpoint
    for `thread_id`. The graph is cheap to build; the LLM + tools are cached.
    """
    from agent_server.memory import get_checkpointer
    from langgraph.prebuilt import create_react_agent

    ac = build_agent_config()
    llm, tools = _build_llm_and_tools()
    saver = get_checkpointer()
    return create_react_agent(llm, tools, prompt=ac["system_prompt"], checkpointer=saver)


if _can_build():
    import mlflow
    from mlflow.genai.agent_server import invoke, stream
    from mlflow.types.responses import (
        ResponsesAgentRequest,
        ResponsesAgentResponse,
        ResponsesAgentStreamEvent,
    )

    mlflow.langchain.autolog()
    logging.getLogger("mlflow.utils.autologging_utils").setLevel(logging.ERROR)

    from agent_server.utils import get_session_id

    def _to_langchain(items):
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
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

    @invoke()
    def invoke_handler(request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        """Synchronous chat handler.

        Reads thread_id from custom_inputs, tags the MLflow trace with it,
        runs the LangGraph ReAct agent, and returns the final assistant turn.
        LangGraph's PostgresSaver persists the conversation state.
        """
        thread_id = get_session_id(request) or "default"
        mlflow.update_current_trace(
            metadata={"mlflow.trace.session": thread_id},
        )
        graph = _build_graph_for_thread(thread_id)
        messages = _to_langchain(request.input)
        result = graph.invoke(
            {"messages": messages},
            config={"configurable": {"thread_id": thread_id}},
        )
        final = result["messages"][-1]
        from mlflow.types.responses import ResponsesAgentResponse  # local import for clarity
        # The @invoke decorator's wrapper exposes create_text_output_item via
        # the request context; use the static helper here to keep it simple.
        return ResponsesAgentResponse(
            output=[{"type": "message", "id": "msg-final",
                      "content": [{"type": "output_text", "text": str(final.content)}]}]
        )

    @stream()
    async def stream_handler(
        request: ResponsesAgentRequest,
    ) -> AsyncGenerator[ResponsesAgentStreamEvent, None]:
        """Streaming handler — registered for future use by the React UI.

        v1 React client doesn't consume the stream; we expose it so future
        work can switch without redeploying the agent.
        """
        thread_id = get_session_id(request) or "default"
        mlflow.update_current_trace(
            metadata={"mlflow.trace.session": thread_id},
        )
        graph = _build_graph_for_thread(thread_id)
        messages = _to_langchain(request.input)
        counter = 0
        for event in graph.stream(
            {"messages": messages},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="updates",
        ):
            for _, node_state in event.items():
                for msg in node_state.get("messages", []) or []:
                    if getattr(msg, "content", None):
                        counter += 1
                        yield ResponsesAgentStreamEvent(
                            type="response.output_item.done",
                            item={
                                "type": "message",
                                "id": f"msg-{counter}",
                                "content": [{"type": "output_text", "text": str(msg.content)}],
                            },
                        )
```

- [ ] **Step 4: Move the system prompt into agent_server/**

Run:

```bash
git mv agent/prompts.py agent_server/prompts.py
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_agent_module.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add agent_server/agent.py agent_server/prompts.py tests/test_agent_module.py
git rm agent/prompts.py
git commit -m "feat(agent_server): LangGraph + Lakebase agent with @invoke/@stream"
```

---

### Task 5: FSISIM eval personas

**Files:**
- Create: `agent_server/personas.py`
- Create: `tests/test_personas.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_personas.py`:

```python
"""Sanity checks on the FSISIM eval personas."""
from agent_server import personas


def test_personas_is_a_nonempty_list():
    assert isinstance(personas.PERSONAS, list)
    assert len(personas.PERSONAS) >= 5


def test_each_persona_has_required_keys():
    for p in personas.PERSONAS:
        assert "goal" in p and p["goal"]
        assert "persona" in p and p["persona"]
        assert "simulation_guidelines" in p
        assert isinstance(p["simulation_guidelines"], list)


def test_personas_cover_fsisim_domains():
    """At least one persona per major FSISIM system."""
    goals = " ".join(p["goal"].lower() for p in personas.PERSONAS)
    for domain in ["hydraulic", "motion", "visual", "fms", "connector"]:
        assert domain in goals, f"no persona for {domain}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_personas.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Create the personas file**

Create `agent_server/personas.py`:

```python
"""FSISIM eval personas for mlflow.genai.evaluate's ConversationSimulator.

Each persona drives a multi-turn simulated conversation. The simulator picks
turns based on `goal` (what the user wants) and `persona` (how they talk);
`simulation_guidelines` shape pacing and follow-up behavior.

Replace this file (or override via the eval_personas_file DAB variable) when
adapting to a different fleet / customer.
"""

PERSONAS: list[dict] = [
    {
        "goal": "Diagnose a hydraulic pressure drop on a G001 simulator during takeoff",
        "persona": (
            "A first-year FSISIM technician with mechanical aptitude but limited "
            "exposure to the G001 platform. Comfortable reading procedures, less "
            "comfortable interpreting raw fault codes."
        ),
        "simulation_guidelines": [
            "Start with a vague symptom report before asking for specific diagnostics.",
            "Ask follow-up questions about whether similar past issues exist before accepting a recommendation.",
        ],
    },
    {
        "goal": "Resolve a motion platform fault code 47B on G001-SIM-03",
        "persona": (
            "A senior technician who knows the motion subsystem well but wants to "
            "validate the AI's recommendation against prior issues before acting."
        ),
        "simulation_guidelines": [
            "Push back on the first answer and ask for cited past issues.",
            "Prefer concise responses; flag any answer over 5 sentences.",
        ],
    },
    {
        "goal": "Investigate visual database corruption at KJFK approach",
        "persona": (
            "A visual systems specialist troubleshooting reports of glitches on the "
            "KJFK approach scene; wants both prior-issue context and manual references."
        ),
        "simulation_guidelines": [
            "Ask whether the issue is on a specific runway or scene-wide.",
            "Request a manual page citation, not just a summary.",
        ],
    },
    {
        "goal": "Understand what FMS VNAV means in the context of G001 sims",
        "persona": (
            "A new hire from a non-aviation background; encountered FMS VNAV in a "
            "ticket and needs the term explained in technician-friendly language."
        ),
        "simulation_guidelines": [
            "Avoid asking about specific fault codes; focus on concept clarification.",
            "Confirm understanding by asking for a real-world example.",
        ],
    },
    {
        "goal": "Find the documented procedure for reseating a hydraulic connector",
        "persona": (
            "An experienced FSISIM tech who wants the exact manual procedure rather "
            "than improvising; will reject AI-invented steps."
        ),
        "simulation_guidelines": [
            "Demand a specific manual + page number citation.",
            "If the AI tries to summarize a procedure without citing the manual, push back.",
        ],
    },
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_personas.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add agent_server/personas.py tests/test_personas.py
git commit -m "feat(eval): FSISIM personas for mlflow.genai.evaluate"
```

---

### Task 6: Eval harness wrapper

**Files:**
- Create: `agent_server/evaluate_agent.py`

- [ ] **Step 1: Create the eval module**

Create `agent_server/evaluate_agent.py`:

```python
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


if __name__ == "__main__":
    evaluate()
```

- [ ] **Step 2: Smoke-import test**

Run: `python -c "from agent_server import evaluate_agent; print(evaluate_agent.evaluate.__doc__)"`
Expected: prints the docstring (no ImportError).

Note: actual evaluation requires the deployed app + an MLflow experiment + Lakebase access; only the import contract is verified locally.

- [ ] **Step 3: Commit**

```bash
git add agent_server/evaluate_agent.py
git commit -m "feat(eval): mlflow.genai.evaluate harness using FSISIM personas"
```

---

### Task 7: Lakebase schema init script

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/init_lakebase_schema.py`

- [ ] **Step 1: Create the script**

Create `scripts/__init__.py` (empty).

Create `scripts/init_lakebase_schema.py`:

```python
"""Create the agent_server schema + message_feedback table in Lakebase.

Idempotent. Run once after the first bundle deploy (or any time the schema
needs to be re-applied after a Lakebase restore).

Usage:
    uv run python -m scripts.init_lakebase_schema
"""
from __future__ import annotations
import logging
import sys

import psycopg

from agent_server.memory import get_pg_connection_string

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


DDL = """
CREATE SCHEMA IF NOT EXISTS agent_server;

CREATE TABLE IF NOT EXISTS agent_server.message_feedback (
  message_id      text PRIMARY KEY,
  rating          text NOT NULL CHECK (rating IN ('up','down')),
  comment         text,
  user_email      text NOT NULL,
  mlflow_trace_id text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS message_feedback_user_idx
  ON agent_server.message_feedback(user_email, created_at DESC);
"""


def main() -> int:
    uri = get_pg_connection_string()
    log.info("Connecting to Lakebase...")
    with psycopg.connect(uri, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
    log.info("Schema applied OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verify the script imports**

Run: `python -c "from scripts import init_lakebase_schema; print(init_lakebase_schema.DDL[:30])"`
Expected: prints the first 30 chars of the DDL string.

- [ ] **Step 3: Commit**

```bash
git add scripts/__init__.py scripts/init_lakebase_schema.py
git commit -m "feat(scripts): idempotent Lakebase schema init for agent_server.message_feedback"
```

---

### Task 8: Lift grant_lakebase_permissions.py from the template

**Files:**
- Create: `scripts/grant_lakebase_permissions.py`

- [ ] **Step 1: Fetch the template script**

Run:

```bash
curl -fsSL https://raw.githubusercontent.com/databricks/app-templates/main/agent-openai-agents-sdk/scripts/grant_lakebase_permissions.py \
  -o scripts/grant_lakebase_permissions.py
```

- [ ] **Step 2: Add FSISIM extension to grant feedback table**

Open `scripts/grant_lakebase_permissions.py`. Find the `MEMORY_TYPE_SCHEMAS` dict at the top of the file. Locate the entry for `"langgraph"`. Replace it with:

```python
    "langgraph": {
        MEMORY_SCHEMA: [
            "checkpoint_migrations",
            "checkpoint_writes",
            "checkpoints",
            "checkpoint_blobs",
            "store_migrations",
            "store",
            "store_vectors",
            "vector_migrations",
        ],
        "agent_server": [
            "responses",
            "messages",
            "message_feedback",  # FSISIM-added; created by scripts/init_lakebase_schema.py
        ],
    },
```

- [ ] **Step 3: Verify imports**

Run: `python -c "import scripts.grant_lakebase_permissions"`
Expected: no output (if dotenv isn't installed locally, the script imports may error — install `python-dotenv` first via `uv pip install python-dotenv`).

- [ ] **Step 4: Commit**

```bash
git add scripts/grant_lakebase_permissions.py
git commit -m "chore(scripts): lift grant_lakebase_permissions from template + add feedback table"
```

---

### Task 9: PDF route migration into agent_server/routes.py

**Files:**
- Create: `agent_server/routes.py`
- Create: `tests/test_routes.py`
- Reference: `app/backend/main.py` (will be deleted later)

- [ ] **Step 1: Write the failing test for the manuals route**

Create `tests/test_routes.py`:

```python
"""Unit tests for agent_server.routes — FastAPI endpoints."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from agent_server.routes import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_health_returns_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_manuals_rejects_invalid_filename(client):
    r = client.get("/api/manuals/..%2Fevil.pdf")
    # Either route mismatch (404) or invalid-filename guard (400):
    assert r.status_code in (400, 404)


def test_manuals_rejects_non_pdf(client):
    r = client.get("/api/manuals/notes.txt")
    assert r.status_code == 400
    assert "Invalid filename" in r.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_routes.py -v`
Expected: FAIL — `agent_server.routes` does not exist.

- [ ] **Step 3: Create the routes module with health + manuals**

Create `agent_server/routes.py`:

```python
"""FastAPI router for FSISIM custom endpoints.

Mounted by agent_server/start_server.py onto the AgentServer's FastAPI app.

Endpoints:
- GET  /api/health             — liveness
- GET  /api/manuals/{filename} — proxy UC Volume PDFs (migrated from app/backend/main.py)
- GET  /api/_diag              — SP volume listing (migrated)
- POST /api/chat               — added in Task 11
- GET  /api/threads            — added in Task 10
- GET  /api/threads/{id}       — added in Task 10
- POST /api/feedback           — added in Task 12
"""
from __future__ import annotations
import os
import urllib.parse

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse, Response

import httpx

router = APIRouter()


CATALOG = os.environ.get("FSISIM_CATALOG", "jdub_demo")
SCHEMA = os.environ.get("FSISIM_SCHEMA", "fsisim_issue_ai_gold")
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/manuals"


def _allowed_filename(name: str) -> bool:
    return name.endswith(".pdf") and "/" not in name and ".." not in name


_W = None


def _get_w():
    global _W
    if _W is None:
        from databricks.sdk import WorkspaceClient
        _W = WorkspaceClient()
    return _W


@router.get("/api/health")
async def health():
    return {"ok": True}


@router.get("/api/manuals/{filename}")
async def manual(filename: str):
    """Return a manual PDF from the UC volume. text/plain on errors."""
    if not _allowed_filename(filename):
        return PlainTextResponse("Invalid filename", status_code=400)
    path = f"{VOLUME_PATH}/{filename}"
    w = _get_w()
    encoded_path = urllib.parse.quote(path)
    url = f"{w.config.host}/api/2.0/fs/files{encoded_path}"
    try:
        auth_headers = w.config.authenticate()
    except Exception as e:
        return PlainTextResponse(
            f"SDK auth failed: {type(e).__name__}: {e}", status_code=500
        )
    headers = {**auth_headers, "Accept": "application/octet-stream"}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url, headers=headers)
    except Exception as e:
        return PlainTextResponse(
            f"httpx fetch failed: {type(e).__name__}: {e}", status_code=502
        )
    ct = r.headers.get("content-type", "")
    if r.status_code != 200:
        body_preview = r.text[:400] if "text" in ct or "json" in ct else f"<{len(r.content)} bytes>"
        return PlainTextResponse(
            f"Files API {r.status_code} from {url}\n\n{body_preview}",
            status_code=r.status_code,
        )
    if not r.content.startswith(b"%PDF"):
        return PlainTextResponse(
            f"Files API returned non-PDF bytes (ct={ct}, len={len(r.content)}):\n\n{r.text[:400]}",
            status_code=502,
        )
    return Response(
        content=r.content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/api/_diag")
async def diag():
    out: dict = {"volume_path": VOLUME_PATH, "ok": False, "items": [], "error": None}
    try:
        w = _get_w()
        items = list(w.files.list_directory_contents(VOLUME_PATH))
        out["items"] = [
            {"name": it.name, "size": it.file_size, "is_dir": it.is_directory}
            for it in items
        ]
        out["ok"] = True
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    return JSONResponse(out)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_routes.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add agent_server/routes.py tests/test_routes.py
git commit -m "feat(routes): migrate /api/health, /api/manuals, /api/_diag into agent_server"
```

---

### Task 10: Thread list + thread detail routes (Lakebase read)

**Files:**
- Modify: `agent_server/routes.py`
- Modify: `tests/test_routes.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_routes.py`:

```python
def test_threads_list_requires_email_header(client):
    r = client.get("/api/threads")
    assert r.status_code == 401


def test_threads_list_returns_user_threads(client, monkeypatch):
    """GET /api/threads filters by X-Forwarded-Email and returns title + updated_at."""
    fake_rows = [
        {"thread_id": "t1", "title": "Hydraulic drop", "updated_at": "2026-06-04T15:00:00+00:00"},
        {"thread_id": "t2", "title": "Motion 47B",      "updated_at": "2026-06-03T10:00:00+00:00"},
    ]
    with patch("agent_server.routes._fetch_user_threads", return_value=fake_rows):
        r = client.get("/api/threads", headers={"X-Forwarded-Email": "tech@flightsafety.com"})
    assert r.status_code == 200
    body = r.json()
    assert body["threads"] == fake_rows


def test_thread_detail_returns_messages(client):
    fake_messages = [
        {"id": "m1", "role": "user", "content": "Hello", "created_at": "..."},
        {"id": "m2", "role": "assistant", "content": "Hi", "created_at": "...",
         "mlflow_trace_id": "tr-1"},
    ]
    with patch("agent_server.routes._fetch_thread_messages", return_value=fake_messages):
        r = client.get(
            "/api/threads/t1",
            headers={"X-Forwarded-Email": "tech@flightsafety.com"},
        )
    assert r.status_code == 200
    assert r.json()["messages"] == fake_messages


def test_thread_detail_rejects_other_user(client):
    """A thread belonging to user A must not be readable by user B."""
    with patch("agent_server.routes._fetch_thread_owner", return_value="otheruser@example.com"):
        r = client.get(
            "/api/threads/t1",
            headers={"X-Forwarded-Email": "tech@flightsafety.com"},
        )
    assert r.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_routes.py -v`
Expected: 4 new tests FAIL (functions don't exist).

- [ ] **Step 3: Implement the routes + Lakebase helpers**

Append to `agent_server/routes.py`:

```python
from fastapi import HTTPException, Request

from agent_server.utils import get_user_email


def _fetch_user_threads(user_email: str) -> list[dict]:
    """Read the 10 most-recent threads for this user from agent_server.messages.

    AgentServer's `messages` table doesn't have an explicit `thread_id` column
    in every schema; the session id is stored in `messages.session_id`. We
    derive (thread_id, title, updated_at) by aggregating over session_id.
    """
    import psycopg
    from agent_server.memory import get_pg_connection_string

    sql = """
        SELECT
            m.session_id        AS thread_id,
            -- Title = first user turn's content, truncated; fallback to thread id
            COALESCE(
              substring(
                (SELECT content FROM agent_server.messages mm
                 WHERE mm.session_id = m.session_id AND mm.role = 'user'
                 ORDER BY mm.created_at ASC LIMIT 1)
                FROM 1 FOR 60),
              m.session_id
            ) AS title,
            MAX(m.created_at)    AS updated_at
        FROM agent_server.messages m
        WHERE m.user_email = %s
        GROUP BY m.session_id
        ORDER BY updated_at DESC
        LIMIT 10
    """
    with psycopg.connect(get_pg_connection_string(), autocommit=True) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(sql, (user_email,))
            rows = cur.fetchall()
    for r in rows:
        if r.get("updated_at") is not None:
            r["updated_at"] = r["updated_at"].isoformat()
    return rows


def _fetch_thread_owner(thread_id: str) -> str | None:
    import psycopg
    from agent_server.memory import get_pg_connection_string
    with psycopg.connect(get_pg_connection_string(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_email FROM agent_server.messages WHERE session_id = %s LIMIT 1",
                (thread_id,),
            )
            row = cur.fetchone()
    return row[0] if row else None


def _fetch_thread_messages(thread_id: str) -> list[dict]:
    import psycopg
    from agent_server.memory import get_pg_connection_string
    sql = """
        SELECT
            id, role, content, created_at,
            mlflow_trace_id
        FROM agent_server.messages
        WHERE session_id = %s
        ORDER BY created_at ASC
    """
    with psycopg.connect(get_pg_connection_string(), autocommit=True) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(sql, (thread_id,))
            rows = cur.fetchall()
    for r in rows:
        if r.get("created_at") is not None:
            r["created_at"] = r["created_at"].isoformat()
    return rows


@router.get("/api/threads")
async def list_threads(request: Request):
    email = get_user_email(request)
    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")
    return {"threads": _fetch_user_threads(email)}


@router.get("/api/threads/{thread_id}")
async def get_thread(thread_id: str, request: Request):
    email = get_user_email(request)
    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")
    owner = _fetch_thread_owner(thread_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    if owner != email:
        raise HTTPException(status_code=403, detail="Not your thread")
    return {"thread_id": thread_id, "messages": _fetch_thread_messages(thread_id)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_routes.py -v`
Expected: 7 passed (3 from Task 9 + 4 new).

- [ ] **Step 5: Commit**

```bash
git add agent_server/routes.py tests/test_routes.py
git commit -m "feat(routes): GET /api/threads + /api/threads/{id} with ownership checks"
```

---

### Task 11: POST /api/chat — bridge to the @invoke handler

**Files:**
- Modify: `agent_server/routes.py`
- Modify: `tests/test_routes.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_routes.py`:

```python
def test_chat_requires_email_header(client):
    r = client.post("/api/chat", json={"content": "hello"})
    assert r.status_code == 401


def test_chat_invokes_agent_and_returns_text(client):
    """POST /api/chat passes thread_id + user to the agent and returns text + ids."""
    from mlflow.types.responses import ResponsesAgentResponse

    fake_response = ResponsesAgentResponse(
        output=[{"type": "message", "id": "assistant-msg-1",
                  "content": [{"type": "output_text", "text": "Resolved."}]}],
    )

    with patch("agent_server.routes._call_invoke", return_value=fake_response) as m:
        with patch("agent_server.routes._reissue_citations",
                   return_value={"manual_citations": [], "issue_citations": []}):
            r = client.post(
                "/api/chat",
                headers={"X-Forwarded-Email": "tech@flightsafety.com"},
                json={"thread_id": "abc-123", "content": "hydraulic drop?"},
            )

    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "Resolved."
    assert body["thread_id"] == "abc-123"
    assert "assistant_message_id" in body
    # The handler must have passed thread_id through custom_inputs:
    request_arg = m.call_args[0][0]
    assert request_arg.custom_inputs["thread_id"] == "abc-123"


def test_chat_mints_thread_id_when_missing(client):
    from mlflow.types.responses import ResponsesAgentResponse
    fake = ResponsesAgentResponse(
        output=[{"type": "message", "id": "x",
                  "content": [{"type": "output_text", "text": "ok"}]}],
    )
    with patch("agent_server.routes._call_invoke", return_value=fake):
        with patch("agent_server.routes._reissue_citations",
                   return_value={"manual_citations": [], "issue_citations": []}):
            r = client.post(
                "/api/chat",
                headers={"X-Forwarded-Email": "tech@flightsafety.com"},
                json={"content": "hello"},
            )
    assert r.status_code == 200
    body = r.json()
    assert body["thread_id"]  # non-empty
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_routes.py -v`
Expected: 3 new FAIL.

- [ ] **Step 3: Implement /api/chat**

Append to `agent_server/routes.py`:

```python
import uuid

from pydantic import BaseModel
from mlflow.types.responses import ResponsesAgentRequest


class ChatRequest(BaseModel):
    content: str
    thread_id: str | None = None


def _call_invoke(req: ResponsesAgentRequest):
    """Indirection so tests can mock the in-process @invoke call."""
    from mlflow.genai.agent_server import get_invoke_function
    fn = get_invoke_function()
    if fn is None:
        raise RuntimeError("@invoke handler not registered (agent_server.agent not imported)")
    return fn(req)


def _reissue_citations(user_message: str) -> dict:
    """Re-query VS indexes for manual + issue citations (existing logic).

    Lives in routes.py so the chat response can be assembled in one place.
    Returns {"manual_citations": [...], "issue_citations": [...]}.
    """
    from databricks.sdk import WorkspaceClient
    w = _get_w() if _W is not None else WorkspaceClient()

    cat = os.environ.get("FSISIM_CATALOG", CATALOG)
    schm = os.environ.get("FSISIM_SCHEMA", SCHEMA)
    manual_idx = f"{cat}.{schm}.manual_knowledge_index"
    issue_idx = f"{cat}.{schm}.issue_history_index"

    manual_citations: list[dict] = []
    try:
        ix = w.vector_search_indexes.query_index(
            index_name=manual_idx, query_text=user_message,
            columns=["source_pdf", "page_first", "page_last", "chunk_to_retrieve"],
            num_results=3, query_type="HYBRID",
        )
        for r in (ix.result.data_array if ix.result else []) or []:
            source_pdf = r[0] or ""
            filename = source_pdf.split("/")[-1] if source_pdf else ""
            title = filename.replace(".pdf", "").replace("_", " ").title()
            manual_citations.append({
                "source_pdf": source_pdf, "filename": filename, "title": title,
                "page_first": int(r[1] or 0), "page_last": int(r[2] or 0),
                "preview": (r[3] or "")[:600],
            })
    except Exception:
        pass

    issue_citations: list[dict] = []
    try:
        ix = w.vector_search_indexes.query_index(
            index_name=issue_idx, query_text=user_message,
            columns=["issue_id", "issue_type", "sim_name",
                     "note_type_description", "composite_text"],
            num_results=3, query_type="HYBRID",
        )
        for r in (ix.result.data_array if ix.result else []) or []:
            issue_citations.append({
                "issue_id": int(r[0] or 0),
                "issue_type": r[1] or "",
                "sim_name": r[2] or "",
                "note_type": r[3] or "",
                "preview": (r[4] or "")[:600],
            })
    except Exception:
        pass

    return {"manual_citations": manual_citations, "issue_citations": issue_citations}


@router.post("/api/chat")
async def chat(req: ChatRequest, request: Request):
    email = get_user_email(request)
    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")

    thread_id = req.thread_id or str(uuid.uuid4())

    agent_req = ResponsesAgentRequest(
        input=[{"role": "user", "content": req.content}],
        custom_inputs={"thread_id": thread_id, "user_email": email},
    )

    response = _call_invoke(agent_req)

    text = ""
    assistant_message_id = ""
    for item in response.output:
        if isinstance(item, dict):
            content = item.get("content", [])
            assistant_message_id = item.get("id", assistant_message_id)
        else:
            content = getattr(item, "content", [])
            assistant_message_id = getattr(item, "id", assistant_message_id)
        for part in content:
            ptype = part.get("type") if isinstance(part, dict) else getattr(part, "type", None)
            ptext = part.get("text") if isinstance(part, dict) else getattr(part, "text", None)
            if ptype in ("output_text", "text") and ptext:
                text += ptext

    citations = _reissue_citations(req.content)

    return {
        "thread_id": thread_id,
        "text": text or "(no response)",
        "manual_citations": citations["manual_citations"],
        "issue_citations": citations["issue_citations"],
        "assistant_message_id": assistant_message_id,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_routes.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add agent_server/routes.py tests/test_routes.py
git commit -m "feat(routes): POST /api/chat bridges to @invoke + re-issues VS citations"
```

---

### Task 12: POST /api/feedback — MLflow assessment + Lakebase mirror

**Files:**
- Modify: `agent_server/routes.py`
- Modify: `tests/test_routes.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_routes.py`:

```python
def test_feedback_requires_email(client):
    r = client.post("/api/feedback", json={"message_id": "m1", "rating": "up"})
    assert r.status_code == 401


def test_feedback_writes_to_mlflow_and_lakebase(client):
    """POST /api/feedback logs feedback to MLflow trace + upserts Lakebase row."""
    with patch("agent_server.routes._lookup_trace_id", return_value="tr-99") as lookup, \
         patch("agent_server.routes._upsert_feedback") as upsert, \
         patch("agent_server.routes._log_mlflow_feedback") as mflog:
        r = client.post(
            "/api/feedback",
            headers={"X-Forwarded-Email": "tech@flightsafety.com"},
            json={"message_id": "m1", "rating": "up", "comment": "great"},
        )
    assert r.status_code == 200
    lookup.assert_called_once_with("m1")
    upsert.assert_called_once()
    mflog.assert_called_once_with("tr-99", "up", "great")


def test_feedback_rating_must_be_up_or_down(client):
    r = client.post(
        "/api/feedback",
        headers={"X-Forwarded-Email": "tech@flightsafety.com"},
        json={"message_id": "m1", "rating": "sideways"},
    )
    assert r.status_code == 422  # pydantic validation


def test_feedback_returns_200_even_if_mlflow_fails(client):
    """MLflow log_feedback failure must NOT fail the request; Lakebase mirror is enough."""
    with patch("agent_server.routes._lookup_trace_id", return_value="tr-99"), \
         patch("agent_server.routes._upsert_feedback") as upsert, \
         patch("agent_server.routes._log_mlflow_feedback",
               side_effect=RuntimeError("MLflow unreachable")):
        r = client.post(
            "/api/feedback",
            headers={"X-Forwarded-Email": "tech@flightsafety.com"},
            json={"message_id": "m1", "rating": "down"},
        )
    assert r.status_code == 200
    upsert.assert_called_once()
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_routes.py -v`
Expected: 4 new FAIL.

- [ ] **Step 3: Implement /api/feedback**

Append to `agent_server/routes.py`:

```python
from typing import Literal


class FeedbackRequest(BaseModel):
    message_id: str
    rating: Literal["up", "down"]
    comment: str | None = None


def _lookup_trace_id(message_id: str) -> str | None:
    import psycopg
    from agent_server.memory import get_pg_connection_string
    with psycopg.connect(get_pg_connection_string(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT mlflow_trace_id FROM agent_server.messages WHERE id = %s",
                (message_id,),
            )
            row = cur.fetchone()
    return row[0] if row else None


def _upsert_feedback(message_id: str, rating: str, comment: str | None,
                     user_email: str, trace_id: str | None) -> None:
    import psycopg
    from agent_server.memory import get_pg_connection_string
    sql = """
        INSERT INTO agent_server.message_feedback
          (message_id, rating, comment, user_email, mlflow_trace_id, updated_at)
        VALUES (%s, %s, %s, %s, %s, now())
        ON CONFLICT (message_id) DO UPDATE SET
          rating = EXCLUDED.rating,
          comment = EXCLUDED.comment,
          mlflow_trace_id = EXCLUDED.mlflow_trace_id,
          updated_at = now()
    """
    with psycopg.connect(get_pg_connection_string(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (message_id, rating, comment, user_email, trace_id))


def _log_mlflow_feedback(trace_id: str, rating: str, comment: str | None) -> None:
    import mlflow
    # mlflow.log_feedback writes an Assessment to the trace.
    mlflow.log_feedback(
        trace_id=trace_id,
        name="thumbs",
        value=rating,
        rationale=comment,
    )


@router.post("/api/feedback")
async def feedback(req: FeedbackRequest, request: Request):
    email = get_user_email(request)
    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")

    trace_id = _lookup_trace_id(req.message_id)
    _upsert_feedback(req.message_id, req.rating, req.comment, email, trace_id)

    if trace_id:
        try:
            _log_mlflow_feedback(trace_id, req.rating, req.comment)
        except Exception:
            # Lakebase mirror is enough for app-side render; log + continue.
            import logging
            logging.getLogger(__name__).warning(
                "mlflow.log_feedback failed for message_id=%s", req.message_id,
                exc_info=True,
            )

    return {"ok": True, "message_id": req.message_id, "rating": req.rating}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_routes.py -v`
Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add agent_server/routes.py tests/test_routes.py
git commit -m "feat(routes): POST /api/feedback writes MLflow assessment + Lakebase mirror"
```

---

### Task 13: AgentServer entrypoint + static SPA mount

**Files:**
- Create: `agent_server/start_server.py`
- Create: `tests/test_start_server.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_start_server.py`:

```python
"""Sanity-check that start_server builds the FastAPI app without errors."""


def test_main_is_callable():
    from agent_server import start_server
    assert callable(start_server.main)


def test_app_module_attribute_exists():
    """`app` must be a module-level FastAPI instance so uvicorn workers can import it."""
    from agent_server import start_server
    assert start_server.app is not None
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_start_server.py -v`
Expected: FAIL — `agent_server.start_server` missing.

- [ ] **Step 3: Create start_server.py**

Create `agent_server/start_server.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_start_server.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add agent_server/start_server.py tests/test_start_server.py
git commit -m "feat(server): AgentServer entrypoint with custom routes + SPA static mount"
```

---

### Task 14: run_eval.py + smoke.py

**Files:**
- Create: `scripts/run_eval.py`
- Create: `scripts/smoke.py`

- [ ] **Step 1: Create run_eval.py**

Create `scripts/run_eval.py`:

```python
"""DAB job entrypoint: run mlflow.genai.evaluate against FSISIM personas.

Usage in databricks.yml job task:
    python_file: scripts/run_eval.py
    parameters:
      - "--personas-file"
      - "agent_server.personas"
"""
from __future__ import annotations
import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--personas-file",
        default="agent_server.personas",
        help="Python module path holding the PERSONAS list",
    )
    parser.add_argument("--max-turns", type=int, default=5)
    args = parser.parse_args()

    # Import here so a misconfigured deploy still gives a usable --help.
    from agent_server.evaluate_agent import evaluate
    evaluate(personas_module_path=args.personas_file, max_turns=args.max_turns)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Create smoke.py**

Create `scripts/smoke.py`:

```python
"""Post-deploy smoke test for the FSISIM app.

1. POST /api/chat with a fixed prompt; assert text + assistant_message_id.
2. POST /api/feedback up; assert 200.
3. GET /api/threads; assert the new thread appears.

Usage:
    uv run python -m scripts.smoke --app-url https://fsisim-scaffold-<host>
"""
from __future__ import annotations
import argparse
import sys

import httpx
from databricks.sdk import WorkspaceClient

PROMPT = "hydraulic pressure drop on takeoff — anything similar in past issues?"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-url", required=True, help="https://fsisim-scaffold-<host>")
    args = parser.parse_args()

    w = WorkspaceClient()
    auth_headers = w.config.authenticate()
    client = httpx.Client(base_url=args.app_url, headers=auth_headers, timeout=120.0)

    print("POST /api/chat ...")
    r = client.post("/api/chat", json={"content": PROMPT})
    r.raise_for_status()
    body = r.json()
    assert body["text"], "empty assistant text"
    assert body["assistant_message_id"], "missing assistant_message_id"
    print(f"  text length={len(body['text'])}; assistant_message_id={body['assistant_message_id']}")

    print("POST /api/feedback ...")
    r = client.post("/api/feedback", json={"message_id": body["assistant_message_id"], "rating": "up"})
    r.raise_for_status()
    print("  feedback recorded")

    print("GET /api/threads ...")
    r = client.get("/api/threads")
    r.raise_for_status()
    threads = r.json()["threads"]
    assert any(t["thread_id"] == body["thread_id"] for t in threads), "thread not found in list"
    print(f"  thread visible (count={len(threads)})")

    print("Smoke OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Verify imports**

Run: `python -c "from scripts import run_eval, smoke; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add scripts/run_eval.py scripts/smoke.py
git commit -m "feat(scripts): run_eval.py for DAB job + smoke.py for post-deploy verification"
```

---

### Task 15: databricks.yml — DAB root config

**Files:**
- Create: `databricks.yml`

- [ ] **Step 1: Create databricks.yml**

Create `databricks.yml`:

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
    default: agent_server.personas
  agent_app_name:
    default: fsisim-scaffold

resources:
  apps:
    fsisim_scaffold:
      name: ${var.agent_app_name}
      description: FSISIM Issue Resolution Agent (synthetic data; Agents as Apps)
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
        quartz_cron_expression: "0 0 7 ? * MON"
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

- [ ] **Step 2: Validate the bundle config locally**

Run: `databricks bundle validate --target dev 2>&1 | tail -20`
Expected: "Validation OK!" (or similar). If errors mention undefined variables or missing resources, fix per the error.

- [ ] **Step 3: Commit**

```bash
git add databricks.yml
git commit -m "feat(dab): bundle root config — app + experiment + eval job + variables"
```

---

### Task 16: Update app.yaml + .databricksignore for the new entrypoint

**Files:**
- Modify: `app.yaml` (replaces `app/app.yaml`)
- Move: `app/app.yaml` -> `app.yaml` (DAB expects app config at bundle root)
- Modify: `app/.databricksignore`

- [ ] **Step 1: Move and rewrite app.yaml**

Run:

```bash
git mv app/app.yaml app.yaml
```

Replace the contents of `app.yaml` with:

```yaml
command: ["uv", "run", "start-app"]

env:
  - name: MLFLOW_TRACKING_URI
    value: "databricks"
  - name: MLFLOW_REGISTRY_URI
    value: "databricks-uc"
  - name: MLFLOW_EXPERIMENT_ID
    valueFrom: "experiment"
  - name: LAKEBASE_INSTANCE_NAME
    value: "fsisim-poc"
  - name: LAKEBASE_DATABASE_NAME
    value: "fsisim_chat"
  - name: LAKEBASE_AGENT_MEMORY_SCHEMA
    value: "agent_server"
```

- [ ] **Step 2: Update .databricksignore (now at bundle root)**

Run:

```bash
git mv app/.databricksignore .databricksignore
```

Replace the contents of `.databricksignore` with:

```
app/frontend/node_modules
app/frontend/src
app/frontend/public
app/frontend/index.html
app/frontend/package.json
app/frontend/package-lock.json
app/frontend/tsconfig*.json
app/frontend/vite.config*
app/frontend/eslint.config.*
app/frontend/.gitignore
app/frontend/.vite
app/frontend/README.md
.worktrees
.venv
__pycache__
*.pyc
mlruns
mlflow.db
mlartifacts
```

- [ ] **Step 3: Commit**

```bash
git add app.yaml .databricksignore
git commit -m "chore(dab): move app.yaml + .databricksignore to bundle root for DAB deploys"
```

---

### Task 17: Remove the old agent/ + app/backend/ code

**Files:**
- Delete: `agent/`
- Delete: `app/backend/`
- Delete: `tests/test_agent_module.py` (it lives in agent_server/ now — re-purpose if needed)

- [ ] **Step 1: Delete the legacy directories**

Run:

```bash
git rm -r agent/ app/backend/
```

- [ ] **Step 2: Verify nothing in agent_server/ imports the old paths**

Run: `grep -rn "from agent\." agent_server/ scripts/ tests/`
Expected: no output. If any matches, switch them to `agent_server.<module>`.

- [ ] **Step 3: Update existing tests that referenced the old paths**

In `tests/test_agent_tools.py`, replace any `from agent import ...` with `from agent_server import ...` (this file may reference the old `agent.tools` — adapt as needed; if the file becomes empty or obsolete, delete it via `git rm`).

In `tests/test_config.py`, the file should not need changes (it imports `config.Config` which is unchanged).

Run: `pytest tests/ -v`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add -u tests/
git commit -m "refactor: drop agent/ + app/backend/ in favor of agent_server/"
```

---

### Task 18: React — add /api/threads + /api/feedback client calls

**Files:**
- Modify: `app/frontend/src/api/chat.ts`

- [ ] **Step 1: Replace `app/frontend/src/api/chat.ts`**

Replace the entire file with:

```typescript
export interface ManualCitation {
  source_pdf: string;
  filename: string;
  title: string;
  page_first: number;
  page_last: number;
  preview: string;
}

export interface IssueCitation {
  issue_id: number;
  issue_type: string;
  sim_name: string;
  note_type: string;
  preview: string;
}

export interface ChatResponse {
  thread_id: string;
  text: string;
  manual_citations: ManualCitation[];
  issue_citations: IssueCitation[];
  assistant_message_id: string;
  error: string | null;
}

export interface ThreadSummary {
  thread_id: string;
  title: string;
  updated_at: string;
}

export interface ThreadMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  mlflow_trace_id?: string;
}

export async function sendChat(content: string, threadId?: string): Promise<ChatResponse> {
  const resp = await fetch("/api/chat", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, thread_id: threadId }),
  });
  if (!resp.ok) {
    return {
      thread_id: threadId ?? "",
      text: `Request failed (${resp.status}).`,
      manual_citations: [],
      issue_citations: [],
      assistant_message_id: "",
      error: `http_${resp.status}`,
    };
  }
  const body = (await resp.json()) as ChatResponse;
  return { ...body, error: null };
}

export async function listThreads(): Promise<ThreadSummary[]> {
  const resp = await fetch("/api/threads", { credentials: "include" });
  if (!resp.ok) return [];
  const { threads } = (await resp.json()) as { threads: ThreadSummary[] };
  return threads;
}

export async function getThread(
  threadId: string,
): Promise<{ messages: ThreadMessage[] }> {
  const resp = await fetch(`/api/threads/${encodeURIComponent(threadId)}`, {
    credentials: "include",
  });
  if (!resp.ok) return { messages: [] };
  return (await resp.json()) as { messages: ThreadMessage[] };
}

export async function postFeedback(
  message_id: string,
  rating: "up" | "down",
  comment?: string,
): Promise<boolean> {
  const resp = await fetch("/api/feedback", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_id, rating, comment }),
  });
  return resp.ok;
}
```

- [ ] **Step 2: Type-check**

Run: `cd app/frontend && npx tsc --noEmit && cd ../..`
Expected: no errors. ChatThread.tsx and other consumers will break — that's expected; fixed in Task 19/20.

- [ ] **Step 3: Commit**

```bash
git add app/frontend/src/api/chat.ts
git commit -m "feat(ui): add listThreads / getThread / postFeedback client calls"
```

---

### Task 19: React — thread list sidebar

**Files:**
- Modify: `app/frontend/src/components/LeftRail.tsx`

- [ ] **Step 1: Replace `LeftRail.tsx`**

Replace the entire file with:

```typescript
import { useEffect, useState } from "react";
import {
  Box,
  Button,
  List,
  ListItemButton,
  ListItemText,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import { listThreads, type ThreadSummary } from "../api/chat";
import { FS_NAVY, FS_BORDER, FS_MUTED } from "../theme";

interface Props {
  currentThreadId: string | null;
  onSelectThread: (threadId: string | null) => void;
  refreshTrigger: number;
}

export default function LeftRail({ currentThreadId, onSelectThread, refreshTrigger }: Props) {
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      const data = await listThreads();
      if (!cancelled) {
        setThreads(data);
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshTrigger]);

  return (
    <Box
      sx={{
        width: 260,
        bgcolor: "#FAFBFC",
        borderRight: `1px solid ${FS_BORDER}`,
        display: "flex",
        flexDirection: "column",
        height: "100%",
      }}
    >
      <Box sx={{ p: 1.5 }}>
        <Button
          fullWidth
          startIcon={<AddIcon />}
          variant="outlined"
          onClick={() => onSelectThread(null)}
          sx={{
            justifyContent: "flex-start",
            color: FS_NAVY,
            borderColor: FS_BORDER,
            textTransform: "none",
          }}
        >
          New chat
        </Button>
      </Box>
      <Typography
        variant="overline"
        sx={{ px: 2, color: FS_MUTED, fontSize: 10, mt: 1 }}
      >
        Recent threads
      </Typography>
      <Box sx={{ flex: 1, overflowY: "auto" }}>
        {loading && (
          <Typography sx={{ px: 2, py: 1, fontSize: 12, color: FS_MUTED }}>
            Loading…
          </Typography>
        )}
        {!loading && threads.length === 0 && (
          <Typography sx={{ px: 2, py: 1, fontSize: 12, color: FS_MUTED }}>
            No threads yet.
          </Typography>
        )}
        <List dense disablePadding>
          {threads.map((t) => (
            <ListItemButton
              key={t.thread_id}
              selected={t.thread_id === currentThreadId}
              onClick={() => onSelectThread(t.thread_id)}
              sx={{
                px: 2,
                "&.Mui-selected": { bgcolor: "#E8EEF7" },
              }}
            >
              <ListItemText
                primary={t.title}
                primaryTypographyProps={{
                  fontSize: 13,
                  noWrap: true,
                  color: FS_NAVY,
                  fontWeight: t.thread_id === currentThreadId ? 600 : 400,
                }}
                secondary={new Date(t.updated_at).toLocaleDateString()}
                secondaryTypographyProps={{ fontSize: 10, color: FS_MUTED }}
              />
            </ListItemButton>
          ))}
        </List>
      </Box>
    </Box>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add app/frontend/src/components/LeftRail.tsx
git commit -m "feat(ui): thread list sidebar wired to /api/threads"
```

---

### Task 20: React — thumbs UI on assistant bubbles

**Files:**
- Modify: `app/frontend/src/components/MessageBubble.tsx`

- [ ] **Step 1: Add thumbs to MessageBubble**

Open `app/frontend/src/components/MessageBubble.tsx` and find the assistant-bubble branch. Add a thumbs row beneath the message text. Replace the assistant-bubble JSX block with:

```typescript
import { useState } from "react";
import { Box, IconButton, Typography } from "@mui/material";
import ThumbUpAltOutlinedIcon from "@mui/icons-material/ThumbUpAltOutlined";
import ThumbUpAltIcon from "@mui/icons-material/ThumbUpAlt";
import ThumbDownAltOutlinedIcon from "@mui/icons-material/ThumbDownAltOutlined";
import ThumbDownAltIcon from "@mui/icons-material/ThumbDownAlt";
import { postFeedback } from "../api/chat";
import type { Citation } from "./CitationPill";
import CitationPill from "./CitationPill";
import { FS_NAVY, FS_BORDER, FS_MUTED } from "../theme";

interface Props {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
  assistantMessageId?: string;
  initialRating?: "up" | "down" | null;
  onCitationClick?: (c: Citation) => void;
}

export default function MessageBubble({
  role,
  text,
  citations,
  assistantMessageId,
  initialRating = null,
  onCitationClick,
}: Props) {
  const [rating, setRating] = useState<"up" | "down" | null>(initialRating);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (next: "up" | "down") => {
    if (!assistantMessageId || submitting) return;
    const prev = rating;
    setRating(next);
    setSubmitting(true);
    const ok = await postFeedback(assistantMessageId, next);
    setSubmitting(false);
    if (!ok) setRating(prev); // roll back on failure
  };

  if (role === "user") {
    return (
      <Box sx={{ alignSelf: "flex-end", maxWidth: "78%", my: 0.5 }}>
        <Box
          sx={{
            bgcolor: FS_NAVY,
            color: "#FFFFFF",
            px: 2,
            py: 1.25,
            borderRadius: 2,
            fontSize: 14,
            whiteSpace: "pre-wrap",
          }}
        >
          {text}
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ alignSelf: "flex-start", maxWidth: "92%", my: 0.5 }}>
      <Box
        sx={{
          bgcolor: "#FFFFFF",
          color: FS_NAVY,
          border: `1px solid ${FS_BORDER}`,
          px: 2,
          py: 1.25,
          borderRadius: 2,
          fontSize: 14,
          whiteSpace: "pre-wrap",
        }}
      >
        {text}
      </Box>
      {citations && citations.length > 0 && (
        <Box sx={{ mt: 0.75, display: "flex", flexWrap: "wrap" }}>
          {citations.map((c, i) => (
            <CitationPill key={i} c={c} onClick={() => onCitationClick?.(c)} />
          ))}
        </Box>
      )}
      {assistantMessageId && (
        <Box sx={{ mt: 0.5, display: "flex", alignItems: "center", gap: 0.5 }}>
          <IconButton
            size="small"
            onClick={() => submit("up")}
            disabled={submitting}
            sx={{ color: rating === "up" ? FS_NAVY : FS_MUTED, padding: 0.25 }}
            aria-label="thumbs up"
          >
            {rating === "up" ? <ThumbUpAltIcon fontSize="inherit" /> : <ThumbUpAltOutlinedIcon fontSize="inherit" />}
          </IconButton>
          <IconButton
            size="small"
            onClick={() => submit("down")}
            disabled={submitting}
            sx={{ color: rating === "down" ? FS_NAVY : FS_MUTED, padding: 0.25 }}
            aria-label="thumbs down"
          >
            {rating === "down" ? <ThumbDownAltIcon fontSize="inherit" /> : <ThumbDownAltOutlinedIcon fontSize="inherit" />}
          </IconButton>
          <Typography sx={{ fontSize: 10, color: FS_MUTED, ml: 1 }}>
            {rating ? "Thanks for the feedback" : "Was this helpful?"}
          </Typography>
        </Box>
      )}
    </Box>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add app/frontend/src/components/MessageBubble.tsx
git commit -m "feat(ui): thumbs up/down on assistant bubbles wired to /api/feedback"
```

---

### Task 21: React — thread-aware ChatThread + App.tsx wiring

**Files:**
- Modify: `app/frontend/src/components/ChatThread.tsx`
- Modify: `app/frontend/src/App.tsx`

- [ ] **Step 1: Update ChatThread.tsx**

Open `app/frontend/src/components/ChatThread.tsx`. Replace the entire component to accept a `threadId` prop, load history on mount, pass the thread id on each send, and bubble the assistant_message_id through to MessageBubble:

```typescript
import { useEffect, useRef, useState } from "react";
import { Box, Container, IconButton, Stack, TextField } from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import MessageBubble from "./MessageBubble";
import CitationSlideOver from "./CitationSlideOver";
import EmptyHero from "./EmptyHero";
import { getThread, sendChat, type ThreadMessage } from "../api/chat";
import type { Citation } from "./CitationPill";
import { FS_NAVY, FS_BORDER } from "../theme";

interface Message {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
  assistantMessageId?: string;
  initialRating?: "up" | "down" | null;
}

interface Props {
  examples: string[];
  threadId: string | null;
  onThreadChange: (threadId: string) => void;
}

export default function ChatThread({ examples, threadId, onThreadChange }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [slideOver, setSlideOver] = useState<Citation | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  // Load history when the parent switches threads.
  useEffect(() => {
    if (!threadId) {
      setMessages([]);
      return;
    }
    let cancelled = false;
    (async () => {
      const { messages: hist } = await getThread(threadId);
      if (cancelled) return;
      const mapped: Message[] = hist
        .filter((m: ThreadMessage) => m.role !== "system")
        .map((m: ThreadMessage) => ({
          role: m.role as "user" | "assistant",
          text: m.content,
          assistantMessageId: m.role === "assistant" ? m.id : undefined,
        }));
      setMessages(mapped);
    })();
    return () => {
      cancelled = true;
    };
  }, [threadId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(textOverride?: string) {
    const content = (textOverride ?? input).trim();
    if (!content || busy) return;
    const next: Message[] = [
      ...messages,
      { role: "user", text: content },
      { role: "assistant", text: "…" },
    ];
    setMessages(next);
    setInput("");
    setBusy(true);

    const resp = await sendChat(content, threadId ?? undefined);

    if (!threadId && resp.thread_id) {
      onThreadChange(resp.thread_id);
    }

    const citations: Citation[] = [
      ...resp.manual_citations.map((m) => ({
        kind: "manual" as const,
        sourcePdf: m.source_pdf,
        filename: m.filename,
        title: m.title,
        pageFirst: m.page_first,
        pageLast: m.page_last,
        preview: m.preview,
      })),
      ...resp.issue_citations.map((i) => ({
        kind: "issue" as const,
        issueId: i.issue_id,
        issueType: i.issue_type,
        simName: i.sim_name,
        noteType: i.note_type,
        preview: i.preview,
      })),
    ];

    setMessages((m) => {
      const copy = [...m];
      copy[copy.length - 1] = {
        role: "assistant",
        text: resp.text || "(no response)",
        citations,
        assistantMessageId: resp.assistant_message_id,
      };
      return copy;
    });
    setBusy(false);
  }

  const hasMessages = messages.length > 0;

  return (
    <Box sx={{ display: "flex", flex: 1, overflow: "hidden", position: "relative" }}>
      <Box sx={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <Container maxWidth="md" sx={{ flex: 1, display: "flex", flexDirection: "column", py: hasMessages ? 3 : 0 }}>
          {!hasMessages && <EmptyHero examples={examples} onPickExample={(q) => send(q)} />}
          {hasMessages && (
            <Stack sx={{ flex: 1, width: "100%" }}>
              {messages.map((m, i) => (
                <MessageBubble
                  key={i}
                  role={m.role}
                  text={m.text}
                  citations={m.citations}
                  assistantMessageId={m.assistantMessageId}
                  initialRating={m.initialRating ?? null}
                  onCitationClick={setSlideOver}
                />
              ))}
              <div ref={endRef} />
            </Stack>
          )}
        </Container>
        <Box sx={{ borderTop: `1px solid ${FS_BORDER}`, p: 1.5 }}>
          <Container maxWidth="md" sx={{ display: "flex", gap: 1 }}>
            <TextField
              fullWidth
              size="small"
              placeholder="Ask about an issue, a fault code, or a manual…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              disabled={busy}
            />
            <IconButton
              onClick={() => send()}
              disabled={busy || !input.trim()}
              sx={{ color: FS_NAVY }}
              aria-label="send"
            >
              <SendIcon />
            </IconButton>
          </Container>
        </Box>
      </Box>
      <CitationSlideOver
        open={slideOver !== null}
        citation={slideOver}
        onClose={() => setSlideOver(null)}
      />
    </Box>
  );
}
```

- [ ] **Step 2: Update App.tsx to manage threadId state**

Open `app/frontend/src/App.tsx`. Replace the existing component body with:

```typescript
import { useState } from "react";
import { Box, AppBar, Toolbar, Avatar, Stack, Typography } from "@mui/material";
import FlightTakeoffIcon from "@mui/icons-material/FlightTakeoff";
import { FS_NAVY, FS_SKY } from "./theme";
import ChatThread from "./components/ChatThread";
import LeftRail from "./components/LeftRail";

export const EXAMPLES = [
  "G001-SIM-01 hydraulic pressure drop on takeoff. Anything similar?",
  "What does FMS VNAV stand for and how is it used in our sims?",
  "Motion platform fault code 47B on G001-SIM-03",
  "Visual database corruption at KJFK approach",
  "How was the connector reseating procedure handled last time?",
];

export default function App() {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const onThreadChange = (newId: string) => {
    setThreadId(newId);
    setRefreshTrigger((n) => n + 1);
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100vh", bgcolor: "background.default" }}>
      <AppBar
        position="static"
        elevation={0}
        sx={{
          bgcolor: FS_NAVY,
          backgroundImage: `linear-gradient(180deg, ${FS_NAVY} 0%, #050530 100%)`,
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <Toolbar sx={{ minHeight: 64, px: { xs: 2, sm: 3 } }}>
          <Stack direction="row" sx={{ alignItems: "center", gap: 1.5 }}>
            <Box
              component="img"
              src="/fsi-logo.svg"
              alt="FlightSafety"
              sx={{ height: 28, filter: "brightness(0) invert(1)", opacity: 0.96 }}
            />
            <Box sx={{ width: "1px", height: 22, bgcolor: "rgba(255,255,255,0.18)", mx: 1.5, flexShrink: 0 }} />
            <Stack direction="row" sx={{ alignItems: "center", gap: 1 }}>
              <FlightTakeoffIcon sx={{ color: FS_SKY, fontSize: 18 }} />
              <Typography
                sx={{ color: "rgba(255,255,255,0.95)", fontWeight: 600, fontSize: 14, letterSpacing: "-0.005em" }}
              >
                FSISIM Issue Resolution Agent
              </Typography>
            </Stack>
          </Stack>
          <Box sx={{ flex: 1 }} />
          <Stack direction="row" sx={{ alignItems: "center", gap: 2 }}>
            <Avatar
              sx={{
                width: 32,
                height: 32,
                bgcolor: FS_SKY,
                fontSize: 13,
                fontWeight: 700,
                border: "2px solid rgba(255,255,255,0.15)",
              }}
            >
              JW
            </Avatar>
          </Stack>
        </Toolbar>
      </AppBar>

      <Box sx={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <LeftRail
          currentThreadId={threadId}
          onSelectThread={setThreadId}
          refreshTrigger={refreshTrigger}
        />
        <Box sx={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", position: "relative" }}>
          <ChatThread examples={EXAMPLES} threadId={threadId} onThreadChange={onThreadChange} />
        </Box>
      </Box>
    </Box>
  );
}
```

- [ ] **Step 3: Type-check + build**

Run: `cd app/frontend && npm run build 2>&1 | tail -10 && cd ../..`
Expected: build succeeds; dist/assets/index-<new-hash>.js produced.

- [ ] **Step 4: Commit**

```bash
git add app/frontend/src/components/ChatThread.tsx app/frontend/src/App.tsx
git commit -m "feat(ui): thread-aware ChatThread + App wires LeftRail to threadId state"
```

---

### Task 22: Update README + CLAUDE.md for the new deploy flow

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Rewrite the README Quickstart**

Open `README.md`. Replace the entire "## Quickstart" section (from the `## Quickstart` heading through the closing triple-backtick of step 14 / "Deploy") with:

```markdown
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
python -c "from agent.tools import apply; apply()"   # or apply tools.sql

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
```

- [ ] **Step 2: Update CLAUDE.md to reflect the new structure**

Open `CLAUDE.md`. Replace the entire file with:

```markdown
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
```

- [ ] **Step 3: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: rewrite quickstart for DAB deploy + Lakebase + Agents-as-Apps"
```

---

### Task 23: Provision Lakebase + first DAB deploy (manual / one-time)

This task is performed **once** to bring the deployed app online for the first time. Subsequent deploys are just `npm run build && databricks bundle deploy`.

- [ ] **Step 1: Provision a Lakebase instance**

Through the workspace UI: Create a Lakebase Postgres instance named `fsisim-poc` in the same region as the workspace. Pick the smallest tier (capacity_units=1 is fine for the scaffold). Record the instance name; it must match the `lakebase_instance_name` variable in `databricks.yml`.

- [ ] **Step 2: Validate the bundle**

Run: `databricks bundle validate --target dev`
Expected: "Validation OK!"

- [ ] **Step 3: Build the frontend**

Run: `cd app/frontend && npm install && npm run build && cd ../..`
Expected: `app/frontend/dist/assets/index-<hash>.js` produced.

- [ ] **Step 4: Deploy the bundle**

Run: `databricks bundle deploy --target dev`
Expected: bundle uploads, app + experiment + job are created/updated, App reaches RUNNING state. May take 5-10 minutes on first deploy.

- [ ] **Step 5: Grant Lakebase permissions to the App SP**

Run:

```bash
APP_SP=$(databricks apps get fsisim-scaffold --output json | jq -r '.service_principal_client_id')
echo "App SP: $APP_SP"
uv run python scripts/grant_lakebase_permissions.py "$APP_SP" \
  --memory-type langgraph --instance-name fsisim-poc
```

Expected: prints grant statements; no errors.

- [ ] **Step 6: Create the custom feedback schema**

Run: `uv run python -m scripts.init_lakebase_schema`
Expected: "Schema applied OK."

- [ ] **Step 7: Smoke-test the deployed app**

Look up the app URL:

```bash
APP_URL=$(databricks apps get fsisim-scaffold --output json | jq -r '.url')
echo "App URL: $APP_URL"
```

Open the URL in a browser, log in, send a chat, click thumbs up.

Then run the script:

```bash
uv run python -m scripts.smoke --app-url "$APP_URL"
```

Expected: "Smoke OK."

- [ ] **Step 8: Verify MLflow experiment has traces**

In the workspace UI, navigate to MLflow experiments and find the one bound to `fsisim-scaffold`. Confirm:
- Traces appear after the smoke chat
- The trace has `mlflow.trace.session` metadata matching the smoke thread id
- The trace has an assessment named `thumbs` with value `up`

This task has no commit — it's an operational checklist confirming the deploy works end to end.

---

## Self-review notes

The plan covers each spec section:
- **Architecture / Components**: Tasks 1-13 implement the entire backend (agent module, memory, routes, eval, AgentServer entrypoint, DAB scaffold).
- **Data model**: Task 7 creates `agent_server.message_feedback`; LangGraph PostgresSaver and AgentServer auto-create the rest.
- **Data flow**: covered by Task 11 (`/api/chat`), Task 12 (`/api/feedback`), and Task 10 (thread reads).
- **Error handling**: Task 9 (PDF text/plain on failure), Task 12 (Lakebase mirror succeeds even if MLflow fails), Task 10 (401/403/404 paths).
- **Testing**: every backend task ships its own pytest. UI changes type-check + build.
- **Deployment**: Task 23 documents the one-time setup.
- **Open questions from the spec**: resolved at implementation time:
  - `mlflow.log_feedback` signature: confirmed in Task 12 (`mlflow.log_feedback(trace_id, name, value, rationale)`)
  - AgentServer's `messages` schema: Task 10 reads `session_id`, `user_email`, `mlflow_trace_id`, `id`, `role`, `content`, `created_at`. If column names differ at runtime, fix the SQL in `_fetch_*` functions
  - `@invoke` `custom_outputs` support: Task 11 sidesteps this by extracting `id` from the `output[].id` field directly, which the template guarantees
  - CI: skipped; not in scope for this branch
  - Lakebase instance provisioning: Task 23 step 1 is manual (UI)
