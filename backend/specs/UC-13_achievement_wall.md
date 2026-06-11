# UC-13 — Ver achievements desbloqueados y bloqueados

**Tipo:** Forge Arena / Vista de progresión
**Audiencia:** Player
**Prioridad:** P1 — Motor de retención y motivación de largo plazo
**Sprint objetivo:** Día 6 del MVP

---

## Historia de usuario

Como **Player**, quiero ver los achievements desbloqueados (los míos y los del resto del equipo) y los que me faltan, para tener objetivos claros más allá del sprint actual y reconocer logros de mis compañeros.

---

## Contexto

Los achievements son objetivos de mediano y largo plazo que premian patrones de excelencia (no solo volumen). Generan retención del sistema: aunque un dev no esté top en su liga este sprint, puede estar trabajando en desbloquear "Code Surgeon" o "Legendary Quarter".

El wall debe sentirse celebratorio: ver achievements desbloqueados es parte del reward; ver los locked motiva.

---

## Criterios de aceptación

**AC-13.1** Existe vista `/arena/achievements` accesible desde side nav de Arena ("Achievements" o "Hall").

**AC-13.2** Header con tabs:
- **My Wall** (default): mis achievements desbloqueados + locked.
- **Team Wall**: achievements desbloqueados por todo el equipo, ordenados por recencia.
- **Hall of Fame**: achievements legendary y mythic desbloqueados (de cualquier player).

**AC-13.3** Vista "My Wall":
- Grid responsive de cards (3-4 columnas en desktop).
- Achievements desbloqueados en color completo + borde dorado/según rareza + fecha de unlock.
- Achievements bloqueados en gris/silueta + descripción visible + progreso (si medible).
- Toggle "Mostrar bloqueados" / "Solo desbloqueados".
- Filtro por rareza (common/rare/epic/legendary/mythic).

**AC-13.4** Card de achievement (cualquier estado):
- Icono (color por rareza).
- Nombre.
- Descripción visible.
- Si desbloqueado: fecha de unlock + sprint en que se desbloqueó + bono SP recibido.
- Si bloqueado y medible: barra de progreso (ej. "8/10 sub-tasks Done sin bugs").
- Si bloqueado y no medible: descripción de cómo desbloquearlo.

**AC-13.5** Vista "Team Wall":
- Feed cronológico (más reciente primero) de unlocks del equipo.
- Cada entrada: avatar + nombre del player + achievement + fecha.
- Filtros: por área del player, por rareza.
- Genera sensación de comunidad y reconocimiento.

**AC-13.6** Vista "Hall of Fame":
- Wall destacado de unlocks legendary y mythic históricos.
- Cada uno con player, fecha, contexto.
- Visual más prestigioso (fondos oscuros, brillos, decoración).
- "Wall of Champions" — los más raros de obtener.

**AC-13.7** Animación de unlock:
- Cuando un player desbloquea un achievement, aparece notificación en su sesión:
  - Pop-up con animación arcade (sonido opcional, light by default).
  - Detalle: nombre, descripción, rareza, bono SP.
  - CTA "Ver en mi wall".
- Si el achievement es legendary o mythic, la animación es más elaborada y permanece más tiempo.

**AC-13.8** Detección y unlock automático:
- Después de cada sync de Jira o aplicación de SP, el motor evalúa achievements bloqueados.
- Si un player cumple condición, se crea registro en `achievement_unlocks` con `unlocked_at`, `sprint_id`, `trigger_context` (JSON con info del evento que disparó).
- Se aplica bono SP si `sp_bonus > 0` (entrada en `sp_adjustments` tipo `achievement_bonus`).

**AC-13.9** Click en un achievement abre detalle:
- Para los desbloqueados: muestra contexto del unlock (qué sub-task, qué sprint).
- Para los bloqueados: muestra condición técnica + progreso actual del player.

**AC-13.10** Stats globales:
- Header de "My Wall": "X de Y achievements desbloqueados (Z%)".
- Distribución por rareza visible.

**AC-13.11** Empty states:
- Si el player no tiene unlocks: "Aún no tienes achievements. Tu primer sub-task done desbloqueará 'First Blood'."
- Si Team Wall está vacío: improbable, pero "Aún no hay unlocks del equipo."

---

## Entidades involucradas

- `achievements` — catálogo
- `achievement_unlocks` — relación player ↔ achievement
- `players` — para el Team Wall y Hall of Fame
- `sp_adjustments` — bonos SP de tipo `achievement_bonus`

---

## Reglas de negocio

- **No repetibles en MVP**: UNIQUE constraint en `(player_id, achievement_code)` impide unlock duplicado.
- **Evaluación automática**: el motor evalúa todos los achievements después de cada sync, no a demanda.
- **Bonos SP se acumulan**: si el achievement tiene `sp_bonus > 0`, se aplica como ajuste en el sprint en que se desbloqueó.
- **Hall of Fame es de todo el equipo**: incluye unlocks de cualquier player en cualquier sprint histórico.
- **Achievements retroactivos**: si se agrega un nuevo achievement al catálogo, el motor evalúa retroactivamente si algún player ya lo cumplió (decisión: sí, se reconoce con fecha de "evaluación retroactiva").

---

## Out of scope para MVP

- Achievements custom creados por el PM.
- Compartir achievements en redes sociales / Slack.
- Achievements por equipo (no individuales).
- Achievements secretos (que ni siquiera aparezcan en locked).
- Sistema de "puntos extra" por achievements (más allá de `sp_bonus`).
- Notificaciones push externas (Slack, email) al desbloquear.

---

## Dependencias

- **Motor de achievements** (`engine/achievement_engine.py`) — dispatcher de condiciones.
- **UC-01** (Sync Jira) — disparador de evaluación.
- **UC-09** (Login) — sesión del player.

---

## Definición de hecho (DoD)

- [ ] Endpoint GET `/api/arena/achievements/mine` implementado.
- [ ] Endpoint GET `/api/arena/achievements/team` implementado.
- [ ] Endpoint GET `/api/arena/achievements/hall-of-fame` implementado.
- [ ] Motor de evaluación con dispatcher por `unlock_condition_code` implementado.
- [ ] Las 12 condiciones del catálogo seed implementadas en código (ACH01-ACH12).
- [ ] Vista `/arena/achievements` con 3 tabs.
- [ ] Cards de achievement con estados unlocked/locked.
- [ ] Progreso visible en achievements medibles.
- [ ] Animación de unlock al desbloquear.
- [ ] Detalle al click funcional.
- [ ] Empty states implementados.
