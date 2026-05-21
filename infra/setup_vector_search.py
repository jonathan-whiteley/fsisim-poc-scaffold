"""Idempotent VS endpoint + index creation for issues and manuals.

Uses the Databricks SDK (OAuth via ~/.databrickscfg DEFAULT profile) rather
than the standalone vectorsearch client (which requires a PAT).

Creates a STANDARD VS endpoint, a composite-text Delta table over the issue
table (CDF enabled), and two Delta Sync indexes (issues + manuals) with
Databricks-managed embeddings (gte-large-en).

The manual index will fail to create until the manual_chunks Delta table
exists (Task 10 populates it). The script catches that and prints a hint.
"""
from __future__ import annotations
import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.vectorsearch import (
    EndpointType, DeltaSyncVectorIndexSpecRequest, EmbeddingSourceColumn,
    PipelineType, VectorIndexType,
)
from databricks.sdk.errors import ResourceAlreadyExists, NotFound, BadRequest

from config import Config


COMPOSITE_VIEW_SQL = """
CREATE OR REPLACE VIEW {catalog}.{schema}.g001_issue_embed_view AS
SELECT
  id AS chunk_id,
  issue_id,
  issue_type,
  category,
  systems,
  root_cause,
  sim_name,
  sim_type_name,
  loc_name,
  note_type,
  note_type_description,
  note_create_date,
  CONCAT_WS(' | ',
    CONCAT('Issue type: ', COALESCE(issue_type, '')),
    CONCAT('Category: ', COALESCE(category, '')),
    CONCAT('System: ', COALESCE(systems, '')),
    CONCAT('Simulator: ', COALESCE(sim_name, ''), ' (', COALESCE(sim_type_name, ''), ')'),
    CONCAT('Location: ', COALESCE(loc_name, '')),
    CONCAT('Root cause: ', COALESCE(root_cause, '')),
    CONCAT('Note (', COALESCE(note_type_description, ''), '): ', COALESCE(note, ''))
  ) AS composite_text
FROM {catalog}.{schema}.g001_issue
"""


def _pick_warehouse(w: WorkspaceClient) -> str:
    warehouses = list(w.warehouses.list())
    running = [x for x in warehouses if x.state and x.state.value == "RUNNING"]
    chosen = running[0] if running else warehouses[0]
    if chosen.state and chosen.state.value != "RUNNING":
        print(f"  starting warehouse {chosen.name} ({chosen.id}) ...")
        w.warehouses.start(chosen.id).result()
    print(f"  using warehouse {chosen.name} ({chosen.id})")
    return chosen.id


def _execute_sql(w: WorkspaceClient, warehouse_id: str, sql: str) -> None:
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
        raise RuntimeError(f"SQL state={state}: {msg}\nSQL:\n{sql}")


def _ensure_endpoint(w: WorkspaceClient, name: str) -> None:
    existing = {e.name for e in w.vector_search_endpoints.list_endpoints()}
    if name not in existing:
        print(f"  creating VS endpoint {name} ...")
        w.vector_search_endpoints.create_endpoint(name=name, endpoint_type=EndpointType.STANDARD)
    else:
        print(f"  endpoint {name} already exists")

    # Wait for ONLINE
    print("  waiting for endpoint to be ONLINE (can take 5 to 15 minutes) ...")
    waited = 0
    while True:
        ep = w.vector_search_endpoints.get_endpoint(name)
        state = ep.endpoint_status.state.value if ep.endpoint_status and ep.endpoint_status.state else "UNKNOWN"
        print(f"    state={state} ({waited}s)")
        if state == "ONLINE":
            return
        if state in ("PROVISIONING_FAILED", "OFFLINE_FAILED"):
            raise RuntimeError(f"Endpoint failed: state={state}")
        time.sleep(20)
        waited += 20
        if waited > 1500:
            raise RuntimeError("Endpoint did not become ONLINE within 25 minutes")


def _ensure_index(
    w: WorkspaceClient,
    endpoint: str,
    index_name: str,
    source_table: str,
    embedding_column: str,
) -> None:
    spec = DeltaSyncVectorIndexSpecRequest(
        source_table=source_table,
        pipeline_type=PipelineType.TRIGGERED,
        embedding_source_columns=[
            EmbeddingSourceColumn(
                name=embedding_column,
                embedding_model_endpoint_name="databricks-gte-large-en",
            )
        ],
    )
    try:
        w.vector_search_indexes.create_index(
            name=index_name,
            endpoint_name=endpoint,
            primary_key="chunk_id",
            index_type=VectorIndexType.DELTA_SYNC,
            delta_sync_index_spec=spec,
        )
        print(f"  created index {index_name} (sync triggered)")
    except ResourceAlreadyExists:
        print(f"  index {index_name} already exists; triggering sync")
        w.vector_search_indexes.sync_index(index_name)
    except (NotFound, BadRequest) as e:
        msg = str(e)
        if "TABLE_OR_VIEW_NOT_FOUND" in msg or "does not exist" in msg.lower():
            print(
                f"  source table {source_table} not found. "
                f"Run Task 10 first (parse_chunk_manuals), then re-run."
            )
        else:
            raise


def main() -> None:
    cfg = Config()
    w = WorkspaceClient()

    print(f"Ensuring VS endpoint {cfg.vs_endpoint} ...")
    _ensure_endpoint(w, cfg.vs_endpoint)

    print("Building composite text table for issue index ...")
    warehouse_id = _pick_warehouse(w)
    _execute_sql(w, warehouse_id, COMPOSITE_VIEW_SQL.format(catalog=cfg.catalog, schema=cfg.schema))
    source_view = f"{cfg.catalog}.{cfg.schema}.g001_issue_embed_view"
    composite_table = f"{cfg.catalog}.{cfg.schema}.g001_issue_embed"
    _execute_sql(
        w, warehouse_id,
        f"CREATE OR REPLACE TABLE {composite_table} AS SELECT * FROM {source_view}",
    )
    _execute_sql(
        w, warehouse_id,
        f"ALTER TABLE {composite_table} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)",
    )

    print(f"Ensuring issue index {cfg.issue_index_fqn} ...")
    _ensure_index(
        w, endpoint=cfg.vs_endpoint, index_name=cfg.issue_index_fqn,
        source_table=composite_table, embedding_column="composite_text",
    )

    print(f"Ensuring manual index {cfg.manual_index_fqn} ...")
    _ensure_index(
        w, endpoint=cfg.vs_endpoint, index_name=cfg.manual_index_fqn,
        source_table=cfg.manual_table_fqn, embedding_column="chunk_to_embed",
    )

    print("Done. Indexes continue syncing in the background.")


if __name__ == "__main__":
    main()
