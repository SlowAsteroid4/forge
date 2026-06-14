---
type: system
tags: [arquitectura, stack]
---
# Arquitectura del Sistema

## Stack
- **Backend**: FastAPI + SQLAlchemy + Alembic + SQLite (`backend/forge.db`; Postgres como destino futuro [INFERENCIA por el uso de Alembic y tipos portables]). Tooling: `uv`, `ruff`, `mypy` (baseline ~56 errores pre-existentes en `cli.py`/`main.py` — los WPs exigen 0 errores *nuevos*).
- **Frontend**: Next.js 16 + React 19 + Tailwind, en `frontend/`. Server Components con `force-dynamic` para vistas de datos.
- **Repo**: `github.com/SlowAsteroid4/forge` — 37 commits, monorepo backend+frontend. ⚠️ Branch por defecto = `feat/wp18-arena-login` (no master) — el flujo de ramas se desvió del protocolo en los últimos WPs.

## Capas del backend (`backend/src/forge/`)
`etl/` (sync Jira + time_metrics) → `db/models/` → `services/` (13 servicios + `engine/`) → `schemas/` (Pydantic) → `api/routers/` → `main.py`. El **engine** (orchestrator, sp_calculator, forecast) es el único que recalcula SP — los services lo invocan, nunca calculan SP a mano.

## Decisiones estructurales clave
- **Una sola fuente por concepto**: `CANONICAL_STATUS_MAP` (`services/canonical_status.py`), `_WIP_STATES` (`pulse_service.py`), buckets de tiempo (`etl/time_metrics.py`). Prohibido duplicarlas.
- **Read-only por diseño**: Pulso, Analítica, Forecast y Costos no escriben negocio (demo de no-escritura en cada WP). Escriben solo: aprobación CP, cierres, penalizaciones, players admin — todo a `audit_log`.
- **Clasificaciones de Forge viven en campos que el sync no pisa** ([[ADR-008 Clasificaciones durables]]).

## Operación (Makefile)
`make sync` (ventana −14d) · `make sync-full` (backfill) · `make recalc --all-cycles` · `make seed-epic-kinds` · `make test` · `make typecheck`. Backups manuales: `cp forge.db forge.db.backup_wpNN_fecha` antes de cada WP destructivo.

Enlaces: [[ETL Jira - Conocimiento Critico]] · [[Convenciones de Ingenieria]]
