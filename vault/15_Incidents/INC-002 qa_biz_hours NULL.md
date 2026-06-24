---
type: incident
tags: [incidente, qa, tiempo]
---
# INC-002 — qa_biz_hours NULL (185/267)

**Síntoma.** La mayoría de subtasks Done sin tiempo de QA registrado.
**Causa raíz.** **El mismo patrón de INC-001** en otra capa: el bucket de tiempo buscaba estados con nombres equivocados; las transiciones reales no acumulaban.
**Fix.** Buckets redefinidos sobre estados reales + nuevo `ready_for_qa_biz_hours` separado (WP-07h, `80c82da`).
**Lección.** Cuando encuentres un bug de mapeo de estados, **buscalo en todas las demás métricas**: el mismo error se replica en silencio. Ver [[Atribucion de Tiempo WP-07h]].
