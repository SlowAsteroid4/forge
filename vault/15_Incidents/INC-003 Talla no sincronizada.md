---
type: incident
tags: [incidente, etl]
---
# INC-003 — Talla no sincronizada (≈105/210)

**Síntoma.** Mitad de subtasks sin talla → sin CP → velocity/forecast imposibles. El sync "reportaba 150 actualizadas" sin cambiar el conteo.
**Causa raíz.** No era el campo (sospecha inicial): `customfield_10851` era correcto. Eran (1) la **ventana JQL −14d** (lo viejo nunca se re-traía) y (2) **3 issue types excluidos** del sync.
**Fix.** `make sync-full` (backfill) + 7 tipos sincronizados + cp inline (`647e601`).
**Lección.** "El sync corrió bien" ≠ "los datos están bien": validar **conteos antes/después**, no logs. → [[ADR-002 Talla y sync-full]], [[ETL Jira - Conocimiento Critico]].
