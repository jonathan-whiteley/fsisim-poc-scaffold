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
