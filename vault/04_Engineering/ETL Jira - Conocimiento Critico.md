---
type: service
tags: [etl, jira, sync]
---
# ETL Jira — Conocimiento Crítico

El sync (`etl/sync_orchestrator.py`) trae épicas → stories → subtasks + changelog desde Jira (`beyapsi-org.atlassian.net`, proyecto YAP). Lo que hay que saber para no romperlo:

## Trampas conocidas (todas mordieron)
1. **Ventana JQL −14d**: el sync diario solo mira lo actualizado en 14 días. Cambios viejos requieren `make sync-full` (backfill). Causa raíz de la talla desincronizada ([[INC-003 Talla no sincronizada]]).
2. **Tipos sincronizados**: 7 issue types (incl. `Test Sub-Task`, `Design Sub-task`, `Coordination`). Excluir tipos = subtasks invisibles.
3. **`subtasks.created_at` = fecha de IMPORT, no de creación en Jira** → inútil para lead time; la creación real solo sobrevive en `lt_biz_hours` ([[INC-007 created_at es fecha de import]]).
4. **Las `histories` del changelog NO vienen ordenadas** — ordenar por timestamp antes de detectar transiciones ([[INC-006 Histories desordenadas]]).
5. **El sync reescribe `assignee_player_id` en cada corrida** (sync_orchestrator ~:224) — atribución por assignee es efímera. **Nunca escribe** `players.*`, `epic_kind`, ni costos → ahí viven las clasificaciones durables ([[ADR-008 Clasificaciones durables]]).
6. **`subtask.area` se infiere de `player.area`** (`_infer_area`, ~:193) — corregir el área de un player corrige sus subtasks al siguiente sync.
7. **Talla = `customfield_10851`** (el campo siempre fue el correcto; el bug era la ventana).
8. **Bug histórico parent=null** en el sync: subtasks sin padre crasheaban — corregido (los 8 terceros flotantes son legítimamente sin padre, [[Terceros - Coordinacion]]).

## Cadena de datos
talla → cp → (aprobación) → velocity/forecast → sp_final → leaderboard. Romper el eslabón 1 pudre todo: por eso el pozo de datos (WP-07a–j) se cerró antes de construir Ops.

Enlaces: [[Jira - Mapa de Integracion]] · [[Estados Crudos vs Canonicos]]
