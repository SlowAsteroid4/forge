---
type: incident
tags: [incidente, tiempo]
---
# INC-005 — Los devs cargaban el tiempo de Edgar

**Síntoma.** Tiempos de responsabilidad del dev inflados (Juan: 475h).
**Causa raíz.** `dev_resp` incluía los estados de QA: las horas de revisión de Edgar se le cargaban al autor de la tarjeta.
**Fix.** Separación RfQA (cola del dev) vs In QA/Testing (Edgar) — `dev_resp` excluye In QA (WP-07h). Juan: 475→**343h**. Golden: YAP-721, dev_resp 79.74 = 99.44 − 19.70.
**Lección.** Antes de comparar personas, pregunta **de quién es cada hora**. → [[ADR-004 RfQA dev In QA Edgar]].
