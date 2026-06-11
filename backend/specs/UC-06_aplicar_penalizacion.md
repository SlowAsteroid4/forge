# UC-06 — Aplicar penalización manual a una sub-task

**Tipo:** Forge Console / Workflow administrativo
**Audiencia:** Admin / PM
**Prioridad:** P1 — Necesario para casos no detectables automáticamente
**Sprint objetivo:** Día 7 del MVP

---

## Historia de usuario

Como **Admin/PM**, quiero aplicar manualmente una penalización a una sub-task con razón documentada, para casos donde el sistema automático no detecta el problema pero observo evidencia que justifica un debuff (ej. mala práctica reportada en code review, problema reportado en daily, etc.).

---

## Contexto

El sistema aplica debuffs automáticos según los disparadores del catálogo (D01-D16), pero hay casos cualitativos que requieren juicio humano. Este caso de uso permite al PM aplicar penalizaciones manualmente con trazabilidad completa.

Bajo OQ-12 acordada, las penalizaciones automáticas se aplican sin intervención, pero **el PM puede revertir o crear nuevas manualmente**, y el player puede apelar en la weekly.

---

## Criterios de aceptación

**AC-6.1** Desde el detalle de una sub-task (vista accesible desde múltiples lugares en Ops) existe un botón "Aplicar penalización".

**AC-6.2** Modal "Aplicar penalización" con:
- Player afectado (auto-detectado del assignee de la sub-task, editable si se justifica).
- Selector de debuff:
  - Catálogo completo de `debuffs` activos.
  - Opción "Custom" para penalización personalizada.
- Si es del catálogo: muestra el valor automático del debuff (no editable).
- Si es custom: permite ingresar SP a restar (negativo) y tipo (`sp_pct_reduction`, `sp_flat`, etc.).
- Campo obligatorio: "Razón" (mínimo 30 caracteres).
- Checkbox: "Notificar al player" (para Arena, en MVP solo log interno).

**AC-6.3** Al confirmar:
- Se crea entrada en `sp_adjustments`:
  - `player_id` del afectado
  - `sprint_id` actual
  - `subtask_key` de la sub-task
  - `adjustment_type = 'debuff_manual'`
  - `source_code` = código del debuff o `'CUSTOM'`
  - `sp_delta` = valor negativo
  - `reason` = texto ingresado
  - `applied_by` = admin.id
- Se recalcula `subtasks.sp_final` aplicando el ajuste.
- Se registra en `audit_log` con `action_type='manual_penalty_applied'`.
- Toast de confirmación en UI.

**AC-6.4** Vista de penalizaciones aplicadas en el sprint:
- Tabla con todos los `sp_adjustments` del sprint actual de tipo debuff (auto o manual).
- Columnas: Fecha, Player, Sub-task, Tipo, SP delta, Razón, Aplicado por, Estado apelación.
- Filtros por player, por tipo, por aplicado por.
- Permite ver detalle y revertir.

**AC-6.5** Revertir penalización (cuando se acepta apelación):
- Botón "Revertir" en cada fila de la tabla.
- Modal con razón de reversión obligatoria.
- Al confirmar:
  - Marca `sp_adjustments.is_appealed = 1`, `appeal_resolution = 'reversed'`, `appeal_resolved_by`, `appeal_resolved_at`, `appeal_notes`.
  - Crea nuevo `sp_adjustments` con `sp_delta` opuesto y `adjustment_type = 'reversal'`.
  - Recalcula `subtasks.sp_final`.
  - `audit_log` con `action_type='penalty_reversed'`.
- Reducción parcial: en lugar de reversión total, permite especificar nuevo valor (ej. original -10, reducir a -3).

**AC-6.6** Vista de apelaciones pendientes:
- Sección en Forge Console "Apelaciones".
- Lista de `sp_adjustments` marcados como `is_appealed = 1` y `appeal_resolution IS NULL`.
- El PM puede resolver cada una: upheld / reversed / reduced.
- En MVP local, las apelaciones se levantan presencialmente en la weekly y el PM las captura aquí.

**AC-6.7** Validaciones:
- No se permite penalizar a un player en un sprint ya cerrado.
- No se permite penalizar más que el SP total ganado en la sub-task (un sub-task de 5 SP no puede llevarse -100 SP por una penalización).
- Excepción: penalizaciones tipo `-100% SP` (D09, D14) sí pueden llevar el valor a 0, no más allá.

**AC-6.8** Notificación al player (en Arena, post-MVP):
- Banner en su perfil: "⚠ Penalización aplicada en [Sub-task X]. Razón: ..."
- CTA "Apelar" abre flujo de apelación digital (en MVP es presencial en weekly).

---

## Entidades involucradas

- `sp_adjustments` — destino principal
- `subtasks` — recálculo de `sp_final`
- `audit_log` — registros
- `debuffs` — catálogo
- `players` — afectado y aplicador

---

## Reglas de negocio

- **Penalizaciones automáticas (PVD OQ-12)**: se aplican sin intervención del PM cuando el motor detecta el disparador. El PM las ve en la tabla pero no las "aprueba".
- **Apelación presencial en weekly**: en MVP no hay flujo digital. El player levanta el tema, PM decide en el momento y captura la decisión en UC-06.
- **Inmutabilidad**: los registros de `sp_adjustments` nunca se UPDATE para borrar; siempre se INSERT de signo opuesto. Esto preserva auditabilidad.
- **Recálculo en cascada**: aplicar/revertir una penalización dispara recálculo de `sp_final` de la sub-task y del leaderboard si el sprint sigue activo.

---

## Out of scope para MVP

- Flujo digital de apelación (formulario que llena el player, etc.).
- Notificaciones push o email al penalizar.
- Approval workflow donde el PM propone y otro confirma.
- Penalizaciones que afectan a múltiples players simultáneamente (bulk).

---

## Dependencias

- **UC-01** (Sync) — necesita sub-tasks en BD.
- **Motor de cálculo de SP** (parte de Foundation) — recálculo en cascada.
- **Catálogo de debuffs seed** — para que la lista tenga opciones.

---

## Definición de hecho (DoD)

- [ ] Endpoint POST `/api/penalties` implementado.
- [ ] Endpoint POST `/api/penalties/{id}/reverse` implementado.
- [ ] Endpoint GET `/api/penalties?sprint_id=X` implementado.
- [ ] Modal de aplicación de penalización funcional.
- [ ] Vista de penalizaciones del sprint con filtros.
- [ ] Vista de apelaciones pendientes.
- [ ] Recálculo de `sp_final` correcto al aplicar/revertir.
- [ ] Validaciones de límite (no más de lo ganado) funcionan.
- [ ] `audit_log` registra todas las operaciones.
- [ ] Reversión crea registro de signo opuesto, no UPDATE.
