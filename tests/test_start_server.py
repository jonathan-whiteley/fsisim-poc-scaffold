"""Sanity-check that start_server builds the FastAPI app without errors.

Note: These tests skip when mlflow.genai.agent_server is not available (dev environment).
      In production, mlflow is installed and tests run fully.
      Basic syntax is verified via: python -m py_compile agent_server/start_server.py
"""
import pytest


def test_main_is_callable():
    pytest.importorskip("mlflow.genai.agent_server")
    from agent_server import start_server
    assert callable(start_server.main)


def test_app_module_attribute_exists():
    """`app` must be a module-level FastAPI instance so uvicorn workers can import it."""
    pytest.importorskip("mlflow.genai.agent_server")
    from agent_server import start_server
    assert start_server.app is not None
