.PHONY: dev db-init db-reset seed seed-epic-kinds sync sync-full prune prune-apply test test-unit test-cov test-jira recalc recalc-all shell lint format typecheck cycle-generate cycles-list sprint-generate

dev:
	uv run uvicorn forge.main:app --reload --port 8000

db-init:
	uv run alembic upgrade head

db-reset:
	uv run alembic downgrade base && uv run alembic upgrade head

seed:
	uv run forge seed

seed-epic-kinds:
	uv run forge seed-epic-kinds

sync:
	uv run forge sync

sync-full:
	@echo "⚠️  Backfill completo — puede tardar varios minutos"
	uv run forge sync --full

prune:
	@echo "🔍 Dry-run: muestra qué se borraría (no borra nada)"
	uv run forge prune

prune-apply:
	@echo "🧹 Reconcilia borrados de Jira — BORRA registros obsoletos"
	uv run forge prune --apply

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

recalc-all:
	uv run forge recalc --all-cycles --force

cycle-generate:
	uv run forge cycle-generate

cycles-list:
	uv run forge cycles-list

sprint-generate:
	@echo "DEPRECATED: usar make cycle-generate"
	uv run forge cycle-generate

shell:
	uv run forge shell

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy src/forge
