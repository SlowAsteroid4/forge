---
type: adr
estado: vigente
fecha: 2026-06
tags: [adr, mvp, negocio]
---
# ADR-011 — Gate estricto de ≥4 ciclos para MVP del Mes

**Contexto.** UC-17 exige ≥4 ciclos cerrados con MVP para cerrar el mes. Durante el demo de WP-10 el umbral se relajó a 1 para poder demostrar el flujo, y mayo quedó cerrado con datos de demo.
**Problema.** Un MVP del Mes otorgado con 1 ciclo de evidencia devalúa el reconocimiento y deja SP/achievements basados en demo en producción.
**Alternativas.** (a) Dejar el demo (mayo "cerrado"); (b) revertir y restaurar el gate.
**Decisión.** (b): `_MIN_CLOSED_CYCLES_FOR_CLOSE=4` restaurado; el cierre de mayo se revirtió **append-only** (reversal de −10 SP, `mvp_monthly=0`) — el ACH04 de Juan se conservó porque lo ganó legítimamente por W22, no por el demo.
**Consecuencias.** La regla AC-17.4 quedó intacta (candidatos = solo MVPs semanales, validado con SQL). El primer MVP del Mes real llegará cuando exista historia suficiente — el sistema prefiere esperar a fingir.
**Tradeoffs.** Mes sin cierre hasta acumular 4 ciclos; coherente con [[Ritmo Operativo]] y el principio "preliminar antes que inventado". Nota: existe un fix posterior no revisado ("excepción de cierre de primer mes", `6a2268a`) que **podría haber tocado esta regla** — verificar ([[Pendientes y Deuda]]).
