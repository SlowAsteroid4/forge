---
type: product
tags: [producto, vision]
---
# Forge — Visión del Producto

## Problema
El PM de Yapsi no confiaba en las métricas del equipo: Jira dice *qué* pasa, pero los números derivados (WIP, QA first-pass, tiempos, velocity) **mentían** por errores de mapeo de estados, datos no sincronizados y conceptos mal modelados. Sin números confiables, no hay forecast creíble ni gestión justa del desempeño. Ver [[MOC Incidentes]]: 8+ mentiras de datos cerradas antes de construir encima.

## Usuarios
- **PM (único admin)** → Forge Ops: consola operativa y ejecutiva.
- **Devs del equipo** → Forge Arena: identidad RPG, SP, leaderboard, logros, tienda.
- **Dirección** (indirecto) → forecast y costos por área que el PM presenta.

## Las dos mitades
| | Forge Ops | Forge Arena |
|---|---|---|
| Estado | ✅ Completa | 🟡 Solo login (WP-18, sin revisar) |
| Vistas | Dashboard, Aprobación CP, Cierre de ciclo, MVP del Mes, Penalizaciones/Apelaciones, Forecast, Pulso, Analítica, Players, Costos | Login → onboarding → perfil → leaderboard → achievements → tienda (pendientes) |
| Escritura | Sí (aprobaciones, cierres, ajustes — auditados) | Solo lectura de SP + audit de sesión |

## Principio rector
**El dato primero.** Cada métrica se validó con cruce manual contra Jira/BD antes de construir UI encima ([[Patrones que Funcionan]]). El sistema admite incertidumbre ("preliminar", "sin comparativa", "—") antes que inventar un número.

## Métricas de éxito
[INFERENCIA — nunca se formalizaron KPIs del propio Forge]: confianza del PM en los números (cruces manuales que cuadran), adopción de la weekly con Arena proyectada, forecast usado con dirección.

Enlaces: [[MOC Casos de Uso]] · [[JPDS - Contrato de Medicion]] · [[Arquitectura del Sistema]]
