# 🚀 Setup de Forge - Paso a Paso

Sigue estos pasos **en orden** para levantar el proyecto.

---

## 1️⃣ Instalar uv (si no lo tienes)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Reinicia tu terminal después de instalarlo.

---

## 2️⃣ Ir al directorio backend

```bash
cd forge/backend
```

---

## 3️⃣ Instalar dependencias

```bash
uv sync
```

Esto instala todas las deps de `pyproject.toml`. Toma ~30 segundos.

---

## 4️⃣ Configurar variables de entorno

```bash
cp .env.example .env
```

Ahora edita `.env` con tu editor favorito:

```bash
nano .env
# o
code .env
```

**Campos CRÍTICOS a completar:**

### a) Jira Instance URL
```bash
JIRA_INSTANCE_URL=https://beyapsi-org.atlassian.net
```
(Reemplaza con tu instancia real de Jira)

### b) Tu email de Jira
```bash
JIRA_USER_EMAIL=tu-email@yapsi.com
```

### c) API Token de Jira

**⚠️ Este es el paso más importante:**

1. Ve a: https://id.atlassian.com/manage-profile/security/api-tokens
2. Clic en **"Create API token"**
3. Dale un nombre: "Forge Sync"
4. **Copia el token** (solo aparece una vez)
5. Pégalo en el .env:

```bash
JIRA_API_TOKEN=ATATT3xFfGF0X...
```

### d) Encryption Key

Genera una clave para cifrar datos sensibles:

```bash
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copia el output y pégalo:

```bash
ENCRYPTION_KEY=el-output-del-comando-anterior
```

---

## 5️⃣ Inicializar base de datos

```bash
uv run alembic upgrade head
```

Esto crea todas las 18 tablas en `forge.db` (SQLite).

---

## 6️⃣ Verificar setup

```bash
uv run python scripts/verify_setup.py
```

Deberías ver:

```
✅ Archivo .env encontrado
✅ Base de datos inicializada
✅ Configuración Jira encontrada
```

---

## 7️⃣ Probar conexión a Jira

```bash
uv run forge test-jira
```

**Si todo funciona:**

```
✅ Conexión exitosa!
Usuario: Tu Nombre
Account ID: 5b10ac8d82e05b22cc7d4ef5
Instancia: https://beyapsi-org.atlassian.net
```

**Si falla:**
- Verifica el API token (regénera uno nuevo si es necesario)
- Confirma que el email es correcto
- Asegúrate de que la instancia URL no tenga `/` al final

---

## 8️⃣ Sincronizar issues de Jira (UC-01)

```bash
uv run forge sync
```

Esto importará:
- Epics
- Stories
- Subtasks

Con métricas de tiempo y calidad extraídas del changelog.

---

## 9️⃣ Arrancar servidor de desarrollo

```bash
uv run uvicorn forge.main:app --reload --port 8000
```

O desde la raíz:

```bash
make dev
```

**API disponible en:**
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

---

## 🧪 Correr tests

```bash
# Todos los tests
uv run pytest

# Solo unit tests
uv run pytest tests/unit -v

# Con cobertura
uv run pytest --cov=forge --cov-report=html
```

---

## 📊 Endpoints de UC-01

### POST /api/integrations/jira/test-connection

Probar conexión.

### POST /api/integrations/jira/sync

Sincronizar issues (default: últimas 2 semanas).

**Query params:**
- `jql` (opcional): Query JQL personalizada

Ejemplo:
```bash
curl -X POST "http://localhost:8000/api/integrations/jira/sync?jql=project%20=%20SIMPL%20AND%20updated%20%3E=%20-7d"
```

### GET /api/integrations/jira/status

Estado de la integración.

---

## 🐛 Troubleshooting

### "Invalid credentials"

Regenera el API token:
1. https://id.atlassian.com/manage-profile/security/api-tokens
2. Revoca el token anterior
3. Crea uno nuevo
4. Actualiza `.env`

### "Table doesn't exist"

```bash
rm forge.db
uv run alembic upgrade head
```

### Imports fallan

```bash
uv sync
```

### Ver estructura de tablas

```bash
sqlite3 forge.db
.tables
.schema players
.quit
```

---

## ✨ Próximos Pasos (Desarrollo)

**Inmediato:**
- [ ] Implementar engine de CP/SP (motor de cálculo)
- [ ] Crear más routers (dashboard, approvals, etc.)
- [ ] Completar seeds YAML (classes, avatars, buffs, etc.)
- [ ] Tests de integración para ETL

**UC-02 a UC-15:**
- [ ] Dashboard general
- [ ] Aprobación de CP L/XL
- [ ] Arena API (login, profile, leaderboard)
- [ ] Achievement engine
- [ ] Shop y canjes

---

**¿Dudas?** Revisa:
- `backend/README.md` - Documentación del backend
- `README.md` raíz - Overview del proyecto
- `seed/README.md` - Guía de seeds

---

**Hecho con ❤️ por Claude para el equipo Yapsi**
