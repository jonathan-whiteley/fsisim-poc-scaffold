"""Log the FSISIM agent to MLflow, register to UC, deploy as a serving endpoint.

Uses mlflow.pyfunc.log_model with python_model=<file path>. MLflow does NOT
instantiate the agent here; it serializes the source file and re-executes it
inside the serving container, where only pip_requirements packages are
installed (no local pyspark conflicts).

After registration, databricks.agents.deploy creates or updates the agent
serving endpoint named agents_<catalog>-<schema>-<model_name>.
"""
from __future__ import annotations
import mlflow
from databricks.agents import deploy
from mlflow.models.resources import (
    DatabricksFunction, DatabricksServingEndpoint, DatabricksVectorSearchIndex,
)

from config import Config


PIP_REQUIREMENTS = [
    "mlflow>=2.18.0",
    "databricks-agents>=0.10.0",
    "databricks-langchain>=0.4.0",
    "langgraph>=0.2.0",
    "langchain-core>=0.3.0",
    "databricks-sdk>=0.30.0",
    "unitycatalog-ai>=0.1.0",
    "unitycatalog-langchain>=0.1.0",
]


def main() -> None:
    cfg = Config()
    mlflow.set_registry_uri("databricks-uc")

    resources = [
        DatabricksServingEndpoint(endpoint_name=cfg.llm_endpoint),
        DatabricksFunction(function_name=cfg.search_past_issues_fqn),
        DatabricksFunction(function_name=cfg.search_technical_manuals_fqn),
        DatabricksVectorSearchIndex(index_name=cfg.issue_index_fqn),
        DatabricksVectorSearchIndex(index_name=cfg.manual_index_fqn),
    ]

    print("Logging agent to MLflow ...")
    with mlflow.start_run(run_name="fsisim_agent_scaffold"):
        logged = mlflow.pyfunc.log_model(
            python_model="agent/agent.py",
            artifact_path="agent",
            pip_requirements=PIP_REQUIREMENTS,
            resources=resources,
            code_paths=["config.py", "agent/prompts.py"],
        )
        print(f"  logged at {logged.model_uri}")

    model_fqn = f"{cfg.catalog}.{cfg.schema}.fsisim_agent"
    print(f"Registering to {model_fqn} ...")
    registered = mlflow.register_model(model_uri=logged.model_uri, name=model_fqn)
    print(f"  registered version {registered.version}")

    print(f"Deploying serving endpoint for {model_fqn} v{registered.version} ...")
    deployment = deploy(
        model_name=model_fqn,
        model_version=int(registered.version),
        scale_to_zero=True,
    )
    print(f"  endpoint: {deployment.endpoint_name}")
    print(f"  view: {deployment.endpoint_url}")
    print(
        "Endpoint will take 5-15 minutes to come online. Check the Serving "
        "Endpoints page in the workspace UI for readiness."
    )


if __name__ == "__main__":
    main()
