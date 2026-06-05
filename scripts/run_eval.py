"""DAB job entrypoint: run mlflow.genai.evaluate against FSISIM personas.

Usage in databricks.yml job task:
    python_file: scripts/run_eval.py
    parameters:
      - "--personas-file"
      - "agent_server.personas"
"""
from __future__ import annotations
import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--personas-file",
        default="agent_server.personas",
        help="Python module path holding the PERSONAS list",
    )
    parser.add_argument("--max-turns", type=int, default=5)
    args = parser.parse_args()

    # Import here so a misconfigured deploy still gives a usable --help.
    from agent_server.evaluate_agent import evaluate
    evaluate(personas_module_path=args.personas_file, max_turns=args.max_turns)
    return 0


if __name__ == "__main__":
    sys.exit(main())
