---
type: testing
tags: [testing, golden]
---
# Golden Cases — los casos del PM como criterio de aceptación

Casos reales, verificados a mano contra Jira/BD, que funcionan como **pruebas de aceptación vivas**. Si un cambio los rompe, el cambio está mal.

## YAP-721 — atribución de tiempo y cycle/lead (la subtask de referencia)
- `ready_for_qa_biz_hours` = **47.74h** (cuello del dev) · `qa_biz_hours` = **19.70h** (Edgar) · `dev_resp` = **79.74h** = 99.44 − 19.70.
- **Cycle canónico = 107.44h** (primer In Progress real 2026-04-24, histories ordenadas por timestamp; el literal 99.44 arrancaba en el In Progress de re-trabajo). **Lead = 120.15h ≥ cycle** (de `lt_biz_hours`).
- Invariante: cualquier WP que toque tiempo debe demostrar estos valores **byte-idénticos** (salvo decisión explícita).

## Alondra (DB, player 13) — definición de WIP
1 In Progress + 1 In Code + 4 In Review → **WIP=2, Review=4**, semáforo verde (2<5). ⚠️ **Validación final pendiente** ([[Definicion de WIP]]).

## Alan Daniel Ríos (BE) — Backlog jamás es WIP
11 en Backlog → WIP no puede ser 43 (el bug histórico); su WIP = solo In Progress+In Code.

## Velocity BE — cruce manual del forecast
W19–W22: 6+13+18+12 = 49 CP / 4 ciclos = **12.25** exacto contra el servicio.

## Dev metrics — el canónico agrega los crudos
Juan Castillo (id 7): Ready canónico 1900.78 = Ready 1279.64 + Ready for QA 621.14; sum(crudo)=sum(canónico)=**3318.69**.

## SP append-only — demo limpio (WP-11)
Reversión total restaura exacto; reducción parcial 2.0→−2.0→+1.5=neto −0.5; límite topa en 0; cero UPDATEs de `amount_sp`.

## Inmutabilidad CP (reformulado en WP-24 — [[ADR-016 Deprecacion del gate CP y auto-lock]])
~~`cp_approved_at` count = **56**~~ — el conteo fijo dejó de ser el invariante: las aprobaciones manuales del PM lo movieron a 138 antes de WP-24, y el auto-lock lo hace crecer con cada sync (by design). El invariante vigente:
1. **Toda subtask activa con CP válido no-XXL queda lockeada** (`cp_approved_at NOT NULL`) tras el sync; XXL y sin-CP nunca se lockean.
2. **La inmutabilidad se mantiene**: un cambio de `cp` en Jira post-lock se ignora (flag `cp_modified_post_approval` + `cp_change_attempted_post_approval` en audit_log).
3. **Las filas históricas aprobadas manualmente** (`cp_approved_by NOT NULL`, 138 al 2026-07-01) quedan byte-idénticas; el auto-lock usa el sentinela `cp_approved_by = NULL`.
Verificación: `test_cp_autolock.py::test_golden_invariant_all_valid_non_xxl_locked` + `test_sync_cp_immutability.py`.

Enlaces: [[Atribucion de Tiempo WP-07h]] · [[Economia CP-SP]] · [[Patrones que Funcionan]]
