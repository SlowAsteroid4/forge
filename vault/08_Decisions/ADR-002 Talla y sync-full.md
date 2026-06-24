---
type: adr
estado: vigente
fecha: 2026-05
tags: [adr, etl, talla]
---
# ADR-002 — La talla era correcta; el bug era la ventana

**Contexto.** Solo ~la mitad de las subtasks tenía talla en BD; sin talla no hay CP ni velocity ([[Economia CP-SP]]).
**Problema.** Sospecha inicial: campo de Jira equivocado. La auditoría probó que `customfield_10851` **era el correcto**; las causas reales eran (1) la ventana JQL de −14 días del sync diario (cambios viejos jamás se re-traían) y (2) 3 issue types excluidos del sync.
**Alternativas.** (a) Cambiar de campo (incorrecto); (b) ampliar la ventana permanente (lento); (c) backfill bajo demanda + tipos ampliados.
**Decisión.** (c): `make sync-full` para backfill completo + 7 tipos sincronizados (incl. Test Sub-Task); cp calculado inline en el sync (WP-07f/j, `647e601`).
**Consecuencias.** Cadena talla→cp→velocity cerrada; el forecast se volvió posible. Regla operativa: tras cambios masivos en Jira, correr sync-full.
**Tradeoffs.** El sync diario sigue con ventana −14d (rápido); el costo es recordar el backfill. Ver [[INC-003 Talla no sincronizada]].
