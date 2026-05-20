# fsisim-poc-scaffold

Scaffold build of the FSISIM Technician Issue Resolution Agent. See
`~/Desktop/Vault/Work/Projects/fsisim-poc-scaffold/Project.md` for the spec
and `Implementation-Plan.md` for the build plan.

## Quickstart

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
pytest
```

## Forking for production

All UC names live in `config.py`. Change `CATALOG` to your target catalog
and rerun `infra/setup_catalog.py` and `infra/setup_vector_search.py`.
