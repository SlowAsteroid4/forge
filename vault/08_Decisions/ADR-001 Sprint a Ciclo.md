---
type: adr
estado: vigente
fecha: 2026-05
tags: [adr, ciclo]
---
# ADR-001 — Sprint → Ciclo (Ritmo Operativo)

**Contexto.** Forge v0.1 nació con un modelo `sprints` genérico. El JPDS define otra cosa: [[Ritmo Operativo]] (Pulso / Ciclo Lun–Vie / Ventana Móvil de 4 ciclos cerrados).
**Problema.** El modelo Sprint no soporta cierre ritual semanal, MVP por ciclo ni la ventana móvil; construir encima habría calcificado el modelo equivocado.
**Alternativas.** (a) Renombrar sprints; (b) tabla `cycles` nueva y migrar el negocio; (c) mantener ambos.
**Decisión.** (b): tabla `cycles` aditiva (WP-01a, `10a9861`), luego switch de todo el código de negocio (WP-01b, `f643f72`), FKs `cycle_id`, un solo ciclo activo.
**Consecuencias.** Todos los specs UC escritos "pre-migración" requieren **traducción** (donde dicen sprint/semana → ciclo) — regla permanente en los prompts de WP. La tabla `sprints` quedó legacy.
**Tradeoffs.** Migración temprana costosa, pero evitó re-trabajo en 15+ WPs posteriores.
