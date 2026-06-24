---
type: incident
tags: [incidente, tiempo, etl]
---
# INC-006 — Las histories de Jira no vienen ordenadas

**Síntoma.** Cycle time de YAP-721 = 99.44h cuando el cálculo manual daba 107.44h.
**Causa raíz.** El changelog de Jira entrega `histories` **sin orden cronológico garantizado**; "el primer In Progress" por orden de array era el de un re-trabajo posterior, no el inicio real.
**Fix.** Ordenar por timestamp antes de detectar transiciones (WP-17b). 107.44 = 107.44 ✓.
**Lección.** El **cruce manual** caza lo que ningún test sintético ve: este bug habría shippeado un cycle time sutilmente bajo para siempre. → [[Golden Cases]], [[Patrones que Funcionan]].
