# Guía de contribución

## Flujo de trabajo

1. Crea tu rama desde `develop` siguiendo la convención de nombres
2. Haz commits pequeños y descriptivos (Conventional Commits)
3. Abre un PR hacia `develop`
4. Espera la revisión de al menos 1 persona
5. Una vez aprobado y con CI verde, se hace merge
6. La rama se elimina automáticamente después del merge

## Convención de nombres de ramas

```
feature/descripcion-corta       — nueva funcionalidad
fix/descripcion-del-bug         — corrección de bug
hotfix/descripcion-urgente      — parche urgente (va a main y develop)
chore/descripcion               — deps, config, refactor
docs/descripcion                — solo documentación
refactor/descripcion            — restructuración sin cambio de comportamiento
test/descripcion                — solo tests
```

**Regla:** todo en `kebab-case` (minúsculas + guiones). Sin mayúsculas ni `camelCase`.

## Convención de commits (Conventional Commits)

```
tipo(scope): descripción corta

[cuerpo opcional]

[footer opcional]
```

Tipos válidos: `feat`, `fix`, `hotfix`, `chore`, `docs`, `refactor`, `test`, `ci`

Ejemplos:

```
feat(auth): agregar login con Google
fix(api): corregir error 404 en endpoint de usuarios
chore(deps): actualizar dependencias a versiones estables
docs(readme): actualizar instrucciones de setup
refactor(engine): extraer lógica de CP a función pura
test(etl): agregar tests para quality_metrics
```

## ¿A qué rama hago el PR?

| Tipo de trabajo      | Rama destino           |
|----------------------|------------------------|
| Feature nueva        | `develop`              |
| Bug fix              | `develop`              |
| Hotfix urgente       | `main` **y** `develop` |
| Release (QA)         | `staging` (desde `develop`) |
| Release (producción) | `main` (desde `staging`) |

## Setup local

```bash
# Backend
cd backend
uv sync
cp .env.example .env   # llenar credenciales Jira + ENCRYPTION_KEY
make db-init
make dev               # servidor en :8000

# Frontend
cd frontend
npm install
npm run dev            # servidor en :3000
```

Ver `backend/README.md` para más detalle.

## Comandos de calidad (correr antes de abrir un PR)

```bash
cd backend
make lint              # ruff check
make typecheck         # mypy strict
make test-unit         # tests rápidos (sin DB real)
make test              # suite completa
```

## Reglas de protección

| Rama       | Restricciones                                             |
|------------|-----------------------------------------------------------|
| `main`     | Solo PRs · 1 reviewer · CI verde · sin push directo       |
| `staging`  | Solo PRs · 1 reviewer · CI verde · sin push directo       |
| `develop`  | Solo PRs · 1 reviewer · CI verde recomendado              |

Nadie hace `push --force` a ramas permanentes.
