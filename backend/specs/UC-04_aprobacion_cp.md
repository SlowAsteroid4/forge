# UC-04 — Aprobación de CP para sub-tasks L/XL

**Tipo:** Forge Console / Workflow administrativo
**Audiencia:** Admin / PM
**Prioridad:** P0 — Quality gate del JPDS
**Sprint objetivo:** Día 7 del MVP

---

## Historia de usuario

Como **Admin/PM**, quiero aprobar manualmente el CP propuesto para sub-tasks de talla L (5 CP) o XL (8 CP) antes de que pasen a estado `Ready`, para evitar inflación de puntos y mantener la integridad del sistema.

---

## Contexto

El JPDS v2.0 (sección 2.1.3) establece que **el PM es el aprobador final de CPs de tallas grandes**. Esto previene auto-inflación, garantiza que las estimaciones críticas tengan revisión humana, y mantiene calibrado el motor.

Sub-tasks XS/S/M (1, 2, 3 CP) no requieren aprobación — se confía en el dev y se audita por muestreo mensual. XXL (13 CP) no se acepta nunca: se rompe la sub-task antes de continuar.

---

## Criterios de aceptación

**AC-4.1** Existe una vista `/admin/cp-approvals` accesible desde Forge Console como "CP Aprobaciones Pendientes". Visible en el side nav con badge numérico si hay items pendientes.

**AC-4.2** La vista muestra una tabla con sub-tasks que cumplen:
- `complexity_size IN ('L','XL')`
- `cp_approval_required = 1`
- `cp_approved_at IS NULL`
- `status = 'Backlog'` (todavía no pasaron a Ready)

Columnas: Key, Summary, Área, Player propuesto, Talla propuesta, CP propuesto, Fecha de propuesta, Tiempo esperando.

**AC-4.3** Cada fila tiene 3 acciones:
- **✓ Aprobar** — Acepta el CP tal como fue propuesto.
- **✎ Ajustar y aprobar** — Permite cambiar la talla a una diferente (con el CP correspondiente) y aprobar.
- **✗ Rechazar** — Marca la sub-task como rechazada con razón obligatoria.

**AC-4.4** Al aprobar (sin ajuste):
- Se actualiza `subtasks.cp_approved_by = admin.id` y `cp_approved_at = NOW()`.
- Se registra en `audit_log` con `action_type='cp_approved'`.
- La sub-task ya puede pasar a `Ready` cuando Jira la mueva.
- Notificación in-app al player que propuso (opcional en MVP).

**AC-4.5** Al ajustar y aprobar:
- Se muestra modal con selector de talla (XS/S/M/L/XL) — XXL bloqueado.
- Se muestra el CP equivalente automáticamente.
- Campo obligatorio: "Razón del ajuste".
- Al confirmar: se actualiza `complexity_size`, `cp`, se marca aprobación.
- `audit_log` con `action_type='cp_adjusted_and_approved'` y razón.

**AC-4.6** Al rechazar:
- Modal con campo obligatorio "Razón del rechazo".
- La sub-task queda con `cp_approval_required = 1` y `cp_approved_at = NULL`.
- Se marca `subtasks.cp_rejection_reason` (campo a agregar al schema).
- En Jira se podría comentar automáticamente (post-MVP).
- El player debe reescribir o partir la sub-task.

**AC-4.7** Detección automática de XXL:
- Si una sub-task se sincroniza con `complexity_size = 'XXL'`, no se acepta.
- Aparece en una sección separada "XXL detectadas (requieren ruptura)".
- El admin no puede aprobarla; solo puede marcarla como "Notificada al equipo" (lo que se hace offline).

**AC-4.8** Vista de detalle al click en la sub-task:
- Summary completo.
- Descripción.
- Validaciones / criterios de aceptación.
- Tech considerations.
- Link directo a Jira.
- Histórico de cambios de CP (si hubo).

**AC-4.9** Filtros disponibles:
- Por área.
- Por player que propuso.
- Por proyecto.
- Por tiempo esperando (>3 días en cola = alerta).

**AC-4.10** Si una sub-task L/XL es aprobada y posteriormente alguien intenta cambiar su CP en Jira:
- El sistema detecta el cambio en el sync.
- NO acepta el cambio (CP es inmutable post-aprobación, JPDS v2.0).
- Genera alerta en `audit_log` y notificación al admin.
- En la UI aparece flag "CP modificado en Jira post-aprobación, ignorado".

---

## Entidades involucradas

- `subtasks` — campos `cp`, `complexity_size`, `cp_proposed_*`, `cp_approved_*`
- `audit_log` — registro de aprobaciones/rechazos/ajustes
- `players` — referencia al admin que aprueba

---

## Reglas de negocio

- **CP inmutable post-aprobación**: una vez `cp_approved_at IS NOT NULL`, ningún UPDATE de Jira sobrescribe `cp`.
- **Solo Admin/Owner aprueban**: Tech Leads ven la cola pero no pueden aprobar (en MVP).
- **XXL bloqueado siempre**: no hay flujo de aprobación para XXL, solo notificación de ruptura.
- **Aprobación retroactiva no permitida**: si una sub-task L/XL ya está en estados avanzados (In Progress, etc.) sin aprobación, el sistema marca alerta pero no recalcula CP retroactivamente — eso requiere decisión manual del PM.

---

## Out of scope para MVP

- Aprobación bulk (seleccionar 5 sub-tasks y aprobar de un click).
- Delegación de aprobación a Tech Leads por área.
- Workflow de "revisión a 2 ojos" (requiere 2 aprobadores).
- Sugerencia automática de talla por IA (planeado para v0.4 según JPDS v2.0 sec 2.1.4).
- Notificaciones por Slack/email.

---

## Dependencias

- **UC-01** (Sync Jira) — necesita sub-tasks con `complexity_size` poblado.
- **Custom field "Complexity" en Jira** debe existir y estar mapeado en el ETL.

---

## Definición de hecho (DoD)

- [ ] Endpoint GET `/api/cp-approvals/pending` implementado.
- [ ] Endpoint POST `/api/cp-approvals/{subtask_key}/approve` implementado.
- [ ] Endpoint POST `/api/cp-approvals/{subtask_key}/adjust` implementado.
- [ ] Endpoint POST `/api/cp-approvals/{subtask_key}/reject` implementado.
- [ ] Vista `/admin/cp-approvals` funcional con tabla, filtros y acciones.
- [ ] Detección de XXL funciona en sync.
- [ ] CP inmutable validado: cambiar CP en Jira post-aprobación se ignora.
- [ ] Audit log registra correctamente las 3 acciones.
- [ ] Modal de ajuste valida que razón sea obligatoria.
