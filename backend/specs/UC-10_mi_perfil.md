# UC-10 — Ver mi perfil de player

**Tipo:** Forge Arena / Vista personal
**Audiencia:** Player
**Prioridad:** P0 — Pieza central de la experiencia Arena
**Sprint objetivo:** Día 5 del MVP

---

## Historia de usuario

Como **Player**, quiero ver mi perfil con mi clase, avatar, SP del sprint, buffs activos, quest log y mi progreso, para sentir identidad propia dentro del sistema y entender mi estado actual en una sola pantalla.

---

## Contexto

El perfil es la pantalla más visitada de Arena. Debe ser:
- **Personal**: refleja la identidad elegida (clase, avatar).
- **Vivo**: cambia constantemente con buffs/debuffs activos, quests.
- **Motivacional**: hace que el player quiera volver para ver su SP subir.
- **Honesto**: muestra debuffs y penalizaciones sin esconder.

Estéticamente, es la pantalla donde se concentra más el espíritu arcade del producto.

---

## Criterios de aceptación

**AC-10.1** Existe vista `/arena/me` accesible desde el side nav de Arena ("My Profile" o icono de player).

**AC-10.2** Header del perfil:
- Avatar grande (sprite predefinido).
- Nombre del player + emblema de clase.
- Área (BE/FE/Design/DB/QA) con badge.
- "Lead" badge si `is_lead=1`.
- Frame visual indicando el tier/rareza (común al inicio, evoluciona con achievements).

**AC-10.3** Sección "Stats del sprint actual":
- SP totales del sprint en grande (número destacado, animado).
- Posición actual en su liga.
- CP completados / CP asignados (con barra de progreso).
- QA first-pass rate (%) del sprint.
- Sub-tasks Done en sprint.

**AC-10.4** Sección "Buffs activos":
- Lista de buffs aplicados a sub-tasks actualmente en proceso o cerradas en el sprint.
- Cada buff con: icono, nombre narrativo, multiplicador, sub-task asociada.
- Tooltip al hover con descripción completa.

**AC-10.5** Sección "Debuffs / Curses activos":
- Penalizaciones del sprint actual.
- Cada uno: icono distinto (rojo/oscuro), nombre, SP delta, razón, fecha.
- CTA "Apelar" (en MVP redirige a "Levanta en la próxima weekly").

**AC-10.6** Sección "Quest log":
- Tabs: "Active" / "Ready" / "Done este sprint".
- Para cada sub-task asignada, una card con:
  - Key, summary corto.
  - Estado actual.
  - Proyecto (dungeon).
  - CP / SP esperado.
  - Tiempo en estado actual.

**AC-10.7** Sección "Wallet" (con detalles de la tienda):
- Balance total acumulado.
- Gastado este mes (con barra de progreso hacia el techo mensual de 100 SP).
- Restante gastable este mes.
- CTA "Ir a tienda".

**AC-10.8** Sección "Achievements progress":
- 3-5 achievements destacados que están "casi desbloqueados" (>70% de progreso).
- Cada uno con: icono, nombre, descripción, barra de progreso.
- CTA "Ver todos" lleva a `/arena/achievements`.

**AC-10.9** Sección "Historial reciente":
- Últimos 10 eventos: sub-task done, achievement desbloqueado, penalización, canje aprobado, etc.
- Timeline vertical con timestamps.

**AC-10.10** El perfil se actualiza automáticamente al regresar a la vista (sin refresh manual).

**AC-10.11** Estética:
- Pixel-art consistente con el design system.
- Animaciones: subida de SP con efecto numérico animado, brillo en buffs activos.
- Colores de rareza para frames y items.
- Tema arcade retro pero legible.

**AC-10.12** El player NO ve:
- Sus costos individuales.
- Detalle de penalizaciones de otros players.
- Datos administrativos.

---

## Entidades involucradas

- `players` — datos personales
- `classes`, `avatars` — visualización
- `subtasks` — quest log y stats
- `sp_adjustments` — buffs/debuffs activos
- `achievement_unlocks` — achievements
- `achievements` — catálogo (para los "casi desbloqueados")
- `redemptions` + view `player_wallet` — wallet
- `view monthly_spent_by_player` — techo mensual

---

## Reglas de negocio

- **Buffs visibles**: los que afectaron sub-tasks con `done_at` en el sprint actual O sub-tasks activas (todavía sin cerrar).
- **Debuffs visibles**: aplicados en el sprint actual; los apelados con `appeal_resolution='reversed'` se muestran tachados o en sección "Historial de apelaciones".
- **Achievements "casi desbloqueados"**: el motor evalúa qué falta para cada achievement bloqueado y rankea por % de progreso. Solo los achievements activos con condición medible.
- **Quest log**: incluye sub-tasks asignadas (`assignee_player_id = me.id`) del sprint actual.
- **Wallet balance**: tomado de la vista `player_wallet` ya definida en el schema.

---

## Out of scope para MVP

- Edición de avatar dentro del perfil (eso vive en `/arena/onboarding` o vista de configuración separada).
- Comparativa con otros players desde el perfil (eso vive en leaderboard).
- Compartir perfil externamente (link público).
- Editor pixel-art (post-MVP v0.4).
- Estadísticas históricas multi-sprint (post-MVP).

---

## Dependencias

- **UC-09** (Login player) — necesita sesión.
- **UC-15** (Selección de clase/avatar) — para que el perfil tenga identidad.
- **Motor de SP** — para que los buffs/debuffs estén calculados.

---

## Definición de hecho (DoD)

- [ ] Endpoint GET `/api/arena/me/profile` implementado (incluye todas las secciones).
- [ ] Endpoint GET `/api/arena/me/quests` (sub-tasks del sprint).
- [ ] Endpoint GET `/api/arena/me/buffs-debuffs` (activos del sprint).
- [ ] Endpoint GET `/api/arena/me/achievements-progress` (próximos a desbloquear).
- [ ] Vista `/arena/me` renderiza todas las secciones.
- [ ] Animaciones de SP subiendo funcionan.
- [ ] Estética pixel-art consistente con design system.
- [ ] Refresh automático al regresar a la vista.
- [ ] Empty states para cada sección si está vacía.
- [ ] Tooltips de buffs/debuffs funcionan.
