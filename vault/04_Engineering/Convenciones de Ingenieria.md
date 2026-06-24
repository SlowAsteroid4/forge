---
type: engineering
tags: [convenciones, proceso]
---
# Convenciones de Ingeniería

## El loop de trabajo (protocolo del proyecto)
1 sesión de Claude Code = 1 Work Package. El **chat maestro** (arquitecto) redacta el prompt con decisiones cerradas; Claude Code ejecuta y entrega **Handoff Report** con salidas reales de BD; el chat maestro aprueba/ajusta/bloquea. Reglas duras:
- **PASO 0 de auditoría obligatorio** antes de construir (leer código real + queries de diagnóstico). Saltárselo causó el bug del WP-20 ([[INC-009 WIP inflado e In Code]]).
- **Backup de `forge.db` + branch + checkpoint commit** antes de WPs que escriben.
- **Validación con salidas reales** (no "los tests pasan"): demos sobre datos reales + **cruce manual** de los números clave ([[Patrones que Funcionan]]).
- Los **casos golden del PM van como criterio de aceptación literal** en el prompt ([[Golden Cases]]).

## Código
- Migraciones **siempre aditivas** (Alembic); SQL documentado en `docs/migrations/wpNN.sql`. SQLite no tiene DDL transaccional — las migraciones deben ser idempotentes (`PRAGMA table_info` check).
- Tests: pytest (≈490+ verdes al cierre de Ops); tests de integración golpean la API con TestClient; anti-regresión de inmutabilidad (`cp_approved_at` count) y de no-escritura en cada WP.
- Frontend: tipos TS espejo exacto de los schemas Pydantic; `tsc --noEmit` + `npm run build` como gate; shadcn parcial (no Input/Label — HTML nativo + Tailwind).
- audit_log para toda escritura admin; datos sensibles enmascarados.

Enlaces: [[Historial de Work Packages]] · [[Arquitectura del Sistema]]
