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
