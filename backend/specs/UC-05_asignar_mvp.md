# UC-05 — Asignar MVP del sprint al cierre

**Tipo:** Forge Console / Workflow de cierre de sprint
**Audiencia:** Admin / PM
**Prioridad:** P1 — Importante para la dinámica de gamificación
**Sprint objetivo:** Día 7 del MVP

---

## Historia de usuario

Como **Admin/PM**, quiero asignar el MVP del sprint al cierre, con un panel que me muestre candidatos sugeridos según métricas objetivas y permita justificar la decisión cualitativa, para reconocer comportamientos que el sistema automático no puede detectar.

---

## Contexto

El MVP del sprint es una categoría asignada manualmente por el PM (JPDS v2.0 sección 3.6). Mide cosas que un script no ve: cubrir a alguien ausente, mentorear a un nuevo, resolver un incidente fuera del área, documentar algo crítico.

Carga +10 SP al player ganador (buff B17 "Champion") más reconocimiento público en Arena. El sistema sugiere candidatos pero la decisión final es del PM.

---

## Criterios de aceptación

**AC-5.1** Existe una vista `/admin/sprints/{sprint_id}/close` que se vuelve disponible cuando el sprint está en su último día o ya pasó su `end_date`. Visible como "Cerrar sprint" en el menú admin.

**AC-5.2** La vista muestra un resumen del sprint terminado:
- Nombre y fechas.
- CP totales done.
- SP totales generados.
- Top 5 por SP en cada categoría (BE, FE, Design, DB, QA).
- Lista de bugs derivados resueltos.
- Sub-tasks destacadas por dificultad o impacto.

**AC-5.3** Una sección "Candidatos sugeridos para MVP" muestra 3-5 players con justificación automática:
- Player con mayor SP del sprint.
- Player con mejor M_calidad promedio.
- Player con más mentorías documentadas.
- Player con más desbloqueos a otros (M_cooperacion disparado).
- Player que resolvió un Bug crítico (severity high) en menos tiempo.

Cada candidato tiene su métrica destacada y su avatar/clase.

**AC-5.4** Selector de MVP:
- Dropdown con todos los players activos del sprint (todas las áreas, no solo top).
- Permite elegir un player que no esté en la lista de sugeridos.
- Campo obligatorio: "Razón del MVP" (text area, mínimo 20 caracteres).

**AC-5.5** Al confirmar el MVP:
- Se actualiza `sprints.mvp_player_id = player.id`, `sprints.mvp_reason = texto`.
- Se crea entrada en `sp_adjustments`:
  - `player_id` = mvp.id
  - `sprint_id` = sprint.id
  - `adjustment_type` = `'mvp_bonus'`
  - `source_code` = `'B17'`
  - `sp_delta` = +10
  - `reason` = el texto ingresado
  - `applied_by` = admin.id
- Se desbloquea achievement `ACH04 - Champion of the Realm` si es la primera vez.
- Se registra en `audit_log` con `action_type='mvp_assigned'`.
- Se marca `sprints.is_closed = 1` y `closed_at = NOW()` y `closed_by = admin.id`.

**AC-5.6** Una vez cerrado el sprint:
- No se pueden modificar más sub-tasks de ese sprint en Forge.
- El sync de Jira respeta el cierre (no actualiza sub-tasks ya cerradas).
- El sprint queda visible en read-only en navegación histórica.

**AC-5.7** Validaciones antes de cerrar:
- Todas las sub-tasks Done del sprint deben tener `sp_final` calculado.
- No deben quedar penalizaciones automáticas pendientes de aplicar.
- No deben quedar CP propuestos sin aprobar (warning, no bloqueante).
- Si hay validaciones bloqueantes, el botón "Cerrar sprint" está deshabilitado con tooltip explicativo.

**AC-5.8** Notificación al MVP:
- En su perfil de Arena aparece banner "🏆 MVP del sprint X" al siguiente login.
- En Forge Ops, el dashboard del próximo sprint muestra al MVP anterior en una sección "MVP previo".

**AC-5.9** Editar MVP retroactivamente:
- Posible solo dentro de 24h hábiles del cierre.
- Requiere razón del cambio.
- Revierte el ajuste anterior (crea nuevo `sp_adjustments` opuesto) y aplica el nuevo.
- Después de 24h, el MVP es definitivo.

**AC-5.10** Historial de MVPs:
- Vista `/admin/sprints/mvp-history` con tabla de todos los MVPs históricos.
- Cada fila: sprint, MVP, razón, fecha de asignación.
- Filtros por área del MVP, por player.

---

## Entidades involucradas

- `sprints` — destino del MVP
- `sp_adjustments` — bonus aplicado
- `achievement_unlocks` — desbloqueo de ACH04
- `audit_log` — registro
- `players` — candidatos y MVP

---

## Reglas de negocio

- **Cualquier player activo puede ser MVP**, incluso Daniela (DB) o Edgar (QA) que están en categorías solo. En su caso, el bono de +10 SP se aplica pero no compite con otros en ranking.
- **Chuy (PO) y Adán (Auxiliar) están fuera** del sistema de SP pero NO del MVP — pueden ser MVP si su contribución lo justifica. El bono se les acumula como "SP simbólico" que sirve para Wallet y tienda.
- **Solo un MVP por sprint**, no múltiples.
- **El MVP NO se sugiere para sprints que aún no han cerrado**: la vista solo aparece cuando `end_date <= today`.

---

## Out of scope para MVP

- Votación del equipo para MVP (peer-based MVP).
- Múltiples MVPs por categorías (MVP técnico + MVP cultural).
- Notificación automática por Slack al MVP.
- "MVP del trimestre" como categoría separada (post-MVP, v0.4).

---

## Dependencias

- **UC-02** (Dashboard sprint) — los candidatos se calculan con la misma data.
- **UC-09** (Login player) — para que el MVP vea su badge.
- **UC-13** (Achievement wall) — para reflejar el unlock de ACH04.

---

## Definición de hecho (DoD)

- [ ] Endpoint GET `/api/sprints/{id}/mvp-candidates` implementado.
- [ ] Endpoint POST `/api/sprints/{id}/close` implementado (incluye MVP).
- [ ] Vista `/admin/sprints/{id}/close` funcional.
- [ ] Validaciones bloqueantes/no-bloqueantes correctas.
- [ ] `sp_adjustments` se crea correctamente con tipo mvp_bonus.
- [ ] ACH04 se desbloquea la primera vez.
- [ ] Banner "MVP del sprint" visible en Arena del player.
- [ ] Historial de MVPs accesible y filtrable.
- [ ] Edición retroactiva dentro de 24h funciona.
