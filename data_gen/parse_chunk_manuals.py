"""Parse manual PDFs from UC volume via ai_parse_document + ai_prep_search,
write chunks to jdub_demo.fsisim_issue_ai_gold.g001_manual_chunks.

Pipeline (all SQL, executed against a serverless warehouse):
  1. READ_FILES on the manuals/ volume folder (binaryFile format).
  2. ai_parse_document(content) -> VARIANT with parsed elements.
  3. ai_prep_search(doc) -> VARIANT with retrieval-ready chunks.
  4. explode + cast into typed columns; write to Delta.

Output schema:
  chunk_id          STRING (PK from ai_prep_search)
  source_pdf        STRING
  chunk_position    INT
  chunk_to_retrieve STRING (returned to the user / cited)
  chunk_to_embed    STRING (passed to the embedding model)
  page_first        INT
  page_last         INT

Gates verified at execution time:
  - ai_prep_search Beta enabled in workspace Previews page.
  - Warehouse runs Databricks Runtime 18.2+ (or serverless env v3+).
"""
from __future__ import annotations
from databricks.sdk import WorkspaceClient

from config import Config


CHUNK_SQL_TEMPLATE = """
WITH parsed AS (
  SELECT
    path AS source_pdf,
    ai_parse_document(content, map('version', '2.0')) AS doc
  FROM READ_FILES('{volume}/', format => 'binaryFile')
  WHERE path LIKE '%.pdf'
),
prepped AS (
  SELECT
    source_pdf,
    ai_prep_search(doc) AS prep
  FROM parsed
),
chunks AS (
  SELECT
    source_pdf,
    explode(CAST(prep:document:contents AS ARRAY<VARIANT>)) AS chunk
  FROM prepped
)
SELECT
  chunk:chunk_id::STRING                AS chunk_id,
  source_pdf,
  chunk:chunk_position::INT             AS chunk_position,
  chunk:chunk_to_retrieve::STRING       AS chunk_to_retrieve,
  chunk:chunk_to_embed::STRING          AS chunk_to_embed,
  COALESCE(CAST(chunk:pages AS ARRAY<VARIANT>)[0]:page_id::INT, 0)                                      AS page_first,
  COALESCE(CAST(chunk:pages AS ARRAY<VARIANT>)[size(CAST(chunk:pages AS ARRAY<VARIANT>)) - 1]:page_id::INT, 0) AS page_last
FROM chunks
WHERE chunk:chunk_to_embed IS NOT NULL
  AND length(chunk:chunk_to_embed::STRING) > 50
"""


def _pick_warehouse(w: WorkspaceClient) -> str:
    warehouses = list(w.warehouses.list())
    if not warehouses:
        raise RuntimeError("No SQL warehouses found.")
    running = [x for x in warehouses if x.state and x.state.value == "RUNNING"]
    chosen = running[0] if running else warehouses[0]
    if chosen.state and chosen.state.value != "RUNNING":
        print(f"  starting warehouse {chosen.name} ({chosen.id}) ...")
        w.warehouses.start(chosen.id).result()
    print(f"  using warehouse {chosen.name} ({chosen.id})")
    return chosen.id


def _execute(w: WorkspaceClient, warehouse_id: str, sql: str) -> None:
    """Submit asynchronously and poll until terminal state."""
    import time
    resp = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id, statement=sql, wait_timeout="50s",
    )
    state = resp.status.state.value if resp.status and resp.status.state else "UNKNOWN"
    while state in ("PENDING", "RUNNING"):
        time.sleep(5)
        resp = w.statement_execution.get_statement(resp.statement_id)
        state = resp.status.state.value if resp.status and resp.status.state else "UNKNOWN"
    if state != "SUCCEEDED":
        msg = resp.status.error.message if resp.status and resp.status.error else "(no error msg)"
        raise RuntimeError(f"SQL state={state}: {msg}\nSQL:\n{sql}")


def main() -> None:
    cfg = Config()
    w = WorkspaceClient()

    warehouse_id = _pick_warehouse(w)
    sql = CHUNK_SQL_TEMPLATE.format(volume=cfg.manuals_volume_path)
    target = cfg.manual_table_fqn

    print(f"Writing chunks to {target} ...")
    ctas = f"CREATE OR REPLACE TABLE {target} AS\n{sql}"
    _execute(w, warehouse_id, ctas)

    _execute(
        w, warehouse_id,
        f"ALTER TABLE {target} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)",
    )

    count_resp = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=f"SELECT COUNT(*) FROM {target}",
        wait_timeout="30s",
    )
    n = count_resp.result.data_array[0][0] if count_resp.result and count_resp.result.data_array else "?"
    print(f"  wrote {n} chunks to {target}")
    print("Done.")


if __name__ == "__main__":
    main()
