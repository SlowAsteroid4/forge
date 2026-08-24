# UC-04 — Auto-lock de CP y worklist de subtasks sin CP

**Tipo:** Forge Console / Visibilidad operativa
**Audiencia:** Admin / PM
**Prioridad:** P1 — Visibilidad del trabajo sin tallar
**Reescrito:** WP-24 (2026-07) — deprecación del gate de aprobación manual (ver ADR-016)

---

## Historia de usuario

Como **Admin/PM**, quiero que el CP de toda subtask con talla válida quede **lockeado
automáticamente** durante el sync, y quiero **ver las subtasks que aún no tienen CP,
agrupadas por apartado**, para detectar trabajo sin tallar y subtasks XXL que
requieren ruptura — sin tener que aprobar nada a mano.

---

## Contexto

La versión original de este UC definía un gate manual: el PM aprobaba (o ajustaba, o
rechazaba) el CP de cada subtask L/XL antes de que avanzara. En la práctica el gate no
aportaba: **se aprobaba prácticamente todo tal cual** (al momento de la deprecación:
137 aprobaciones directas, 1 ajuste, 1 rechazo, según audit_log). El chat maestro
decidió (WP-24, ADR-016)
reemplazar el gate por un **auto-lock** que preserva lo que sí importaba del flujo:

1. **Inmutabilidad del CP** — `cp_approved_at IS NOT NULL` sigue siendo lo que impide
   que el sync de Jira sobreescriba `cp`/`complexity_size`.
2. **XXL como talla rechazada** — una XXL (13 CP) nunca se acepta: no se lockea y se
   muestra como alerta ("requiere ruptura").

Lo que se pierde deliberadamente: "ajustar y aprobar". El CP queda congelado al valor
que trae Jira. Si una talla está mal, se corrige **en Jira antes del sync** (o queda
registrada la discrepancia post-lock en `audit_log`, como siempre).

---

## Criterios de aceptación

**AC-4.1 (auto-lock)** Al final de cada sync (`SyncOrchestrator.sync_all`), toda
subtask activa (no podada) con `cp` y `complexity_size` poblados, talla ≠ XXL y
`cp_approved_at IS NULL` queda lockeada:
- `cp_approved_at = now()`
- `cp_approved_by = NULL` (sentinela de sistema — distingue el lock automático de las
  aprobaciones manuales históricas, que llevan el id del PM)
- `cp_approval_required = false`
- Registro en `audit_log` con `event_type='cp_auto_locked'` y `actor_player_id=NULL`.

**AC-4.2 (orden del pipeline)** El auto-lock corre **después** de los upserts del sync:
el valor legítimo de Jira aterriza primero y luego se lockea, nunca antes.

**AC-4.3 (idempotencia)** Una subtask ya lockeada no se re-lockea ni cambia. Una
segunda corrida del auto-lock produce 0 cambios. Las filas históricas aprobadas
manualmente quedan intactas.

**AC-4.4 (XXL nunca se lockea)** `complexity_size = 'XXL'` es talla rechazada: el
auto-lock la ignora y aparece en la sección de alerta "XXL detectadas — requieren
ruptura" de la pantalla nueva, y como alerta `xxl_detected` en el dashboard.

**AC-4.5 (inmutabilidad post-lock, sin cambios)** Si alguien cambia el CP en Jira
después del lock: el sync NO acepta el cambio, marca `cp_modified_post_approval=true`
y registra `cp_change_attempted_post_approval` en `audit_log` (comportamiento
heredado del flujo original, intacto).

**AC-4.6 (pantalla nueva, read-only v1)** Existe la vista `/operations/cp-worklist`
("Subtasks sin CP") en el side nav, con badge numérico del total. Muestra:
- Subtasks con `cp IS NULL` (no podadas), **agrupadas por apartado** derivado del
  prefijo `[XXX]` de la épica (derivación WP-21/ADR-012, vía story → epic), con
  **"Sin apartado" como categoría de primera clase** (al final).
- Grupos colapsables con contador. Por subtask: key (link a Jira), summary, área,
  player, status, antigüedad en BD.
- Sección de alerta con las XXL detectadas.
- **Sin acciones de escritura** — asignar CP inline es un WP futuro.

**AC-4.7 (endpoint)** `GET /api/cp-worklist` devuelve `{total, groups[], xxl_total,
xxl_items[], jira_base_url}`. Cero escrituras.

**AC-4.8 (flujo manual retirado)** Los endpoints `POST /api/cp-approvals/{key}/approve`,
`/adjust`, `/reject`, `/mark-xxl-notified` y `GET /api/cp-approvals/pending`,
`/xxl-detected`, `/{key}` **no existen**. El histórico de `audit_log`
(`cp_approved`, `cp_adjusted_and_approved`, `cp_rejected`, `xxl_notified`) se conserva.

**AC-4.9 (cierre de ciclo)** El warning "CP propuestos sin aprobar" del resumen de
cierre fue eliminado — ese estado ya no existe.

---

## Entidades involucradas

- `subtasks` — `cp`, `complexity_size`, `cp_approved_at`, `cp_approved_by`,
  `cp_approval_required`, `pruned_at`
- `audit_log` — `cp_auto_locked` (nuevo) + histórico del flujo manual (conservado)
- `epics`/`stories` — derivación de apartado (prefijo `[XXX]` del summary de la épica)

---

## Reglas de negocio

- **CP inmutable post-lock**: una vez `cp_approved_at IS NOT NULL`, ningún UPDATE de
  Jira sobrescribe `cp` (sin cambios vs. la regla original).
- **XXL bloqueado siempre**: no se lockea, no se acepta; solo visibilidad de ruptura.
- **Sentinela de sistema**: `cp_approved_at NOT NULL` + `cp_approved_by NULL` ≡
  auto-lock. `cp_approved_by NOT NULL` ≡ aprobación manual histórica.
- **Golden reformulado**: ya no existe el conteo fijo (`= 56`); el invariante es
  *"toda subtask activa con CP válido no-XXL está lockeada tras el sync, y la
  inmutabilidad se mantiene"* (ver `vault/09_Testing/Golden Cases.md`).

---

## Out of scope

- Asignar/editar CP inline desde la pantalla (WP futuro).
- Cualquier flujo de aprobación manual (deprecado, no vuelve).
- Notificaciones (Slack/email/in-app).

---

## Dependencias

- **UC-01** (Sync Jira) — el auto-lock vive dentro del pipeline de sync.
- **WP-21/ADR-012** — derivación dinámica de apartados.

---

## Definición de hecho (DoD)

- [x] `auto_lock_cp()` en `services/engine/cp_autolock.py`, invocado al final de
      `sync_all` (post-upserts).
- [x] Idempotente; XXL/sin-CP/podadas/históricas excluidas; `audit_log` por lock.
- [x] Endpoints del flujo manual retirados; `audit_log` histórico conservado.
- [x] `GET /api/cp-worklist` agrupado por apartado + sección XXL, read-only.
- [x] Vista `/operations/cp-worklist` con grupos colapsables y alerta XXL.
- [x] Warning "CP sin aprobar" eliminado del resumen de cierre.
- [x] Tests: auto-lock (lock/skip/idempotencia/históricas), inmutabilidad post-lock,
      endpoint (agrupado, read-only), golden reformulado.
