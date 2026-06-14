---
type: knowledge-gap
tags: [gaps]
---
# Knowledge Gaps (información faltante)

| Gap | Impacto | Prioridad | Cómo obtenerla |
|---|---|---|---|
| ¿WP-18 cumple su DoD? (Handoff nunca evaluado) | Arena arranca sobre base sin revisar | Alta | Sesión corta de verificación con el DoD diseñado |
| ¿Alondra = WIP 2/Review 4 en Forge hoy? | El tablero de saturación podría seguir mintiendo | Alta | Ajuste WP-20: query cruda + endpoint + test golden 2/4 |
| ¿`6a2268a` tocó el gate ≥4 del MVP mensual? | Posible regresión de [[ADR-011 Umbral 4 ciclos MVP mensual]] | Alta | `git show 6a2268a` + leer la regla actual |
| Commits de WP-11/12/13/19/20 | Trazabilidad WP→commit rota | Media | `git log --all` / reconstruir del reflog o re-commitear con nombre |
| Detector de debuffs automáticos (D01–D13): ¿qué dispara cada uno? | El PM no puede explicar penalizaciones auto al equipo | Media | FASE B: extraer del código del detector |
| `monthly_hours_cap`: ¿semántica exacta y quién lo define? | Costos de externos dependen de él | Media | Confirmar con el PM + código de [[ADR-015 Forecast on-the-fly]]/costos |
| Fechas de ingreso (`joined_at`) de los 14 players | Prorrateo de costos impreciso | Media | Capturarlas en `/admin/players` |
| ¿Qué es cada tercero (STP, Nubarium, Cierto, MoSi…)? | Contexto de negocio de [[Terceros - Coordinacion]] | Baja | 1 párrafo del PM por tercero |
| KPIs del propio Forge (¿qué mide su éxito?) | La visión queda en [INFERENCIA] | Baja | Definirlos con el PM |
| Multiplicadores de SP por clase/rol de Arena | La fórmula SP los menciona; valores sin documentar aquí | Media | FASE B: extraer de `sp_calculator` |

Enlaces: [[Pendientes y Deuda]] (deuda de *trabajo*; esta nota es deuda de *información*)
