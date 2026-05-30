# Forge — Sistema de Medición y Gamificación para Equipos de Desarrollo

**Versión:** MVP v0.1 (Local)  
**Organización:** Yapsi / SimplyBe  
**Fecha:** Mayo 2026

---

## ¿Qué es Forge?

Forge es una plataforma dual que combina medición de desempeño y gamificación para equipos de desarrollo de software. Funciona como dos productos hermanos sobre el mismo motor:

- **Forge Ops** — Consola operativa para PMs, Tech Leads y Dirección (dashboards, forecast, costos, análisis)
- **Forge Arena** — Experiencia lúdica para el equipo (perfil RPG, leaderboards, achievements, tienda de canjes)

---

## Estructura del Monorepo

```
forge/
├── backend/          # Python + FastAPI + SQLAlchemy
│   ├── src/forge/    # Código fuente
│   ├── tests/        # Tests unitarios, integración y e2e
│   ├── seed/         # Catálogos iniciales (YAML)
│   ├── scripts/      # CLI commands
│   └── alembic/      # Migraciones de BD
│
└── frontend/         # Next.js + React + TypeScript (TBD)
```

---

## Stack Técnico (Backend)

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.11 |
| Web Framework | FastAPI 0.110+ |
| ORM | SQLAlchemy 2.0 |
| Migraciones | Alembic |
| Validación | Pydantic 2 |
| Base de Datos | SQLite (MVP) → PostgreSQL (v0.4+) |
| HTTP Client | httpx |
| Package Manager | uv |
| Tests | pytest + pytest-asyncio + pytest-cov |
| Linting | ruff + mypy |

---

## Setup Rápido (Backend)

**Prerrequisitos:**
- Python 3.11+
- uv (package manager): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Cuenta de Jira Cloud con API token

**Instalación:**

```bash
cd forge/backend

# Instalar dependencias
uv sync

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de Jira

# Inicializar base de datos
uv run alembic upgrade head

# Cargar catálogos seed
uv run forge seed

# Arrancar servidor de desarrollo
uv run uvicorn forge.main:app --reload --port 8000
```

**API disponible en:** `http://localhost:8000`  
**Docs interactivas:** `http://localhost:8000/docs`

---

## Comandos CLI

```bash
# Sincronizar con Jira (manual)
uv run forge sync

# Recalcular motor completo
uv run forge recalc --sprint-id 1

# Cargar datos seed
uv run forge seed --catalogs --players

# Crear nuevo sprint
uv run forge sprint create --name "Sprint 2026-W20" --start 2026-05-19 --end 2026-05-30
```

---

## Tests

```bash
# Todos los tests
uv run pytest

# Solo unit tests (rápidos)
uv run pytest tests/unit -v

# Con cobertura
uv run pytest --cov=forge --cov-report=html

# E2E (requiere BD limpia)
uv run pytest tests/e2e -v
```

---

## Casos de Uso Implementados (MVP)

| ID | Caso de Uso | Estado |
|---|---|---|
| UC-01 | Conectar Jira y sincronización | ✅ |
| UC-02 | Dashboard general del sprint | 🚧 |
| UC-03 | Filtro global por proyecto | 🚧 |
| UC-04 | Aprobación de CP L/XL | 🚧 |
| UC-05 | Asignar MVP del sprint | 🚧 |
| UC-06 | Aplicar penalización manual | 🚧 |
| UC-07 | Forecast con 3 escenarios | 🚧 |
| UC-09 | Login player a Arena | 🚧 |
| UC-10 | Mi perfil de player | 🚧 |
| UC-11 | Leaderboard global | 🚧 |
| UC-12 | Detalle de mi SP | 🚧 |
| UC-13 | Achievement wall | 🚧 |
| UC-14 | Canjear SP en tienda | 🚧 |
| UC-15 | Elegir clase y avatar | 🚧 |

---

## Documentación

- [Arquitectura del Backend](backend/docs/architecture.md)
- [Motor de Complejidad (JPDS v2.0)](backend/docs/motor-jpds-v2.md)
- [Guía de Integración con Jira](backend/docs/jira-integration.md)
- [Catálogos de Gamificación](backend/docs/catalogs.md)

---

## Licencia y Uso

Este proyecto es propiedad de Yapsi / SimplyBe. Uso interno exclusivamente.

---

**Contacto:** Saúl (PM) | Equipo de Desarrollo Yapsi
