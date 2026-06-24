# UC-03 — Filtro global por proyecto en todas las vistas de Ops

**Tipo:** Forge Ops / UX transversal
**Audiencia:** Admin / PM / Director / Lead
**Prioridad:** P0 — Afecta toda la navegación
**Sprint objetivo:** Día 4 del MVP (junto con UC-02)

---

## Historia de usuario

Como **Admin/PM**, quiero filtrar todas las vistas de Forge Ops por uno de los 3 proyectos activos (`[YAPAPP]`, `[PLD]`, `[BSAPI]`) o ver el agregado de todos, para poder analizar cada línea de trabajo aisladamente sin perderme entre datos cruzados.

---

## Contexto

Yapsi opera 3 proyectos simultáneos con dinámicas, equipos y prioridades distintas. Un dashboard global está bien para visión ejecutiva, pero el trabajo diario del PM requiere foco proyecto-por-proyecto. El filtro debe ser persistente, visible y consistente entre vistas.

---

## Criterios de aceptación

**AC-3.1** En el header global de Forge Ops (justo arriba del side nav) existe un selector de proyecto:
- Opciones: "Todos los proyectos" (default), "YAPAPP - Yapsi App", "PLD - Prevención Lavado", "BSAPI - Backend Services API".
- Selector tipo dropdown con búsqueda si crece la lista.
- Indicador visual del proyecto actualmente seleccionado (color o badge).

**AC-3.2** El filtro afecta todas las vistas de Ops que muestran datos de trabajo:
- Dashboard (UC-02).
- Vistas por área (Backend, Frontend, Design, DB, Quality).
- Forecast (UC-07).
- Costos por área/dev.
- Reportes y export.

**AC-3.3** El filtro NO afecta:
- Vistas de configuración (engine config, players, integraciones).
- Audit log.
- Tienda admin / canjes (los canjes son por player, no por proyecto).

**AC-3.4** La selección persiste durante la sesión del navegador (localStorage o cookie). Al recargar, el filtro previo se mantiene.

**AC-3.5** La selección se refleja en la URL como query param (`?project=YAPAPP`), lo que permite:
- Compartir links a vistas filtradas.
- Bookmarks específicos por proyecto.
- Reflejar el estado al hacer back/forward del navegador.

**AC-3.6** Al cambiar el filtro:
- Todos los componentes de la vista actual recargan sus datos.
- Loading states son visibles.
- No se pierde el scroll position si la vista lo permite.

**AC-3.7** Cuando el filtro está activo en un proyecto específico, el resto de la UI lo refleja:
- Header de la vista muestra el nombre del proyecto.
- Breadcrumb incluye el proyecto (`Forge Ops > [YAPAPP] Yapsi App > Backend`).
- Color de acento sutil del proyecto (opcional, definido en design system).

**AC-3.8** Si el proyecto seleccionado no tiene datos para la vista actual (ej. PLD sin sub-tasks de Design), se muestra empty state claro: "Este proyecto no tiene datos de Design en el sprint actual."

---

## Entidades involucradas

- `projects` — catálogo del filtro
- Implícitamente todas las vistas que usen `subtasks.project_code`

---

## Reglas de negocio

- El filtro siempre opera sobre `subtasks.project_code` (denormalizado para queries rápidas).
- "Todos los proyectos" no filtra; suma/agrega todo lo activo.
- Proyectos con `is_active=0` no aparecen en el selector (pero sus datos históricos se mantienen en BD).
- Si se agrega un nuevo proyecto en el futuro (ej. `[MOSI]`), aparece automáticamente en el selector.

---

## Out of scope para MVP

- Filtro multi-select (elegir 2 de 3 proyectos). En MVP es 1 o todos.
- Filtro por área simultáneamente con proyecto (cada vista maneja sus propios sub-filtros).
- Permisos granulares por proyecto (en MVP cualquier admin ve todo).

---

## Dependencias

- **UC-01** (Sync Jira) — necesita `subtasks.project_code` poblado.

---

## Definición de hecho (DoD)

- [ ] Componente `<ProjectFilter />` implementado en el header global de Ops.
- [ ] Hook/context `useProjectFilter()` disponible para todas las vistas.
- [ ] Query params sincronizados con el estado del filtro.
- [ ] Persistencia en localStorage funciona.
- [ ] Dashboard (UC-02) reacciona correctamente al filtro.
- [ ] Mínimo 2 vistas adicionales validan el filtro funcionando (Backend area + Forecast).
- [ ] Empty states cuando no hay datos.
- [ ] No hay flickering al cambiar de filtro.
