---
type: adr
estado: vigente
fecha: 2026-06
tags: [adr, forecast]
---
# ADR-015 — Forecast on-the-fly, ventana de 4 ciclos, 3 fórmulas

**Contexto.** UC-07 pide 3 escenarios de fecha de cierre por épica. El spec hablaba de "4 semanas calendario" (pre-migración) y existía una tabla `forecast_snapshots` vacía.
**Problema.** ¿Ventana calendario o de ciclos? ¿Calcular al vuelo o snapshotear?
**Alternativas.** Ventana: calendario vs **4 ciclos cerrados** (JPDS post-migración). Cálculo: snapshots vs on-the-fly.
**Decisión.** Ventana = **4 ciclos cerrados**. Cálculo **on-the-fly** (siempre fresco; `forecast_snapshots` se difiere para histórico futuro). Fórmulas: optimista = cp_pend / mejor ciclo del trimestre × 1.00; realista = cp_pend / promedio 4 ciclos × 1.20; conservador = cp_pend / max(avg−σ, 1.0) × 1.30 (piso anti-÷0). Fecha de la épica = **max** de sus áreas (termina con la más lenta); área con cp_pend=0 se ignora; <4 ciclos con datos → **"preliminar"** explícito; velocity sobre **CP** (no SP). Excluye version_containers ([[ADR-010 epic_kind y contenedores]]).
**Consecuencias.** Cruce manual de velocity BE = 12.25 exacto ([[Golden Cases]]). `epics.cp_total` estaba en 0 → se deriva del rollup de subtasks: solo las épicas con desglose proyectan (honesto: "proyectamos lo planeado").
**Tradeoffs.** Sin histórico de proyecciones (hasta activar snapshots). El optimista descansa en un solo ciclo viejo (best=42 de W13) — puede salir demasiado optimista hasta acumular historia ([[Knowledge Gaps]]).
