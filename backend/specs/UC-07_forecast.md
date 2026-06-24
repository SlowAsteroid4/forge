# UC-07 — Forecast con tres escenarios por épica activa

**Tipo:** Forge Ops / Vista ejecutiva
**Audiencia:** Director / Admin / PM
**Prioridad:** P1 — Pieza estratégica para dirección
**Sprint objetivo:** Día 6 del MVP

---

## Historia de usuario

Como **Director**, quiero ver el forecast con tres escenarios (optimista, realista, conservador) de cierre por épica activa, para poder comprometer fechas creíbles a stakeholders externos sin sobreprometer ni subestimar.

---

## Contexto

El JPDS v2.0 sección 2.3.4 define que **toda estimación se presenta en tres escenarios** — nunca un solo número con falsa precisión. La velocity se calcula sobre CP cerrados (no SP), por área, en ventana móvil. El cálculo se hace por área de la épica y el escenario por épica es el `max` de los escenarios por área (la épica termina cuando termina su área más lenta).

---

## Criterios de aceptación

**AC-7.1** Existe vista `/ops/forecast` accesible desde side nav "Analítica > Forecast".

**AC-7.2** Tabla principal lista todas las épicas activas (`status NOT IN ('Done','Cancelled')`):
- Key + Summary.
- Proyecto.
- CP total estimado de la épica.
- CP completado.
- % progreso.
- Fecha optimista.
- Fecha realista.
- Fecha conservadora.
- Bloqueos activos (count).

**AC-7.3** Al hacer click en una épica, se expande el detalle:
- Desglose por área (BE, FE, Design, DB, QA, etc.).
- Para cada área: CP pendiente, velocity histórica, semanas restantes.
- Las tres fechas se calculan según fórmulas del JPDS v2.0 sección 7.5:
  - **Optimista**: velocity = mejor semana del último trimestre × CP pendientes.
  - **Realista**: promedio últimas 4 semanas × 1.20 (factor fricción).
  - **Conservador**: (promedio - 1σ) × 1.30.
- La fecha de cierre de la épica = `max` de las fechas por área (la épica termina cuando termina su área más lenta).

**AC-7.4** Visualización gráfica de las 3 fechas en un timeline:
- Eje X: fechas (próximos 3-6 meses).
- Marcadores para optimista, realista, conservador con colores distintos.
- Marcador de "hoy" como línea vertical.
- Hover muestra fecha exacta y días restantes.

**AC-7.5** Filtros:
- Por proyecto (UC-03).
- Por estado de épica (In Progress, Backlog).
- Por owner / sponsor (campo en `epics`, post-MVP).

**AC-7.6** Indicadores visuales:
- 🟢 Verde si fecha realista < deadline comprometida (si existe).
- 🟡 Amarillo si fecha realista = deadline ± 1 semana.
- 🔴 Rojo si fecha realista > deadline.
- (Deadline comprometida es campo opcional en `epics`, post-MVP. En MVP solo se muestran las 3 fechas calculadas sin comparativa.)

**AC-7.7** Cálculo de velocity:
- Se calcula por área usando `subtasks` con `done_at` en la ventana de tiempo.
- Suma de `cp` de sub-tasks Done en el periodo / semanas del periodo = velocity (CP/semana).
- Para "mejor semana del trimestre" se segmenta por semanas y se toma la de mayor CP.
- Si no hay suficiente data histórica (<4 semanas), el sistema muestra advertencia: "Velocity calculada con menos de 4 semanas de datos. Forecast es preliminar."

**AC-7.8** Recálculo:
- El forecast se recalcula automáticamente al sincronizar Jira (UC-01).
- Botón "Recalcular" manual disponible.
- `last_calculated_at` visible en cada épica.

**AC-7.9** Export:
- Botón "Exportar a CSV" descarga la tabla principal.
- Botón "Exportar reporte ejecutivo" (post-MVP) genera PDF.

**AC-7.10** Empty states:
- Si no hay épicas activas: "No hay épicas en progreso. Selecciona un proyecto o ajusta los filtros."
- Si una épica no tiene CP estimado: "Esta épica no tiene CP estimado. Revisa el rollup de sus historias."

---

## Entidades involucradas

- `epics` — fuente principal
- `stories` — rollup de CP por épica
- `subtasks` — datos históricos para velocity
- `projects` — filtro

---

## Reglas de negocio

- **Velocity se calcula sobre CP, no SP**. El JPDS v2.0 es explícito en esto: SP es gamificación, CP es planning.
- **Tres escenarios siempre**: nunca presentar un solo número en UI ejecutiva.
- **Forecast por área, agregado a épica**: la fecha de la épica es el `max` de las fechas de sus áreas.
- **Ventana móvil**: el promedio se toma de las últimas 4 semanas calendario, no de los últimos 4 sprints (los sprints pueden tener huecos).
- **Si una épica tiene CP=0 en alguna área**: esa área se ignora del cálculo (no añade tiempo).

---

## Out of scope para MVP

- Comparación con deadlines comprometidos (requiere campo `target_date` en `epics`).
- Drill-down al detalle de cada sub-task pendiente desde el forecast.
- Forecast a nivel proyecto agregado (todas las épicas).
- Simulador "what-if" (si agrego N devs, cuánto se acorta).
- Confianza estadística más rigurosa (Monte Carlo, etc.).

---

## Dependencias

- **UC-01** (Sync Jira) — necesita histórico de sub-tasks Done.
- **Rollup CP** (parte de Foundation) — `epics.cp_total` y `stories.cp_total` deben estar calculados.
- **UC-03** (Filtro por proyecto) — filtros transversales.

---

## Definición de hecho (DoD)

- [ ] Endpoint GET `/api/forecast/epics?project=X` implementado.
- [ ] Función `engine.forecast.three_scenarios(epic_key)` implementada.
- [ ] Vista `/ops/forecast` con tabla y detalle expandible.
- [ ] Cálculo de velocity por área validado contra datos reales.
- [ ] 3 escenarios calculan correctamente según fórmulas JPDS v2.0.
- [ ] Filtros por proyecto y estado funcionan.
- [ ] Visualización timeline implementada.
- [ ] Advertencia cuando histórico <4 semanas funciona.
- [ ] Export CSV implementado.
