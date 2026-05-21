"""Apply agent/tools.sql against the configured UC catalog/schema.

Substitutes config.py names into the SQL templates and runs each CREATE OR
REPLACE FUNCTION statement against a serverless warehouse.

The search_technical_manuals function references the manual VS index, which
only exists after Task 10 + Task 11 have created it. If that index is missing,
the function CREATE will still succeed (Databricks defers validation until
the function is invoked), but calls to it will error until the index is ready.
"""
from __future__ import annotations
import re
import time
from pathlib import Path

from databricks.sdk import WorkspaceClient

from config import Config


def _pick_warehouse(w: WorkspaceClient) -> str:
    warehouses = list(w.warehouses.list())
    running = [x for x in warehouses if x.state and x.state.value == "RUNNING"]
    chosen = running[0] if running else warehouses[0]
    if chosen.state and chosen.state.value != "RUNNING":
        w.warehouses.start(chosen.id).result()
    return chosen.id


def _execute(w: WorkspaceClient, warehouse_id: str, sql: str) -> None:
    resp = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id, statement=sql, wait_timeout="50s",
    )
    state = resp.status.state.value if resp.status and resp.status.state else "UNKNOWN"
    while state in ("PENDING", "RUNNING"):
        time.sleep(3)
        resp = w.statement_execution.get_statement(resp.statement_id)
        state = resp.status.state.value if resp.status and resp.status.state else "UNKNOWN"
    if state != "SUCCEEDED":
        msg = resp.status.error.message if resp.status and resp.status.error else "(no msg)"
        raise RuntimeError(f"SQL state={state}: {msg}\nSQL head:\n{sql[:300]}")


def _split_statements(sql: str) -> list[str]:
    """Strip comment-only lines, split on semicolons that aren't inside parens."""
    cleaned = "\n".join(
        line for line in sql.splitlines()
        if not line.strip().startswith("--")
    )
    parts = [s.strip() for s in cleaned.split(";") if s.strip()]
    return parts


def main() -> None:
    cfg = Config()
    w = WorkspaceClient()
    warehouse_id = _pick_warehouse(w)

    sql_path = Path(__file__).parent / "tools.sql"
    raw = sql_path.read_text()
    sql = (
        raw.replace("{catalog}", cfg.catalog)
           .replace("{schema}", cfg.schema)
           .replace("{issue_index}", cfg.issue_index_fqn)
           .replace("{manual_index}", cfg.manual_index_fqn)
    )

    for stmt in _split_statements(sql):
        fn_match = re.search(r"FUNCTION\s+(\S+?)\(", stmt)
        label = fn_match.group(1) if fn_match else stmt[:50]
        print(f"Applying: {label}")
        _execute(w, warehouse_id, stmt)

    print("Done.")


if __name__ == "__main__":
    main()
