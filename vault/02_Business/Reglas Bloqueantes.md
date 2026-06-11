---
type: domain
tags: [negocio, reglas]
---
# Reglas Bloqueantes (validadas en código)

Reglas de negocio que el backend **rechaza activamente** (no convenciones blandas):

1. **CP inmutable post-aprobación** — `CPImmutableError`. Invariante verificada en cada WP.
2. **SP append-only** — reversals por INSERT opuesto, jamás UPDATE del valor ([[Economia CP-SP]]).
3. **Piso 0 de SP** — no se puede penalizar más de lo ganado en la subtask; −100% (D09/D14) topa exacto en 0.
4. **Razones mínimas** — penalizaciones ≥30 caracteres; otras acciones admin ≥20.
5. **No penalizar en ciclo cerrado** (salvo flujo de apelación).
6. **MVP del Mes solo entre MVPs semanales** (AC-17.4) + gate ≥4 ciclos cerrados con MVP.
7. **Ventanas de edición**: 24h hábiles (cierre semanal), 72h hábiles (mensual) — horas hábiles MX.
8. **Solo 1 ciclo activo**.
9. **Players inactivos no entran a Arena** (login rechazado).
10. **Whitelist de edición en players** — solo campos Forge (costos, type, flags, area); campos de Jira (display_name, jira_account_id) rechazados con `RuleViolationError` ([[ADR-008 Clasificaciones durables]]).
11. **Límites de WIP por área**: BE=3, FE=3, DESIGN=4, DB=5 — semáforo, no bloqueo duro ([[Definicion de WIP]]).
12. **Costos solo en vistas admin** — enmascarados en audit_log (`"<changed>"`), guard `require_cost_access()` (placeholder hasta auth real).

Enlaces: [[Golden Cases]] · [[MOC Decisiones ADR]]
