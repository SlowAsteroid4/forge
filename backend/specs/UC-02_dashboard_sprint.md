# UC-02 — Dashboard general del sprint en curso

**Tipo:** Forge Ops / Vista ejecutiva
**Audiencia:** Admin / PM / Director / Lead
**Prioridad:** P0 — Cara principal de Ops
**Sprint objetivo:** Día 4 del MVP

---

## Historia de usuario

Como **Admin/PM**, quiero ver el dashboard general del sprint en curso para conocer de un vistazo el estado de delivery, calidad y participación del equipo sin tener que abrir Jira ni revisar reportes separados.

---

## Contexto

Este dashboard es el "home" de Forge Ops y la primera pantalla que ve el PM cada mañana. Debe contestar 4 preguntas en menos de 3 segundos: cuánto se ha hecho, qué falta, dónde están los bloqueos, y cómo va la calidad. La densidad de información importa más que la estética.

---

## Criterios de aceptación

**AC-2.1** Existe una vista `/ops/dashboard` accesible desde el side nav como "Dashboard > Sprint actual".

**AC-2.2** En la parte superior se muestra el header del sprint:
- Nombre del sprint (`Sprint 2026-05-W19`).
- Fechas inicio y fin.
- Días transcurridos / días totales (`8 de 10 días`).
- Indicador visual de progreso temporal (barra horizontal).

**AC-2.3** Se muestran 4 KPI cards principales en grid de 4 columnas:
- **CP Done** — suma de `cp` de sub-tasks con `status='Done'` y `sprint_id=actual`. Con comparativa vs sprint anterior (`+12%` verde o `-5%` rojo).
- **CP Pendientes** — suma de `cp` de sub-tasks con `status NOT IN ('Done','Cancelled')` y `sprint_id=actual`.
- **SP Totales del Sprint** — suma de `sp_final` de sub-tasks Done en el sprint.
- **Bugs Derivados** — conteo de Bug Sub-tasks creadas con link `is caused by` a sub-tasks del sprint.

**AC-2.4** Debajo, una sección "Progreso por área" con cards en grid de 5 columnas (BE, FE, Design, DB, QA):
- CP Done / CP Total del área en el sprint.
- Barra horizontal de progreso (% completado).
- Número de devs activos en esa área.
- Indicador de bottleneck si el área tiene WIP excedido.

**AC-2.5** Una sección "Devs activos" muestra una tabla con:
- Avatar + nombre del player.
- Área.
- Sub-tasks activas (count).
- Sub-tasks Done este sprint (count).
- SP acumulado en sprint actual.
- Estado: 🟢 productivo / 🟡 WIP alto / 🔴 bloqueado / ⚪ inactivo.

Filtrable por área. Ordenable por SP, count, nombre.

**AC-2.6** Una sección "Alertas activas" muestra:
- Sub-tasks abandonadas >14 días (D10).
- Sub-tasks en Waiting >72h sin ticket de bloqueo (D13).
- Devs con WIP excedido (D11).
- CP propuestos pendientes de aprobación (L/XL sin `cp_approved_at`).
- Bugs derivados sin atribución resuelta.

Cada alerta es clickeable y lleva al detalle.

**AC-2.7** Existe un filtro global por proyecto (`[YAPAPP]`, `[PLD]`, `[BSAPI]`, o "Todos") que afecta todas las secciones del dashboard.

**AC-2.8** Existe un selector de sprint para navegar a sprints pasados (read-only).

**AC-2.9** En la parte superior derecha existe un botón "Sync now" que dispara UC-01 sin salir del dashboard. Mientras corre, las KPI cards muestran skeleton loader.

**AC-2.10** Los datos se calculan desde la BD local. No hay llamadas en vivo a Jira. El timestamp del último sync es visible siempre en algún lugar de la vista ("Última sincronización: hace 23 min").

---

## Entidades involucradas

- `sprints` — sprint activo
- `subtasks` — fuente de todos los KPIs
- `players` — devs activos y sus métricas
- `projects` — filtro
- `sp_adjustments` — alertas relacionadas a penalizaciones

---

## Reglas de negocio

- "Sprint actual" = sprint con `is_active=1`. Si no hay sprint activo, el dashboard muestra "No hay sprint activo" con CTA para crear uno.
- "Dev activo" = player con `is_active=1` y al menos 1 sub-task asignada en el sprint.
- "WIP alto" = dev con sub-tasks en estados activos > umbral del área (3 BE/FE, 4 Design, 5 DB).
- "Bloqueado" = dev con todas sus sub-tasks activas en `Blocked` o `Waiting`.

---

## Out of scope para MVP

- Personalización de qué KPIs se muestran (orden fijo en MVP).
- Drill-down detallado a nivel sub-task desde el dashboard (eso vive en vistas específicas).
- Export del dashboard a PDF (post-MVP, v0.4).
- Comparativas multi-sprint en gráficas (post-MVP).

---

## Dependencias

- **UC-01** (Conectar Jira) — necesita datos sincronizados.
- **UC-03** (Filtro por proyecto) — el filtro vive aquí.

---

## Definición de hecho (DoD)

- [ ] Endpoint GET `/api/dashboard/sprint?project=X` implementado.
- [ ] Vista `/ops/dashboard` renderiza todas las secciones.
- [ ] Todos los KPIs calculan correctamente contra datos reales de Yapsi.
- [ ] Filtro por proyecto funciona en las 4 secciones.
- [ ] Comparativa con sprint anterior visible y precisa.
- [ ] Alertas se generan correctamente y son clickeables.
- [ ] Loading states y empty states implementados.
- [ ] Responsive mínimo a 1366×768 (laptop estándar).
