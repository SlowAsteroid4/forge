---
type: adr
estado: vigente
fecha: 2026-06
tags: [adr, canonico, tiempo]
---
# ADR-005 — Canónicos para agrupar/mostrar; WP-07h para atribuir

**Contexto.** Al adoptar los 9 canónicos del Manifiesto (WP-17a), su mapeo literal (`Testing→In Review`, `Ready For QA→Ready`) chocaba con la atribución de tiempo ya validada ([[ADR-004 RfQA dev In QA Edgar]]).
**Problema.** Aplicar el mapeo canónico a la atribución habría movido `dev_resp`/`qa_biz_hours` ya validados con datos reales — reabrir trabajo bueno.
**Alternativas.** (a) Canónicos en todo (reabrir WP-07h); (b) ignorar canónicos (violar el Manifiesto); (c) **separar capas**.
**Decisión.** (c), confirmada por el PM: **categoría canónica** = cómo se agrupa y muestra el flujo (manda el Manifiesto); **atribución** = a quién se carga el tiempo (manda WP-07h). Las barras canónicas re-etiquetan los buckets de WP-07h sin reparsearlos — por eso la suma cuadra garantizada.
**Consecuencias.** `CANONICAL_STATUS_MAP` (37 crudos, módulo único con test anti-fallback) convive con los buckets intactos; YAP-721 byte-idéntico tras WP-17a/b.
**Tradeoffs.** Dos vocabularios coexisten; el costo es documentarlo (esta nota). El beneficio: cero re-validación.
