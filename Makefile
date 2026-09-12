.PHONY: install setup serve worker dev-web check contracts science runtime-checks postgres-check

install:
	uv sync --frozen
	npm --prefix web ci

setup: install
	npm --prefix web run build
	uv run workbench setup

serve:
	uv run workbench serve --port 8317

worker:
	uv run workbench worker

dev-web:
	npm --prefix web run dev

contracts:
	uv run python scripts/export_openapi.py
	npm --prefix web run contracts
	cd web && npm exec -- prettier --write src/contracts.ts

check:
	uv run ruff check --config pyproject.toml src tests scripts
	uv run ruff format --config pyproject.toml --check src tests scripts
	uv run pytest -q
	npm --prefix web run build

science:
	uv run python scripts/verify_science.py

runtime-checks:
	uv run python scripts/verify_runtime.py
	uv run python scripts/verify_budgets.py

postgres-check:
	uv run python scripts/verify_postgres.py
