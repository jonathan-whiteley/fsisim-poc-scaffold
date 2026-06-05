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
        with patch("agent_server.routes._fetch_thread_owner", return_value="tech@flightsafety.com"):
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
