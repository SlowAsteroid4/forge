---
type: adr
estado: vigente
fecha: 2026-05
tags: [adr, pulso]
---
# ADR-014 — El Pulso es read-only (no compite, no escribe)

**Contexto.** El Pulso es la vista live del AHORA ([[Ritmo Operativo]]). La tentación natural: que también otorgue, marque o ajuste.
**Problema.** Si la vista operativa diaria escribiera gamificación, cada refresh sería un riesgo para la moneda de Arena y el ritmo perdería su frontera (lo live no compite; se compite al cierre del Ciclo).
**Alternativas.** (a) Pulso con acciones de gamificación; (b) Pulso estrictamente lector con una única acción administrativa.
**Decisión.** (b): el Pulso no escribe `sp_adjustments` ni leaderboard jamás. Única escritura permitida: **"marcar para revisión"** (`flagged_for_review` → audit_log), trazabilidad pura. Cada WP del Pulso incluye demo de no-escritura (conteos idénticos antes/después).
**Consecuencias.** Refrescar/consultar el Pulso es siempre seguro; la separación live vs cierre se mantiene nítida.
**Tradeoffs.** Acciones rápidas (p. ej. penalizar desde el Pulso) requieren ir a su vista propia — fricción intencional.
