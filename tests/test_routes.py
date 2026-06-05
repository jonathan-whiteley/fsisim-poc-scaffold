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
