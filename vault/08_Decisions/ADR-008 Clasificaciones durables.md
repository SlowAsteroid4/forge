---
type: adr
estado: vigente
fecha: 2026-06
tags: [adr, etl, datos]
---
# ADR-008 — Las clasificaciones de Forge viven donde el sync no pisa

**Contexto.** Forge añade conocimiento que Jira no tiene: área real del player, tipo de contenedor, rol PO, costos. ¿Dónde guardarlo sin que el próximo sync lo borre?
**Problema.** El sync **reescribe** `subtasks.assignee_player_id` en cada corrida y re-infiere `subtask.area`; cualquier corrección hecha en esos campos es efímera.
**Alternativas.** (a) Corregir en los campos sincronizados y re-corregir tras cada sync; (b) modificar el sync para preservar excepciones (complejidad); (c) **capa durable propia**.
**Decisión.** (c): las clasificaciones de Forge viven en campos que el sync **jamás escribe** — `players.area/role/costos` (el sync nunca toca la tabla players), `epics.epic_kind` (`epic_data` no incluye el campo). El sync re-deriva lo demás desde ahí (`_infer_area` lee `player.area`).
**Consecuencias.** Corregir el área de un player corrige sus subtasks al siguiente sync, de forma estable. Patrón aplicado en WP-13, WP-15 y WP-19.
**Tradeoffs.** Ninguno relevante; es la separación correcta Jira-como-fuente / Forge-como-clasificador.
