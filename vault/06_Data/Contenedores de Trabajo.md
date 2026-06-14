---
type: domain
tags: [datos, epicas, contenedores]
---
# Contenedores de Trabajo (`epic_kind`)

Tres tipos de contenedor, distinguidos por `epics.epic_kind` (WP-19; el sync **no lo pisa** — `epic_data` nunca incluye el campo):

| Kind | Qué es | Forecast | Flujo/tiempo |
|---|---|---|---|
| `normal` (46) | Épica con objetivo que cierra | ✅ proyecta fecha | ✅ |
| `version_container` (2) | Cajón de tareas sin épica: **YAP-66 [2.1]** y **YAP-130 [3.0]** | ❌ excluida (38→36) | ✅ cuenta |
| `coordination` (0 épicas) | Reservado — los terceros reales NO son épicas (ver abajo) | ❌ | ✅ |

## El hallazgo importante (corrigió mi propio modelo)
"Coordinación" en el dominio del PM = los **terceros** (integraciones vivas que nunca cierran). Pero en Jira **no son épicas**: son **8 subtasks `Coordination` flotantes sin padre** ([[Terceros - Coordinacion]]). Por eso nunca contaminaron el forecast. Los 5 prefijos de apartado ([PLD], [CAY], [YAPI], [YPNX], [YPAPP]) son **todos producto propio** (normal) — confirmado prefijo por prefijo por el PM.

Mecanismo de clasificación: `seed/epic_kinds.yaml` + `make seed-epic-kinds` (idempotente, auditado con `epic_kind_set`).

Enlaces: [[ADR-010 epic_kind y contenedores]] · [[Apartados de Proyecto]]
