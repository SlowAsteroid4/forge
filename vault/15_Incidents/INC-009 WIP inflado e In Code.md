---
type: incident
tags: [incidente, pulso, wip]
---
# INC-009 — Tres generaciones de WIP mintiendo

**Síntoma (3 olas).** (1) Semáforo de área al 666%. (2) Alondra "5 WIP" trabajando 2; Alan Daniel "43 WIP" con 11 en Backlog. (3) Tras el fix: Alondra WIP=1 — `In Code` sin contar.
**Causas raíz.** (1) Contaba unassigned contra límites de área. (2) "WIP" = todo lo no terminal, sin definición de negocio. (3) El código asumió que `In Code` "no existía aún en datos" **sin verificar** — el PASO 0 de auditoría se saltó, y el test golden se escribió validando el número del bug (1/3) en vez del esperado (2/4).
**Fix.** Definición estricta del PM (`_WIP_STATES={In Progress, In Code}`, [[ADR-009 WIP igual In Progress mas In Code]]); semáforo solo sobre WIP. ⚠️ **Validación final Alondra=2 pendiente** ([[Pendientes y Deuda]]).
**Lección.** Doble: la definición de una métrica es **decisión de negocio**, no del código; y un test que asserta el valor del bug es peor que no tener test.
