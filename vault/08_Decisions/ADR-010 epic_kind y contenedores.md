---
type: adr
estado: vigente
fecha: 2026-06
tags: [adr, forecast, epicas]
---
# ADR-010 — epic_kind: los Version Containers salen del forecast

**Contexto.** El PM aclaró el dominio: hay "tareas de coordinación" (terceros vivos que nunca cierran) y 2 "Version Containers" (cajones de tareas sin épica). El forecast proyectaba fecha de cierre de todo.
**Problema.** Proyectar la fecha de cierre de algo que por diseño no cierra produce fechas sin sentido y ensucia el forecast ejecutivo.
**Alternativas.** (a) Excluir por nombre/heurística; (b) campo de clasificación explícito y durable.
**Decisión.** (b): `epics.epic_kind ∈ {normal, coordination, version_container}` (WP-19), poblado con evidencia: YAP-66 y YAP-130 = version_container; **cero épicas coordination** — la auditoría probó que los terceros reales son 8 subtasks flotantes sin padre ([[Terceros - Coordinacion]]), y el PM confirmó prefijo por prefijo que [PLD]/[CAY]/[YAPI]/[YPNX] son producto propio (normal). Forecast: 38→36 épicas. El flujo/throughput **sí** sigue contando ese trabajo.
**Consecuencias.** Forecast limpio; mecanismo `seed/epic_kinds.yaml` + `make seed-epic-kinds` para clasificar a futuro; el sync no pisa el campo ([[ADR-008 Clasificaciones durables]]).
**Tradeoffs.** El valor `coordination` queda reservado sin uso a nivel épica — correcto, no un hueco.
