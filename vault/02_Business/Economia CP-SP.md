---
type: domain
tags: [negocio, cp, sp, economia]
---
# Economía CP / SP

## CP — Complexity Points (la medida de complejidad)
- Derivados de la **talla** (Jira `customfield_10851`): XS=1, S=2, M=3, L=5, XL=8.
- El PM los **aprueba** por subtask (UC-04). Una vez aprobado, **el CP es inmutable**: `CPImmutableError` si algo intenta tocarlo. Toda validación de WPs incluye el conteo de `cp_approved_at` antes/después (invariante: igual).
- Son la base de **velocity** y **forecast** ([[ADR-015 Forecast on-the-fly]]) y el denominador de costos ($/CP).

## SP — Score Points (la moneda de Arena)
**SP = CP × multiplicadores + bonos − penalizaciones.**
- Bonos: B17 (+5 MVP semanal), B17M (+10 MVP del Mes). Penalizaciones: catálogo D01–D16 (manuales del PM o automáticas del detector).
- `sp_final` materializado por subtask; recálculo con el motor (`recalculate_subtask`, `make recalc --all-cycles`).

## La regla de oro: append-only
`sp_adjustments` **nunca se UPDATEa para cambiar SP**. Revertir = **INSERT de signo opuesto**; reducción parcial = INSERT por la diferencia (original −2.0, reducir a −0.5 → reversal +1.5). La **metadata de apelación** (`is_appealed`, `appeal_resolution`...) **sí** se actualiza en la fila original — es estado, no valor. Validación de límite: nunca dejar `sp_final` negativo (piso 0; debuffs −100% llevan exactamente a 0).

Demo canónico en [[Golden Cases]]. Por qué importa: la moneda de Arena debe ser auditable transacción por transacción — un UPDATE silencioso destruiría la confianza del equipo en el juego.

Enlaces: [[Reglas Bloqueantes]] · [[ADR-011 Umbral 4 ciclos MVP mensual]]
