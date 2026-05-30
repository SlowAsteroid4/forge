.PHONY: dev db-init db-reset seed sync test test-unit test-cov test-jira recalc shell lint format typecheck sprint-generate

dev:
	uv run uvicorn forge.main:app --reload --port 8000

db-init:
	uv run alembic upgrade head

db-reset:
	uv run alembic downgrade base && uv run alembic upgrade head

seed:
	uv run forge seed

sync:
	uv run forge sync

test:
	uv run pytest

test-unit:
	uv run pytest tests/unit -v

test-cov:
	uv run pytest --cov=forge --cov-report=html --cov-report=term

test-jira:
	uv run forge test-jira

recalc:
	uv run forge recalc

sprint-generate:
	uv run forge sprint-generate

shell:
	uv run forge shell

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy src/forge
