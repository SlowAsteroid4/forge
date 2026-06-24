---
type: reference
tags: [referencias, fuentes]
---
# Fuentes y Trazabilidad

## Las tres fuentes de verdad (y su estado)
1. **Repo** — `github.com/SlowAsteroid4/forge` (37 commits; branch default `feat/wp18-arena-login`). El *qué* y el *cómo*. 101 archivos Python, 104 TS/TSX.
2. **Specs** — `/mnt/project/` del chat maestro: 17 UCs + `Manifiesto_JPDS.md` + `forge_entidades_v1.md` + catálogos. El *contrato*. ⚠️ **No versionados en el repo** — meterlos a `backend/specs/` es pendiente prioritario.
3. **El chat maestro** — el *por qué*: prompts de WP, Handoff Reports con salidas reales, decisiones y golden cases. Este vault (FASE A) rescata su contenido; la conversación original sigue siendo la fuente primaria si algo aquí parece incompleto.

## Cadena de trazabilidad
Problema → UC (spec) → WP (prompt del chat maestro) → commit(s) → Handoff Report (validación con datos reales) → ADR/INC en este vault. Mapa completo: [[MOC Casos de Uso]] y [[Historial de Work Packages]].

## Para FASE B (extracción del código)
Los 13 servicios + engine + ETL merecen System/Service notes (inputs/outputs/contratos) extraídas del código real por Claude Code, enlazadas a estos ADRs. Este vault define la estructura destino.
