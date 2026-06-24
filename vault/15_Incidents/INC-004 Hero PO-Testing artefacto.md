---
type: incident
tags: [incidente, analitica]
---
# INC-004 — El bottleneck hero señalaba un fantasma

**Síntoma.** El "cuello de botella" principal de Analítica: PO/Testing — un área de gobierno que no entrega.
**Causa raíz.** Las métricas de flujo mezclaban **Nivel 1 (gobierno)** con delivery; el PO aparecía como área productiva y distorsionaba el ranking.
**Fix.** `DELIVERY_AREAS` excluye PO del flujo (`771d859`); el hero real emergió: **BE / Ready for QA con 460h de cola** — accionable de verdad.
**Lección.** Un dashboard que señala algo que no puedes accionar está midiendo mal el modelo, no el trabajo. → [[JPDS - Contrato de Medicion]] (niveles).
