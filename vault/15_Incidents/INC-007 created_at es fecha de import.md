---
type: incident
tags: [incidente, datos]
---
# INC-007 — created_at es la fecha de IMPORT, no de creación

**Síntoma.** Lead time 0.0 en casi todos los periodos viejos — imposible (lead ≥ cycle siempre).
**Causa raíz.** `subtasks.created_at` guarda cuándo Forge importó la fila (todas "2026-05-21"), no cuándo se creó en Jira. Para tarjetas viejas, import > done → horas hábiles = 0. La creación real **no está en el changelog**.
**Fix.** Lead = `lt_biz_hours` (WP-07h sí la capturó del API); cycle recalculado del changelog (WP-17b).
**Lección.** Una métrica **imposible** (lead < cycle) es el mejor detector de datos podridos: programa invariantes así. → [[ADR-006 Lead desde lt_biz_hours]].
