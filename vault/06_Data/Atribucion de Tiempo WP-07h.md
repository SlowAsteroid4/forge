---
type: domain
tags: [datos, tiempo, qa]
---
# Atribución de Tiempo (WP-07h) — INTOCABLE

Define **a quién se le carga el tiempo** de cada estado. Validada con cruce manual ([[Golden Cases]], YAP-721) y declarada línea roja: ningún WP posterior puede moverla sin revalidar todo.

## Los buckets (`etl/time_metrics.py`)
| Bucket | Estados | Significado |
|---|---|---|
| `dev_resp_biz_hours` | activos del dev **+ `Ready for QA`** | Responsabilidad del dev. RfQA es SU cola/cuello (terminó pero el paquete es suyo hasta que QA lo toma) |
| `qa_biz_hours` | `In QA`, `Testing` | Tiempo de **Edgar** (QA revisando) |
| `review_biz_hours` | `In Review` | Revisión de código |
| `blocked` / `waiting` | `Blocked` / `Waiting` | — |

`dev_resp` **excluye** In QA: el dev no carga el tiempo de Edgar (antes Juan cargaba 475h; real: 343h — [[INC-005 Tiempo de Edgar al dev]]).

## La separación clave ([[ADR-005 Canonicos para agrupar]])
- **Categoría canónica** = cómo se agrupa/muestra (manda el Manifiesto: Testing→In Review).
- **Atribución** = a quién se carga (manda WP-07h: Testing→Edgar).
Son capas distintas a propósito; unificarlas habría reabierto números ya validados.

## Cycle / Lead
- **Cycle** = primer `In Progress` canónico real → Done, con histories **ordenadas por timestamp** (YAP-721: 107.44h, no 99.44 del re-trabajo).
- **Lead** = `lt_biz_hours` de WP-07h (la única fuente con la creación real de Jira; `created_at` es fecha de import — [[INC-007 created_at es fecha de import]]).
- Todo en horas hábiles MX.

Enlaces: [[ADR-004 RfQA dev In QA Edgar]] · [[ADR-006 Lead desde lt_biz_hours]]
