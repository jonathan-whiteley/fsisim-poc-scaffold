import os
from dataclasses import dataclass, field


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


@dataclass
class Config:
    catalog: str = field(default_factory=lambda: _env("FSISIM_CATALOG", "jdub_demo"))
    schema: str = field(default_factory=lambda: _env("FSISIM_SCHEMA", "fsisim_issue_ai_gold"))
    issue_table: str = field(default_factory=lambda: _env("FSISIM_ISSUE_TABLE", "g001_issue"))
    manual_table: str = field(default_factory=lambda: _env("FSISIM_MANUAL_TABLE", "g001_manual_chunks"))
    volume_name: str = field(default_factory=lambda: _env("FSISIM_VOLUME", "manuals"))
    vs_endpoint: str = field(default_factory=lambda: _env("FSISIM_VS_ENDPOINT", "jdub-demo-vs"))
    llm_endpoint: str = field(
        default_factory=lambda: _env("FSISIM_LLM_ENDPOINT", "databricks-claude-sonnet-4-5")
    )
    agent_uc_function_schema: str = field(
        default_factory=lambda: _env("FSISIM_AGENT_FN_SCHEMA", "")
    )

    @property
    def issue_table_fqn(self) -> str:
        return f"{self.catalog}.{self.schema}.{self.issue_table}"

    @property
    def manual_table_fqn(self) -> str:
        return f"{self.catalog}.{self.schema}.{self.manual_table}"

    @property
    def issue_index_fqn(self) -> str:
        return f"{self.catalog}.{self.schema}.issue_history_index"

    @property
    def manual_index_fqn(self) -> str:
        return f"{self.catalog}.{self.schema}.manual_knowledge_index"

    @property
    def manuals_volume_path(self) -> str:
        return f"/Volumes/{self.catalog}/{self.schema}/{self.volume_name}"

    @property
    def search_past_issues_fqn(self) -> str:
        return f"{self.catalog}.{self.schema}.search_past_issues"

    @property
    def search_technical_manuals_fqn(self) -> str:
        return f"{self.catalog}.{self.schema}.search_technical_manuals"
