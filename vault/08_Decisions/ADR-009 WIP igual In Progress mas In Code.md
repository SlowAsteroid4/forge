---
type: adr
estado: vigente — validacion pendiente
fecha: 2026-06
tags: [adr, wip, pulso]
---
# ADR-009 — WIP = In Progress + In Code; semáforo solo sobre WIP

**Contexto.** Tres iteraciones de WIP fallidas: semáforo de área con unassigned (666% falso), luego "todo lo activo" llamado WIP (Alondra salía con 5 cuando trabaja 2; Alan Daniel con 43 teniendo 11 en Backlog).
**Problema.** "WIP" debe medir **manos en la tarea** para que el semáforo de saturación signifique algo; In Review/QA/colas no son trabajo activo del dev.
**Alternativas.** (a) WIP = solo In Progress canónico; (b) In Progress + In Code; (c) todo lo no-terminal.
**Decisión.** (b), del PM: `_WIP_STATES = {In Progress, In Code}` — In Code es el "activo" propio de DB. El desglose por dev muestra columnas separadas (In Progress, In Review, QA, Waiting, Ready) pero **solo el WIP dispara el semáforo** (límites BE=3/FE=3/DESIGN=4/DB=5; verde<límite, amarillo=, rojo>). Un dev con 6 In Review y 1 In Progress es **verde**.
**Consecuencias.** Caso golden: Alondra = WIP 2 / Review 4 ([[Golden Cases]]). Constante separada del mapeo canónico a propósito (es operación del Pulso, no agrupación de métricas).
**Tradeoffs / Estado.** ⚠️ El Handoff de WP-20 reportó 1/3 (no contaba In Code) y el ajuste se pospuso; el código actual ya incluye In Code pero **la validación contra Jira y el test golden 2/4 siguen pendientes** ([[Pendientes y Deuda]]).
