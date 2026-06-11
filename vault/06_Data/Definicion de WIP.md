---
type: domain
tags: [datos, wip, pulso]
---
# Definición de WIP

**WIP = subtasks en `In Progress` + `In Code`** — manos en la tarea, nada más. (`_WIP_STATES`, `pulse_service.py:111`.)

- `In Code` = el "trabajo activo" propio de **Database** (DB nombra distinto su In Progress).
- **NO son WIP**: In Review, Ready for QA, In QA, Waiting, Ready, Backlog, Blocked, Done. Se muestran como columnas separadas en el desglose por dev, **sin color**.
- **Semáforo** solo sobre WIP, contra el límite del área del dev: BE=3, FE=3, DESIGN=4, DB=5. Verde < límite, amarillo = límite, rojo > límite. Un dev con 6 In Review y 1 In Progress es **verde**.

## Caso golden (criterio de aceptación del PM)
**Alondra (DB)**: 1 In Progress + 1 In Code + 4 In Review → **WIP = 2, Review = 4** (verde: 2 < 5).
**Alan Daniel Ríos**: 11 en Backlog → Backlog jamás cuenta (el bug histórico le daba 43).

## Estado: ⚠️ validación pendiente
WP-20 quedó PARTIAL: su Handoff reportó Alondra WIP=1/Review=3 (no contaba In Code) y el PM pospuso el ajuste. El código actual **ya incluye In Code** en `_WIP_STATES`, pero **falta validar contra Jira que Alondra=2** y revisar que el test golden asserte 2/4 (un test que valida el número equivocado es peor que no tener test). Ver [[Pendientes y Deuda]] e [[INC-009 WIP inflado e In Code]].

## Historia del concepto (3 iteraciones)
1. WP-08: semáforo por área contando unassigned → 666% falso. 2. WP-16: se quitó el semáforo, "tareas por estado" — pero todo lo activo se seguía llamando WIP. 3. WP-20: definición estricta del PM (la actual).

Enlaces: [[ADR-009 WIP igual In Progress mas In Code]] · [[Golden Cases]]
