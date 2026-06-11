# UC-16 — Pulso operativo en vivo

**Tipo:** Forge Ops / Vista en tiempo real
**Audiencia:** Admin / PM / Lead / Equipo completo (lectura)
**Prioridad:** P0 — Pieza central del modelo de Ritmo
**Sprint objetivo:** Día 5 del MVP

---

## Historia de usuario

Como **Admin/PM**, quiero ver en tiempo real el estado de la cola operativa para detectar bloqueos, WIP excedido y reprioritizaciones del día sin esperar al cierre del ciclo, **sin que estos eventos contaminen las métricas competitivas del leaderboard ni del MVP**.

Como **Lead de área**, quiero ver el Pulso de mi área para tomar decisiones tácticas durante el día.

Como **miembro del equipo**, quiero ver el Pulso global para entender dónde está el trabajo y dónde puedo ayudar.

---

## Contexto

El Pulso es uno de los tres horizontes canónicos del JPDS (ver Documento 03.1, Módulo de Ritmo Operativo). Es la única vista que refleja el momento presente sin agregar a una ventana temporal cerrada. **No genera métricas competitivas**: es un espacio operativo donde el caos puede ocurrir sin distorsionar el resto del sistema.

El Pulso responde a 4 preguntas en menos de 5 segundos:
- ¿Qué se está moviendo ahora?
- ¿Qué está atorado?
- ¿Qué cambió de prioridad hoy?
- ¿Alguien excedió su límite WIP?

---

## Criterios de aceptación

**AC-16.1** Existe una vista `/ops/pulse` accesible desde el side nav como "Dashboard > Pulso". También accesible como tab paralela en `/ops/dashboard` (Dashboard del Ciclo).

**AC-16.2** La vista refresca automáticamente cada 60 segundos, con timestamp visible "Actualizado hace X segundos".

**AC-16.3** En la parte superior se muestra una franja con 5 indicadores globales:
- **Sub-tasks activas** — total en `In Progress`, `In Review`, `In QA`.
- **Sub-tasks bloqueadas** — total en `Blocked`. Color rojo si > 0.
- **Sub-tasks esperando** — total en `Waiting`.
- **Cola Ready** — total en `Ready`.
- **Aging máximo** — sub-task activa más vieja (en días hábiles).

**AC-16.4** Sección "WIP por área" con cards en grid (BE, FE, Design, DB, QA):
- WIP actual / Límite WIP del área.
- Semáforo: verde (< 80% del límite), amarillo (80-100%), rojo (> 100%).
- Detalle expandible con lista de sub-tasks activas del área y su assignee.

**AC-16.5** Sección "Bloqueos en curso" con tabla:
- Sub-task (key + summary).
- Assignee.
- Área.
- Tiempo en `Blocked` (horas hábiles).
- Razón del bloqueo (último campo `block_reason` del changelog).
- Ordenado por tiempo en bloqueo descendente.
- Cualquier bloqueo > 8 horas hábiles tiene indicador 🚨.

**AC-16.6** Sección "Movimientos del día" con dos columnas:
- **Entraron a Ready hoy** — lista de sub-tasks que pasaron a `Ready` en las últimas 24h hábiles.
- **Salieron de Ready hoy** — lista de sub-tasks que pasaron de `Ready` a otro estado distinto de `In Progress` (ej: volvieron a `Backlog`, o se cancelaron). Estas son **reprioritizaciones legítimas** y se registran sin penalización.

**AC-16.7** Sección "Aging crítico":
- Lista de sub-tasks en estado activo con más de 5 días hábiles de antigüedad.
- Cada fila: key, summary, assignee, días en estado actual, edad total desde creación.
- Botón "Marcar para revisión" que crea una nota en la sub-task sin cambiar su estado.

**AC-16.8** Sección "Cola Ready priorizada":
- Top 10 sub-tasks en `Ready` ordenadas por prioridad (campo Jira) y antigüedad.
- Para cada una: key, summary, área, CP, tiempo en `Ready`.
- Indica al PM cuál sería la siguiente sub-task a tomar por cada área.

**AC-16.9** Filtros disponibles en la vista:
- Por área (multi-select).
- Por proyecto.
- Por player (assignee).

**AC-16.10** Exportación rápida:
- Botón "Exportar snapshot" genera un PNG/PDF del estado actual del Pulso.
- Útil para compartir en reuniones tácticas o reportes urgentes.

**AC-16.11** Notificaciones (post-MVP, marcar como out of scope inicial):
- Alerta al PM cuando un bloqueo supera 24h hábiles.
- Alerta al lead de área cuando WIP excede 110% del límite.

---

## Entidades involucradas

- `subtasks` — fuente principal de datos del Pulso
- `players` — assignees
- `cycles` — para validar que el ciclo activo existe
- Vista SQL `pulse_now` — agrupación oficial del Pulso (ver `forge_entidades_v2_ciclos.md` sección 9)

---

## Reglas de negocio

- **El Pulso nunca alimenta leaderboards**. Las métricas mostradas aquí son operativas, no competitivas.
- **Las reprioritizaciones son legítimas y no se penalizan**. Solo quedan auditadas en `audit_log` con `action_type = 'priority_change'`.
- **El Pulso es read-only** para el equipo. Solo PM y leads pueden tomar acciones desde aquí (marcar para revisión, exportar).
- **El Pulso siempre refleja el ahora**, no la ventana del ciclo. Una sub-task `Done` ayer no aparece aquí (ya está en el dashboard del ciclo).
- **El refresh es por polling cada 60s**, no websocket. Mantenerlo simple para el MVP.

---

## Out of scope para MVP

- Notificaciones push (Slack, email) automáticas.
- Vista de Pulso por player individual (solo agregado por área).
- Histórico del Pulso (snapshots cada hora del día).
- Predicción de aging crítico basada en patrones históricos.
- Integración con Jira para acciones directas (asignar, mover de estado).

---

## Dependencias

- **UC-01** (Conectar Jira) — para que los datos estén sincronizados.
- **UC-02** (Dashboard del Ciclo) — vista complementaria, se cruzan via tab.
- **UC-06** (Aplicar penalización) — los debuffs `D11 Greedy Hoarder` (WIP excedido) se disparan a partir de los WIP detectados aquí (al cierre del ciclo, no en el Pulso).

---

## Definición de hecho (DoD)

- [ ] Endpoint GET `/api/pulse/now` implementado con respuesta < 500ms.
- [ ] Vista `/ops/pulse` funcional con refresh automático cada 60s.
- [ ] Vista SQL `pulse_now` creada e indexada correctamente.
- [ ] Todos los semáforos de WIP por área funcionando con los límites configurados.
- [ ] Detección de bloqueos > 8h funcionando con indicador visual.
- [ ] Detección de aging > 5 días hábiles funcionando.
- [ ] Filtros por área, proyecto y player operativos.
- [ ] Exportación a PNG/PDF funcional.
- [ ] Sin escritura a leaderboards ni a `sp_adjustments` desde este UC (verificado).
- [ ] Reprioritizaciones quedan registradas en `audit_log` sin penalización.
