.PHONY: help install dev test lint format clean sync seed run

help: ## Mostrar esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Instalar dependencias (backend)
	cd backend && uv sync

dev: ## Arrancar servidor de desarrollo
	cd backend && uv run uvicorn forge.main:app --reload --port 8000

test: ## Correr todos los tests
	cd backend && uv run pytest

test-unit: ## Correr solo tests unitarios
	cd backend && uv run pytest tests/unit -v

test-cov: ## Tests con reporte de cobertura
	cd backend && uv run pytest --cov=forge --cov-report=html --cov-report=term

lint: ## Linting con ruff
	cd backend && uv run ruff check src/forge

format: ## Formatear código con ruff
	cd backend && uv run ruff format src/forge

typecheck: ## Type checking con mypy
	cd backend && uv run mypy src/forge

clean: ## Limpiar archivos generados
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/htmlcov backend/.pytest_cache backend/.ruff_cache
	rm -f backend/forge.db

sync: ## Sincronizar con Jira
	cd backend && uv run forge sync

seed: ## Cargar datos seed
	cd backend && uv run forge seed

recalc: ## Recalcular motor completo
	cd backend && uv run forge recalc

db-init: ## Inicializar base de datos
	cd backend && uv run alembic upgrade head

db-reset: ## Resetear base de datos (CUIDADO: borra todo)
	cd backend && rm -f forge.db && uv run alembic upgrade head && uv run forge seed

shell: ## Abrir shell interactivo con contexto cargado
	cd backend && uv run ipython -i scripts/shell_context.py
