---
type: adr
estado: vigente
fecha: 2026-06
tags: [adr, tiempo, lead]
---
# ADR-006 — Lead time desde lt_biz_hours; cycle recalculado canónico

**Contexto.** WP-17b necesitaba cycle/lead por ciclo/mes/histórico. El cruce manual reveló lead_avg=0.0 en periodos viejos — imposible (lead ≥ cycle siempre).
**Problema.** Dos bugs de datos: (1) `subtasks.created_at` es la **fecha de import** (todas 2026-05-21), no la creación en Jira; la creación real **no está en el changelog** (solo histories, no `fields.created`). (2) Las histories no vienen ordenadas: el "primer In Progress" por orden de array era el de re-trabajo (YAP-721: 99.44h en vez de 107.44h).
**Alternativas.** (a) Re-sync trayendo `fields.created` (tocar el ETL en caliente); (b) usar lo que ya capturó WP-07h.
**Decisión.** (b): **lead = `lt_biz_hours`** (única fuente con la creación real); **cycle = recálculo canónico desde el changelog**, con histories **ordenadas por timestamp** y detección del primer In Progress canónico real.
**Consecuencias.** Lead ≥ cycle en todos los periodos; YAP-721 cuadra a mano (107.44 = 107.44, [[Golden Cases]]). El recálculo canónico **no escribe** la columna `ct_biz_hours` (queda el literal de WP-07h).
**Tradeoffs.** Dos cycle times coexisten (literal 99.44 vs canónico 107.44) — el canónico es el que se muestra; documentado para no confundir. Considerar a futuro traer `fields.created` al ETL ([[Knowledge Gaps]]).
