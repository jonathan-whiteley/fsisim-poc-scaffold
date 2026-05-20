import os
import pytest
from config import Config


def test_default_catalog_is_jdub_demo():
    cfg = Config()
    assert cfg.catalog == "jdub_demo"


def test_default_schema_is_fsisim_issue_ai_gold():
    cfg = Config()
    assert cfg.schema == "fsisim_issue_ai_gold"


def test_issue_table_fqn():
    cfg = Config()
    assert cfg.issue_table_fqn == "jdub_demo.fsisim_issue_ai_gold.g001_issue"


def test_manual_table_fqn():
    cfg = Config()
    assert cfg.manual_table_fqn == "jdub_demo.fsisim_issue_ai_gold.g001_manual_chunks"


def test_volume_path():
    cfg = Config()
    assert cfg.manuals_volume_path == "/Volumes/jdub_demo/fsisim_issue_ai_gold/manuals"


def test_env_override_for_catalog(monkeypatch):
    monkeypatch.setenv("FSISIM_CATALOG", "poc_data")
    cfg = Config()
    assert cfg.catalog == "poc_data"
    assert cfg.issue_table_fqn == "poc_data.fsisim_issue_ai_gold.g001_issue"


def test_llm_endpoint_default():
    cfg = Config()
    assert cfg.llm_endpoint == "databricks-claude-sonnet-4-5"


def test_vs_endpoint_default():
    cfg = Config()
    assert cfg.vs_endpoint == "jdub-demo-vs"
