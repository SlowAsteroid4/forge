---
type: roadmap
tags: [roadmap, deuda]
---
# Pendientes y Deuda Técnica

## Bloqueantes / alta prioridad
1. **WP-20 (WIP)**: validar contra Jira que **Alondra = WIP 2 / Review 4** y que el test golden asserte 2/4 (el código ya incluye In Code; la prueba final nunca se hizo) — [[ADR-009 WIP igual In Progress mas In Code]].
2. **WP-18 (login Arena)**: evaluar el Handoff contra el DoD diseñado (arcade AC-9.9, inactivos, localStorage, banner ver-como) — [[ADR-013 Arena sin password]].
3. **Revisar `6a2268a`** ("excepción cierre de primer mes"): ¿tocó el gate ≥4 de [[ADR-011 Umbral 4 ciclos MVP mensual]]?
4. **Versionar specs + Manifiesto en el repo** (`backend/specs/`) — ya causó 2 desviaciones.

## Arena (la mitad faltante)
UC-15 onboarding → UC-10 perfil → UC-11/12 leaderboard+detalle (aplicar `LEADERBOARD_AREAS`, EdP como agregado) → UC-13/14 achievements+tienda. Luego: auth real de Ops (destrabar `admin_id=1`, conectar `require_cost_access()`).

## Deuda menor conocida
- `joined_at` NULL en todos → prorrateo de costos asume meses completos.
- Costos capturados 6/14.
- `block_reason` y `Waiting` sin datos de Jira (huecos del Pulso).
- Detección de "Equipo de Producto" por `display_name` (frágil).
- `best_velocity=42` de un solo ciclo viejo (W13) → optimista inflado hasta tener historia.
- 9 subtasks activas sin assignee (vigilar que la cola no esconda abandono).
- `CLAUDE.md` del repo desactualizado respecto al estado real.
- Branch default = `feat/wp18-arena-login`; consolidar a master/main.
- Radar: vista de estado de [[Terceros - Coordinacion]].

Enlaces: [[Knowledge Gaps]] · [[Historial de Work Packages]]
