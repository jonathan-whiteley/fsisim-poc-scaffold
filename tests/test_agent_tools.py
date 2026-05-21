from agent.agent import build_agent_config


def test_agent_config_lists_both_tools():
    cfg = build_agent_config()
    fns = {t["name"] for t in cfg["uc_functions"]}
    assert "jdub_demo.fsisim_issue_ai_gold.search_past_issues" in fns
    assert "jdub_demo.fsisim_issue_ai_gold.search_technical_manuals" in fns


def test_agent_config_uses_sonnet_endpoint():
    cfg = build_agent_config()
    assert cfg["llm_endpoint"] == "databricks-claude-sonnet-4-5"


def test_agent_config_includes_system_prompt():
    cfg = build_agent_config()
    assert "search_past_issues" in cfg["system_prompt"]
    assert "MOCK DATA" in cfg["system_prompt"]


def test_agent_config_uses_config_module_for_function_fqns(monkeypatch):
    """Env-var overrides on Config should flow into the agent config."""
    monkeypatch.setenv("FSISIM_CATALOG", "poc_data")
    cfg = build_agent_config()
    fns = {t["name"] for t in cfg["uc_functions"]}
    assert "poc_data.fsisim_issue_ai_gold.search_past_issues" in fns
    assert "poc_data.fsisim_issue_ai_gold.search_technical_manuals" in fns
