---
type: adr
estado: vigente — LINEA ROJA
fecha: 2026-05
tags: [adr, tiempo, qa]
---
# ADR-004 — Ready for QA = dev · In QA/Testing = Edgar

**Contexto.** El tiempo "de QA" mezclaba dos cosas distintas: la cola esperando a QA y la revisión activa de Edgar.
**Problema.** Cargar todo al dev inflaba su tiempo (Juan: 475h); cargar todo a Edgar escondía el cuello real (la cola Ready for QA llegó a 460h en BE).
**Alternativas.** (a) Todo el tramo a QA; (b) todo al dev; (c) separar: cola ≠ revisión.
**Decisión.** (c): `Ready for QA` = responsabilidad del **dev** (su entrega sigue siendo suya hasta que QA la toma — y mide el cuello de QA como cola); `In QA`/`Testing` = tiempo de **Edgar**. `dev_resp` excluye In QA (WP-07h, `80c82da`).
**Consecuencias.** Juan 475→343h (real); el hero del bottleneck cambió de artefacto a señal ([[INC-004 Hero PO-Testing artefacto]]). Validado con YAP-721 ([[Golden Cases]]) y declarado **intocable**: todo WP posterior debe demostrar estos buckets byte-idénticos.
**Tradeoffs.** Diverge del mapeo canónico del Manifiesto (RfQA→Ready, Testing→In Review) — resuelto en [[ADR-005 Canonicos para agrupar]].
