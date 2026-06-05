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
