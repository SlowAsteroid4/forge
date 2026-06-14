---
type: domain
tags: [negocio, ritmo, ciclo]
---
# Ritmo Operativo (reemplazó a Sprint)

El modelo temporal de Yapsi tiene **tres capas** ([[ADR-001 Sprint a Ciclo]]):

| Capa | Qué es | Para qué |
|---|---|---|
| **Pulso** | El AHORA, live, read-only | Operación diaria: WIP, bloqueos, aging. **No compite ni escribe** ([[ADR-014 Pulso read-only]]) |
| **Ciclo** | Semana Lun–Vie, cierre ritual el viernes | La unidad de competencia: MVP semanal (+5 SP, B17), snapshot de leaderboard |
| **Ventana Móvil** | Últimos **4 ciclos cerrados** | Tendencias, velocity, forecast — nunca semanas calendario |

## Reglas del Ciclo
- Solo **1 ciclo activo** a la vez. Estados: active → closed → archived.
- El cierre escribe: MVP semanal (B17 +5 SP), achievement ACH04 si aplica, snapshot de leaderboard. Edición post-cierre: ventana de 24h hábiles.
- **MVP del Mes** (UC-17): +10 SP (B17M), candidatos = solo MVPs semanales del mes (AC-17.4), gate = **≥4 ciclos cerrados con MVP** ([[ADR-011 Umbral 4 ciclos MVP mensual]]), edición 72h hábiles.

## Implicación práctica
Con poca historia, el sistema dice **"preliminar"** (forecast) o **"sin comparativa"** (analítica) en vez de inventar — el costo honesto de la Ventana Móvil. Se cura solo al cerrar ciclos.

Enlaces: [[JPDS - Contrato de Medicion]] · [[Economia CP-SP]]
