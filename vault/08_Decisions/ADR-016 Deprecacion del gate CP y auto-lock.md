---
type: adr
estado: vigente
fecha: 2026-07
tags: [adr, engine, cp, sync]
---
# ADR-016 — Deprecación del gate de aprobación CP y auto-lock

**Contexto.** UC-04 definía un gate P0: el PM aprobaba manualmente el CP de cada subtask L/XL antes de que avanzara a Ready. En la práctica el gate no discriminaba nada: del histórico en `audit_log`, 137 aprobaciones directas vs. 1 ajuste y 1 rechazo. La cola solo agregaba fricción y una pantalla que nadie necesitaba operar. Pero el gate estaba enredado con cuatro cosas que sí importan: la [[Inmutabilidad CP|inmutabilidad del CP]] (`cp_approved_at IS NOT NULL` impide que el sync sobreescriba `cp`), la compuerta L/XL, la detección de XXL, y el golden `cp_approved_at = 56`.

**Problema.** Borrar la pantalla sin más rompería la inmutabilidad (nada volvería a poblar `cp_approved_at`), dejaría a las L/XL flaggeadas para siempre como "pendientes", y perdería la visibilidad de XXL.

**Alternativas.** (a) Mantener el gate manual (statu quo: fricción sin valor); (b) eliminar `cp_approved_at` y anclar la inmutabilidad a otra cosa (migración riesgosa de un invariante ganado con sangre); (c) **auto-lock**: el sistema fija `cp_approved_at` automáticamente para todo CP válido no-XXL, al final del sync.

**Decisión.** (c), del PM (chat maestro, WP-24):
- `auto_lock_cp()` corre al final de `SyncOrchestrator.sync_all()`, **después** de los upserts — el valor legítimo de Jira aterriza primero y luego se lockea.
- Lockea toda subtask activa (no podada) con `cp` y talla poblados, talla ≠ XXL y `cp_approved_at IS NULL`: `cp_approved_at = now()`, `cp_approved_by = NULL`, `cp_approval_required = false`, más `audit_log` `cp_auto_locked`.
- **Sentinela de sistema = `cp_approved_by NULL`** (con `cp_approved_at NOT NULL`): distingue el lock automático de las 138 aprobaciones manuales históricas (todas con id del PM). No se creó un player SYSTEM para no contaminar leaderboard/identidades.
- **XXL nunca se lockea** (talla rechazada, debe partirse). Sobrevive como sección de alerta en la pantalla nueva y como alerta `xxl_detected` del dashboard.
- El flujo manual se retira: endpoints approve/adjust/reject y su UI. El histórico de `audit_log` se conserva. La pantalla se reconvierte a **"Subtasks sin CP" por apartado** (read-only, reutiliza la derivación de [[ADR-012 Apartados dinamicos]]).
- El warning de cierre "CP propuestos sin aprobar" se elimina (el estado ya no existe).

**Consecuencias.**
- La inmutabilidad del CP queda intacta y ahora es universal: todo CP válido queda sellado en el primer sync que lo ve.
- La compuerta L/XL pasa sola, sin clic: una L/XL con talla legítima queda lockeada y deja de estar "pendiente". (Nota de auditoría WP-24: la compuerta nunca fue un bloqueo duro de status — era alerta de dashboard + warning de cierre; ambas quedan resueltas por el auto-lock.)
- **Se pierde "ajustar y aprobar"**: el CP queda congelado al valor de Jira. Una talla mal puesta se corrige en Jira *antes* del sync; después del lock, el cambio se ignora y queda `cp_change_attempted_post_approval` en `audit_log` (como siempre).
- El golden "cp_approved_at = 56" se reformula (ver [[Golden Cases]]): el conteo fijo deja de existir; el invariante nuevo es *toda subtask activa con CP válido no-XXL está lockeada tras el sync, y la inmutabilidad se mantiene*. Las filas históricas no se tocan.
- Primera corrida real: ~285 subtasks se lockearán en el siguiente `make sync` tras el merge.

**Tradeoffs.** Se renuncia a la revisión humana de tallas grandes a cambio de cero fricción; la calibración de tallas se audita por métricas (multiplicadores/eficiencia), no por gate. Si el negocio vuelve a necesitar un gate, se reintroduce *encima* del auto-lock (p. ej. excluyendo tallas L/XL del lock), sin migración de datos.

Enlaces: UC-04 (reescrito, `backend/specs/UC-04_aprobacion_cp.md`) · [[Golden Cases]] · [[ADR-012 Apartados dinamicos]] · [[Economia CP-SP]]
