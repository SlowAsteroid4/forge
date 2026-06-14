# UC-17 — Cierre Mensual: Asignar MVP del Mes

**Tipo:** Forge Console / Ritual mensual de cierre
**Audiencia:** Admin / PM
**Prioridad:** P1 — Capa superior del reconocimiento humano
**Sprint objetivo:** Día 9 del MVP

---

## Historia de usuario

Como **Admin/PM**, quiero asignar el MVP del Mes al final del último ciclo de cada mes, eligiendo entre los 4 (o 5) MVPs semanales del mes, para preservar el peso simbólico del reconocimiento humano (achievement ACH04 "Champion of the Realm") sin sobrecargar el ritual semanal.

---

## Contexto

El módulo de Ritmo del JPDS (Documento 03.1) distribuye el reconocimiento humano en dos cadencias:
- **MVP Semanal (+5 SP)**: reconocimiento frecuente, calibrado para no desbalancear el leaderboard.
- **MVP del Mes (+10 SP)**: capa superior, elegido **entre los MVPs semanales del mes**, preserva la mecánica del achievement ACH04 con la misma magnitud que tenía el "MVP del sprint" anterior.

Este UC es el ritual mensual que cierra esa capa. Se ejecuta el último viernes de cada mes, después del cierre del Ciclo correspondiente (que ya designó al MVP semanal de esa última semana).

---

## Criterios de aceptación

**AC-17.1** Existe una vista `/admin/months/{YYYY-MM}/close` accesible desde el side nav como "Cierres > Mes actual" cuando:
- El último ciclo del mes está en estado `closed`.
- No existe aún una fila en `mvp_monthly` para `(iso_year, iso_month)`.

**AC-17.2** La vista muestra un resumen del mes:
- Año y mes (`Mayo 2026`).
- Lista de ciclos del mes (4 o 5) con fecha de cierre y MVP semanal asignado.
- KPIs agregados: CP totales del mes, SP totales generados, sub-tasks done, bugs derivados, achievements desbloqueados.

**AC-17.3** Sección "MVPs Semanales del Mes" con cards horizontales (uno por ciclo):
- Avatar + nombre del MVP semanal.
- Ciclo (ej: `Ciclo 2026-W18`).
- Razón del MVP semanal (texto completo).
- Métricas destacadas: SP del ciclo, M_calidad promedio, sub-tasks done en el ciclo.
- Achievements desbloqueados durante ese ciclo.

**AC-17.4** Selector de MVP del Mes:
- Radio button entre los MVPs semanales del mes.
- **Solo se puede elegir un player que haya sido MVP semanal en al menos un ciclo del mes**. Validación: `player_id IN (SELECT mvp_player_id FROM cycles WHERE iso_year + iso_month en el rango)`.
- Campo obligatorio: "Razón del MVP del Mes" (text area, mínimo 30 caracteres).

**AC-17.5** Al confirmar el MVP del Mes:
- Se crea fila en `mvp_monthly`:
  - `player_id` = mvp.id
  - `iso_year`, `iso_month`
  - `reason` = texto ingresado
  - `sp_bonus` = 10
  - `source_cycle_ids` = JSON array con todos los `cycle.id` del mes
  - `assigned_at` = NOW()
  - `assigned_by` = admin.id
- Se crea entrada en `sp_adjustments`:
  - `player_id` = mvp.id
  - `cycle_id` = id del último ciclo del mes
  - `adjustment_type` = `'mvp_monthly_bonus'`
  - `source_code` = `'B17M'` (variante mensual del buff Champion)
  - `sp_delta` = +10
  - `reason` = "MVP del Mes " + iso_year + "-" + iso_month + ": " + texto
  - `applied_by` = admin.id
- Si es la primera vez que el player es MVP del Mes, se desbloquea achievement `ACH04 - Champion of the Realm` (si no se había desbloqueado ya por MVP semanal).
- Se registra en `audit_log` con `action_type = 'mvp_monthly_assigned'`.

**AC-17.6** Validaciones bloqueantes antes de cerrar el mes:
- El último ciclo del mes debe estar en estado `closed`.
- No deben existir penalizaciones automáticas pendientes de aplicar en ningún ciclo del mes.
- El selector debe tener al menos una opción válida (4 MVPs semanales mínimo).

