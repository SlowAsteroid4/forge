---
type: domain
tags: [datos, apartados, filtros]
---
# Apartados de Proyecto

Sub-divisiones **dentro** del único proyecto Jira (YAP), codificadas como prefijo `[XXX]` en el summary de la **épica** (la fuente confiable; stories/subtasks no traen prefijo propio). Derivación: subtask → story (`parent_story_key`) → epic (`parent_epic_key`) → prefijo.

## Los 5 oficiales + 1
`[YAPI]` · `[YPAPP]` · `[YPNX]` · `[CAY]` · `[PLD]` + **"Sin apartado"** (primera clase, no escondido — es el trabajo bajo los 2 Version Containers, [[Contenedores de Trabajo]]).

Conteos al medirlo (WP-17b, 428 subtasks): YPAPP 190 · PLD 75 · YPNX 7 · Sin apartado 156 (36.4%). YAPI/CAY existían como épica sin subtasks aún.

## Diseño del filtro (WP-21, `e5e5d47`)
**Derivado dinámicamente de los datos** (un prefijo nuevo aparece solo) con red de seguridad `KNOWN_APARTADOS` para ordenar conocidos primero y detectar typos (un `[YPAP]` mal escrito no debe crear un apartado fantasma silencioso). El filtro es **global**: aplica a todas las secciones de Analítica (quality, barras canónicas, cycle/lead, métricas por dev, throughput...).

Enlaces: [[ADR-012 Apartados dinamicos]] · [[Jira - Mapa de Integracion]]
