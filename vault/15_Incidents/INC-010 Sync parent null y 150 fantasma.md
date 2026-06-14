---
type: incident
tags: [incidente, etl]
---
# INC-010 — Sync: crash por parent=null y "150 actualizadas" fantasma

**Síntoma.** (a) El sync crasheaba con subtasks sin padre. (b) Reportaba "150 issues actualizadas" sin que ningún conteo cambiara en BD.
**Causa raíz.** (a) Asumía jerarquía completa — pero los 8 terceros ([[Terceros - Coordinacion]]) son **legítimamente** subtasks sin padre. (b) "Actualizada" = tocada por el API, no = cambió algo; reporting optimista.
**Fix.** parent nullable manejado; validación por conteos antes/después en vez de creerle al log.
**Lección.** Los datos "malformados" a veces son el dominio diciéndote algo (los flotantes eran un concepto real, no basura). Y al log del sync no se le cree: se cuenta. → [[Patrones que Funcionan]].
