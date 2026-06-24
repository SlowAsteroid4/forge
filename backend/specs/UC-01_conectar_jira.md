# UC-01 — Conectar instancia de Jira y sincronización automática

**Tipo:** Foundation / ETL
**Audiencia:** Admin / PM
**Prioridad:** P0 — Bloqueante para todo lo demás
**Sprint objetivo:** Día 2 del MVP

---

## Historia de usuario

Como **Admin**, quiero conectar mi instancia de Jira a Forge para que el sistema sincronice automáticamente todas las sub-tasks de los proyectos configurados, y que pueda forzar una sincronización manual cuando lo necesite.

---

## Contexto

Forge depende de Jira como fuente de verdad operativa. Sin sincronización funcional, ninguna métrica, leaderboard, dashboard ni cálculo de SP es posible. Este caso de uso es el cimiento sobre el que se construyen todos los demás.

Bajo el modelo local, la sincronización corre manualmente desde Forge Console antes de cada weekly. No hay cron automático en MVP — el PM dispara el sync cuando lo necesita.

---

## Criterios de aceptación

**AC-1.1** Existe una vista en Forge Console `/admin/integrations/jira` donde el Admin puede:
- Ingresar la URL de la instancia de Jira (`https://beyapsi-org.atlassian.net`).
- Ingresar el email del usuario API.
- Ingresar el API token (campo password, no se muestra después de guardado).
- Probar la conexión con un botón "Test connection".

**AC-1.2** Al hacer "Test connection", el sistema:
- Hace una llamada de prueba a `/rest/api/3/myself` de Jira.
- Muestra ✓ verde con el nombre del usuario autenticado si la conexión funciona.
- Muestra ✗ rojo con el mensaje de error si falla (401, 403, timeout, DNS).

**AC-1.3** Las credenciales se persisten cifradas en disco (no en texto plano). En MVP local basta con encriptación simétrica con clave en variable de entorno.

**AC-1.4** Existe un botón "Sync now" que dispara el ETL completo:
- Pulla todas las épicas que coincidan con prefijos `[YAPAPP]`, `[PLD]`, `[BSAPI]`.
- Pulla todas las stories hijas de esas épicas.
- Pulla todas las sub-tasks hijas de esas stories.
- Para cada sub-task, pulla el changelog completo.
- Persiste en `epics`, `stories`, `subtasks` (UPSERT por `jira_key`).
- Guarda el changelog raw en `subtasks.raw_changelog` como JSON.

**AC-1.5** Durante el sync, la UI muestra progreso:
- "Sincronizando épicas... 12/12"
- "Sincronizando stories... 87/87"
- "Sincronizando sub-tasks... 234/234"
- "Procesando changelogs... 234/234"
- Tiempo total al terminar.

**AC-1.6** El sync es **idempotente**. Correrlo dos veces seguidas no duplica datos ni rompe cálculos.

**AC-1.7** Al terminar el sync, el sistema:
- Dispara recálculo de tiempos (`adj_ct_biz`, `qa_first_pass`, etc.) en `subtasks`.
- Dispara recálculo de CP rollup en `stories` y `epics`.
- Marca `last_synced_at` y `last_calculated_at` en las filas afectadas.

**AC-1.8** Si el sync falla a mitad de proceso:
- Las filas ya persistidas no se pierden.
- Se registra el error en `audit_log` con `action_type='sync_failed'`.
- La UI muestra el error con suficiente detalle para diagnosticar.

**AC-1.9** El historial de sincronizaciones es visible en `/admin/integrations/jira/history`:
- Timestamp de cada sync.
- Duración.
- Conteos (épicas/stories/sub-tasks procesadas).
- Status (success / partial / failed).
- Último error si aplica.

---

## Entidades involucradas

- `epics` — destino UPSERT
- `stories` — destino UPSERT
- `subtasks` — destino UPSERT (incluye `raw_changelog`)
- `projects` — referencia para mapear prefijos
- `audit_log` — registro de sync events

---

## Reglas de negocio

- El matching de épica a proyecto es por `substring` de `projects.jira_prefix` en `epic.summary`. Ejemplo: una épica con summary `"[YAPAPP] Onboarding completo"` se asocia a `projects.code = 'P01'`.
- Si una épica no matchea ningún prefijo conocido, se persiste con `project_code = NULL` y se loguea en `audit_log` para que el Admin la revise.
- Las sub-tasks que ya no aparezcan en Jira (borradas) se marcan en BD con un campo `is_deleted=1` en lugar de borrarse físicamente. Esto protege la historia de SP.

---

## Out of scope para MVP

- Webhooks de Jira para sync en tiempo real.
- Cron automático.
- Sync incremental por timestamp (en MVP se hace sync completo cada vez; con ~300 sub-tasks tarda <2 min, es aceptable).
- Soporte para múltiples instancias de Jira (single-org Yapsi, single-instance).

---

## Dependencias

Ninguna. Este es el primer caso de uso. Bloquea a UC-02, UC-03, UC-04 y todos los demás.

---

## Definición de hecho (DoD)

- [ ] Endpoint POST `/api/integrations/jira/test` implementado y testeado.
- [ ] Endpoint POST `/api/integrations/jira/sync` implementado y testeado.
- [ ] Vista frontend `/admin/integrations/jira` funcional.
- [ ] Sync completo con datos reales de Yapsi corre sin error.
- [ ] Idempotencia validada (correr 2 veces seguidas no rompe nada).
- [ ] Errores manejados y visibles en UI.
- [ ] `audit_log` registra el sync.
- [ ] Documentación interna: cómo generar API token en Atlassian.
