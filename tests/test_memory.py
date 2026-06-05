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
