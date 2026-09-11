# Contributing / Contribuindo

Use a dedicated branch and add each behavior through Red → Green → Refactor. Do not include API
keys, credentials, production data, or generated local environments.

Use uma branch dedicada e adicione cada comportamento com Red → Green → Refactor. Não inclua API
keys, credenciais, dados de produção ou ambientes locais gerados.

```bash
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
.venv/bin/pytest --cov=viapost --cov-report=term-missing
.venv/bin/python -m build
.venv/bin/twine check dist/*
```

The vendored `src/viapost/openapi.yaml` must stay semantically synchronized with the published
contract. Run `python scripts/check_contract.py` before proposing a contract-related change.
