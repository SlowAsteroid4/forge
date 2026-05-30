# Forge Backend

Backend de Forge: sistema de medición y gamificación para equipos de desarrollo.

---

## Stack Técnico

- **Python**: 3.11
- **Web Framework**: FastAPI 0.110+
- **ORM**: SQLAlchemy 2.0
- **Package Manager**: uv
- **Base de Datos**: SQLite (MVP) → PostgreSQL (v0.4+)
- **HTTP Client**: httpx (async)

---

## Setup (Primeros Pasos)

### 1. Instalar uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clonar y configurar

```bash
cd forge/backend

# Instalar dependencias
uv sync

# Copiar .env de ejemplo
cp .env.example .env
```

### 3. Configurar Jira API Token

**⚠️ Paso crítico para UC-01**

1. Ve a: https://id.atlassian.com/manage-profile/security/api-tokens
2. Clic en **"Create API token"**
3. Dale un nombre (ej: "Forge Sync")
4. **Copia el token** (solo se muestra una vez)
5. Edita `.env` y pega el token:

```bash
JIRA_INSTANCE_URL=https://beyapsi-org.atlassian.net
JIRA_USER_EMAIL=tu-email@yapsi.com
JIRA_API_TOKEN=tu-token-aqui
```

### 4. Generar clave de cifrado

```bash
# Generar encryption key
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Copiar el output y pegarlo en .env:
# ENCRYPTION_KEY=el-output-del-comando-anterior
```

### 5. Inicializar base de datos

```bash
# Crear tablas
uv run alembic upgrade head

# Cargar seeds (opcional)
uv run forge seed
```

### 6. Probar conexión a Jira

```bash
uv run forge test-jira
```

Deberías ver:
```
✅ Conexión exitosa!
Usuario: Tu Nombre
Account ID: 5b10ac8d82e05b22cc7d4ef5
Instancia: https://beyapsi-org.atlassian.net
```

---

## Comandos CLI

```bash
# Probar conexión a Jira
uv run forge test-jira

# Sincronizar issues de Jira (UC-01)
uv run forge sync

# Sincronizar con JQL custom
uv run forge sync --jql "project = SIMPL AND updated >= -7d"

# Ver info del sistema
uv run forge info

# Cargar seeds
uv run forge seed
```

---

## Desarrollo

### Arrancar servidor

```bash
# Con reload automático
uv run uvicorn forge.main:app --reload --port 8000

# O con el Makefile (desde raíz)
make dev
```

API disponible en:
- **Docs interactivos**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

### Tests

```bash
# Todos los tests
uv run pytest

# Solo unit tests
uv run pytest tests/unit -v

# Con cobertura
uv run pytest --cov=forge --cov-report=html
```

### Linting y format

```bash
# Linting
uv run ruff check src/forge

# Format
uv run ruff format src/forge

# Type checking
uv run mypy src/forge
```

---

## Estructura del Código

```
src/forge/
├── core/              # Config, exceptions, security, time utils
├── db/
│   ├── models/        # SQLAlchemy models (18 tablas)
│   ├── base.py        # Declarative Base
│   └── session.py     # Engine y SessionLocal
├── schemas/           # Pydantic DTOs (TODO)
├── repositories/      # Data access layer (TODO)
├── engine/            # Motor puro de cálculo (TODO)
│   ├── multipliers/
│   └── achievement_conditions/
├── etl/               # Jira integration
│   ├── jira_client.py
│   ├── time_metrics.py
│   ├── quality_metrics.py
│   └── sync_orchestrator.py
├── services/          # Business logic (TODO)
├── api/
│   └── routers/
│       └── integrations.py  # UC-01: Jira endpoints
├── scripts/
│   └── cli.py         # Typer CLI
└── main.py            # FastAPI app
```

---

## API Endpoints (UC-01)

### POST /api/integrations/jira/test-connection

Probar conexión a Jira.

**Response:**
```json
{
  "status": "connected",
  "user": "Tu Nombre",
  "account_id": "5b10ac8d82e05b22cc7d4ef5",
  "instance": "https://beyapsi-org.atlassian.net"
}
```

### POST /api/integrations/jira/sync

Sincronizar issues de Jira.

**Query Params:**
- `jql` (opcional): Query JQL personalizada

**Response:**
```json
{
  "status": "success",
  "stats": {
    "epics_created": 5,
    "epics_updated": 12,
    "stories_created": 23,
    "stories_updated": 45,
    "subtasks_created": 89,
    "subtasks_updated": 134,
    "errors": []
  }
}
```

### GET /api/integrations/jira/status

Estado de la integración.

---

## Migraciones de Base de Datos

```bash
# Crear migración automática
uv run alembic revision --autogenerate -m "descripcion"

# Aplicar migraciones
uv run alembic upgrade head

# Ver historial
uv run alembic history

# Rollback
uv run alembic downgrade -1
```

---

## Troubleshooting

### Error: "Invalid credentials" al conectar Jira

- Verifica que `JIRA_USER_EMAIL` sea tu email de Atlassian
- Regenera el API token en https://id.atlassian.com/manage-profile/security/api-tokens
- Asegúrate de NO usar tu contraseña, debe ser el API token

### Error: "Table doesn't exist"

```bash
# Resetear DB
rm forge.db
uv run alembic upgrade head
```

### Error: Import de módulos

```bash
# Reinstalar deps
uv sync
```

---

## Próximos Pasos (Post-MVP)

1. ✅ UC-01: Jira integration
2. 🚧 Engine completo (CP + SP calculation)
3. 🚧 UC-02: Dashboard general
4. 🚧 UC-04: Aprobación de CP L/XL
5. 🚧 Arena API (UC-09 a UC-15)

---

**Contacto:** Saúl (PM) | Equipo Yapsi
