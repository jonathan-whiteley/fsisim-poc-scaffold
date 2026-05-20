"""Materialize ~500 synthetic issues into Delta table jdub_demo.fsisim_issue_ai_gold.g001_issue.

Pipeline:
  1. Generate structural IssueRow objects with a deferred note author (no LLM yet).
  2. Issue all note-authoring LLM calls in parallel against the Databricks FM API.
  3. Patch notes back into rows.
  4. Write to local parquet via pyarrow.
  5. Upload to UC volume staging path.
  6. CREATE OR REPLACE TABLE AS SELECT * FROM the parquet file.

Usage:
  python -m data_gen.write_issues [--num-issues 500] [--workers 16]
"""
from __future__ import annotations
import argparse
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from typing import List

from databricks.sdk import WorkspaceClient

from config import Config
from data_gen.gen_issues import IssueGenerator, IssueRow
from data_gen.note_authoring import IssueContext, NoteAuthor


_PLACEHOLDER_RE = re.compile(r"^__PLACEHOLDER_(\d+)__$")


class _DeferredAuthor:
    """NoteAuthor stand-in that records contexts and returns a placeholder.

    Lets us run IssueGenerator synchronously to lay out the structural rows,
    then fan out all LLM calls in parallel afterwards.
    """

    def __init__(self) -> None:
        self.contexts: List[IssueContext] = []

    def author(self, ctx: IssueContext) -> str:
        idx = len(self.contexts)
        self.contexts.append(ctx)
        return f"__PLACEHOLDER_{idx}__"


def _parallel_author_notes(contexts: List[IssueContext], workers: int) -> List[str]:
    """Author each context in parallel. Returns a list aligned by index."""
    author = NoteAuthor()
    out: List[str] = [""] * len(contexts)
    completed = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        fut_to_idx = {pool.submit(author.author, ctx): i for i, ctx in enumerate(contexts)}
        for fut in as_completed(fut_to_idx):
            i = fut_to_idx[fut]
            try:
                out[i] = fut.result()
            except Exception as e:
                out[i] = f"[note authoring failed: {type(e).__name__}: {e}]"
            completed += 1
            if completed % 100 == 0 or completed == len(contexts):
                elapsed = time.time() - t0
                rate = completed / elapsed if elapsed > 0 else 0
                print(
                    f"  authored {completed}/{len(contexts)} notes "
                    f"({rate:.1f}/s, {elapsed:.0f}s elapsed)"
                )
    return out


def _patch_notes(rows: List[IssueRow], notes: List[str]) -> None:
    for row in rows:
        m = _PLACEHOLDER_RE.match(row.note or "")
        if m:
            row.note = notes[int(m.group(1))]


def _write_parquet(rows: List[IssueRow], path: Path) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    records = [asdict(r) for r in rows]
    table = pa.Table.from_pylist(records)
    pq.write_table(table, path)


def _upload_to_volume(w: WorkspaceClient, local: Path, remote: str) -> None:
    with open(local, "rb") as f:
        w.files.upload(file_path=remote, contents=f, overwrite=True)


def _execute_sql(w: WorkspaceClient, warehouse_id: str, sql: str) -> None:
    resp = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=sql,
        wait_timeout="50s",
    )
    state = resp.status.state.value if resp.status and resp.status.state else "UNKNOWN"
    if state != "SUCCEEDED":
        raise RuntimeError(f"SQL failed (state={state}): {sql}\n{resp.status}")


def _pick_warehouse(w: WorkspaceClient) -> str:
    """Pick a serverless-capable warehouse and start it if necessary."""
    warehouses = list(w.warehouses.list())
    if not warehouses:
        raise RuntimeError("No SQL warehouses found in workspace.")
    # Prefer one that is already RUNNING; else first available
    running = [x for x in warehouses if x.state and x.state.value == "RUNNING"]
    chosen = running[0] if running else warehouses[0]
    if chosen.state and chosen.state.value != "RUNNING":
        print(f"  starting warehouse {chosen.name} ({chosen.id}) ...")
        w.warehouses.start(chosen.id).result()
    print(f"  using warehouse {chosen.name} ({chosen.id})")
    return chosen.id


def main(num_issues: int = 500, workers: int = 16) -> None:
    cfg = Config()
    w = WorkspaceClient()

    print(f"Step 1/6: generating {num_issues} issues (deferred LLM) ...")
    deferred = _DeferredAuthor()
    gen = IssueGenerator(seed=42, note_author=deferred)
    rows = gen.generate(num_issues=num_issues)
    print(f"  generated {len(rows)} note rows, {len(deferred.contexts)} LLM calls queued")

    print(f"Step 2/6: authoring {len(deferred.contexts)} notes in parallel (workers={workers}) ...")
    notes = _parallel_author_notes(deferred.contexts, workers=workers)

    print("Step 3/6: patching notes into rows ...")
    _patch_notes(rows, notes)

    local_path = Path("/tmp/fsisim_g001_issue.parquet")
    print(f"Step 4/6: writing parquet to {local_path} ...")
    _write_parquet(rows, local_path)
    print(f"  parquet size: {local_path.stat().st_size:,} bytes")

    staging_dir = f"{cfg.manuals_volume_path.replace('/manuals', '/_staging')}"
    staging_file = f"{staging_dir}/g001_issue.parquet"
    print(f"Step 5/6: uploading parquet to volume {staging_file} ...")
    # The staging dir lives next to /manuals/; ensure parent volume exists.
    # We piggyback on the existing manuals volume by using a subfolder of the same volume.
    staging_in_manuals = f"{cfg.manuals_volume_path}/_staging/g001_issue.parquet"
    _upload_to_volume(w, local_path, staging_in_manuals)
    print(f"  uploaded to {staging_in_manuals}")

    warehouse_id = _pick_warehouse(w)

    target = cfg.issue_table_fqn
    ctas = (
        f"CREATE OR REPLACE TABLE {target} AS "
        f"SELECT * FROM read_files("
        f"  '{staging_in_manuals}', "
        f"  format => 'parquet'"
        f")"
    )
    print(f"Step 6/6: CTAS into {target} ...")
    _execute_sql(w, warehouse_id, ctas)

    _execute_sql(
        w,
        warehouse_id,
        f"ALTER TABLE {target} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)",
    )

    # Sanity row count
    resp = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=f"SELECT COUNT(*) AS n FROM {target}",
        wait_timeout="30s",
    )
    n = resp.result.data_array[0][0] if resp.result and resp.result.data_array else "?"
    print(f"  wrote {n} rows to {target}")
    print("Done.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--num-issues", type=int, default=500)
    p.add_argument("--workers", type=int, default=16)
    args = p.parse_args()
    main(num_issues=args.num_issues, workers=args.workers)