**AC-17.7** Notificación al MVP del Mes:
- Banner especial en su perfil de Arena: "🏆 MVP del Mes Mayo 2026" — visible por 7 días.
- Mensaje en Achievement Wall: "Champion of the Realm: nominado MVP del Mes".

**AC-17.8** Editar MVP del Mes retroactivamente:
- Posible solo dentro de **72h hábiles** desde la asignación (más amplio que el MVP semanal por su peso simbólico).
- Requiere razón del cambio en `audit_log`.
- Revierte el `sp_adjustment` anterior (crea uno opuesto con `sp_delta = -10`) y aplica el nuevo.
- Después de 72h, el MVP del Mes es definitivo.

**AC-17.9** Historial de MVPs del Mes:
- Vista `/admin/months/mvp-history` con tabla:
  - Mes, MVP, razón, fecha de asignación, número de MVPs semanales que tuvo en ese mes.
- Filtros: por player, por año.
- Export a CSV/XLSX.

**AC-17.10** Vista pública en Arena:
- Sección "Salón del Mes" mostrando los últimos 12 MVPs del Mes en formato carousel/grid.
- Visible para todos los players del equipo.

---

## Entidades involucradas

- `mvp_monthly` — destino del MVP del mes
- `sp_adjustments` — bonus aplicado
- `achievement_unlocks` — desbloqueo de ACH04 si aplica
- `audit_log` — registro
- `cycles` — fuente de los MVPs semanales del mes
- `players` — candidatos y MVP

---

## Reglas de negocio

- **El MVP del Mes solo se elige entre los MVPs semanales del mes**. No es posible elegir a un player que no haya sido MVP en ningún ciclo del mes.
- **Si un mes tiene 5 ciclos** (raro pero posible cuando el primer lunes del mes es muy temprano), los 5 MVPs semanales son candidatos.
- **Si un mes tiene 4 ciclos** (caso típico), los 4 son candidatos.
- **Un player puede ser MVP del Mes múltiples veces** durante el año, no hay restricción anti-repetición.
- **El MVP del Mes puede coincidir con haber sido MVP semanal varias veces ese mes** — eso de hecho lo hace más probable como candidato natural.
- **No hay MVP del Año** en el MVP inicial; ese ritual queda para v0.4.

---

## Out of scope para MVP

- Votación del equipo para MVP del Mes (peer-based).
- MVP del Año / MVP del Trimestre.
- Reconocimiento económico real adicional (bono monetario).
- Notificación automática por Slack al MVP del Mes.
- Integración con HR/payroll para reconocimientos formales.

---

## Dependencias

- **UC-05** (Cerrar Ciclo / MVP Semanal) — debe estar completo para los 4 ciclos del mes antes de poder ejecutar este UC.
- **UC-09** (Login player) — para que el MVP vea su badge especial.
- **UC-13** (Achievement wall) — para reflejar ACH04 si aplica.
- **UC-10** (Mi perfil) — para mostrar el banner del MVP del Mes.

---

## Definición de hecho (DoD)

- [ ] Endpoint GET `/api/months/{YYYY-MM}/candidates` implementado (lista MVPs semanales del mes).
- [ ] Endpoint POST `/api/months/{YYYY-MM}/close` implementado.
- [ ] Vista `/admin/months/{YYYY-MM}/close` funcional.
- [ ] Validación que solo permite elegir entre MVPs semanales del mes.
- [ ] Validación que requiere 4+ ciclos cerrados del mes antes de habilitar el cierre.
- [ ] `mvp_monthly` se crea correctamente con `source_cycle_ids` poblado.
- [ ] `sp_adjustment` con `adjustment_type='mvp_monthly_bonus'` y `sp_delta=+10` se aplica.
- [ ] ACH04 se desbloquea la primera vez si no se había desbloqueado por MVP semanal.
- [ ] Banner "MVP del Mes" visible en Arena del player por 7 días.
- [ ] Edición retroactiva dentro de 72h funciona correctamente con reversión de SP.
- [ ] Historial de MVPs del Mes accesible y filtrable.
- [ ] Salón del Mes visible en Arena para todo el equipo.
- [ ] Cron automático mensual notifica al PM cuando el cierre está habilitado.
