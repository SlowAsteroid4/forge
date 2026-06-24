---
type: domain
tags: [datos, estados, canonico]
---
# Estados Crudos vs Canónicos

**Crudos** = los strings reales de Jira ("cómo el equipo trabaja"). **Canónicos** = las 9 categorías del Manifiesto ("cómo el sistema mide"). Todo crudo mapea a uno y solo un canónico, en `CANONICAL_STATUS_MAP` (`services/canonical_status.py`) — **módulo único, prohibido duplicar**.

## Los números reales
- **37 estados crudos** en `raw_changelog` (histórico), incluyendo **variantes en español** (`En progreso`, `Cerrado`, `Bloqueado`, `En revisión`...) de cuando el equipo cambió el idioma del workflow.
- **12 estados activos** en `subtasks.status` hoy.
- **9 canónicos**: Backlog, Ready, In Progress, In Review, In QA, Waiting, Blocked, Done, Cancelled.

## Mapeos que confunden (memorizar)
| Crudo | Canónico | Nota |
|---|---|---|
| `In Code` | In Progress* | Trabajo activo **solo de DB**; cuenta como WIP ([[Definicion de WIP]]) |
| "Code Review" | — | **No existe**; lo que existe es `In Review` |
| `Ready For QA` | Ready (manifiesto) | Pero el **tiempo** es del dev ([[Atribucion de Tiempo WP-07h]]) |
| `Testing` | In Review (manifiesto) | Pero el **tiempo** es de Edgar/QA |
| `Active`, `Implementation`, `In Design`, `UI Implementation` | In Progress | Sub-etapas activas plegadas (auditable vía `raw_statuses`) |

\*Para display el plegado canónico va a In Progress; el test `test_canonical_status.py` garantiza que los 37 crudos caen en un canónico válido sin fallback silencioso.

**Lección estructural**: tres bugs nacieron de asumir nombres de estados ([[INC-001 QA first-pass falso]], [[INC-002 qa_biz_hours NULL]]). Regla: los nombres de estados **se verifican con `SELECT DISTINCT`, nunca se asumen**.

Enlaces: [[ADR-005 Canonicos para agrupar]] · [[JPDS - Contrato de Medicion]]
