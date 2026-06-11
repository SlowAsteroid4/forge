---
type: domain
tags: [jpds, negocio, contrato]
---
# JPDS — Contrato de Medición

El **Manifiesto JPDS** es el contrato semántico de cómo se mide el trabajo en Yapsi. ⚠️ Vive en `/mnt/project/Manifiesto_JPDS.md` del chat maestro, **no versionado en el repo** ([[Knowledge Gaps]]).

## Principios que Forge implementa
1. **"Los estados canónicos definen cómo el sistema mide. Los especializados definen cómo el equipo trabaja. Nunca se mezclan."** → [[Estados Crudos vs Canonicos]] y [[ADR-005 Canonicos para agrupar]].
2. **Niveles de trabajo**: Nivel 1 = gobierno (PO/PM, no compite en delivery); Nivel 2 = contenedores (épicas, coordinación); Nivel 3 = subtasks (donde se mide CP/SP/tiempo). El PO se excluye de métricas de flujo y leaderboard (`LEADERBOARD_AREAS`).
3. **Tiempo en horas hábiles** (America/Mexico_City, `core/time_utils`) — nunca calendario.
4. **Inmutabilidad**: CP aprobado no se toca ([[Economia CP-SP]]); SP solo se ajusta append-only.
5. **Cycle time** = In Progress → Done; **Lead time** = creación → Done ([[ADR-006 Lead desde lt_biz_hours]]).

## Dónde se desvió Forge (con razón, documentado)
- `Ready For QA` → canónico `Ready` según el manifiesto, pero el **tiempo** se atribuye al dev ([[Atribucion de Tiempo WP-07h]]): categoría ≠ atribución, decisión explícita del PM.
- `Testing` → canónico `In Review` para mostrar, pero el tiempo es de Edgar (QA).

Enlaces: [[Ritmo Operativo]] · [[Reglas Bloqueantes]] · [[Glosario]]
