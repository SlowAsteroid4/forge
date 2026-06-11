# UC-08 — Ver costo agregado por área del último trimestre

**Tipo:** Forge Ops / Vista ejecutiva
**Audiencia:** Director / Admin
**Prioridad:** P2 — Importante para dirección, no bloqueante para arranque
**Sprint objetivo:** Post-MVP fase 0.3 (cuando se capturen costos reales)

---

## Historia de usuario

Como **Director**, quiero ver el costo agregado por área del último trimestre desglosado en costo total, CP producidos y costo por CP, para evaluar la rentabilidad de cada área y tomar decisiones de inversión, contratación o ajuste.

---

## Contexto

Este caso de uso responde a la **Pregunta 2 del JPDS v2.0** ("Costo y rentabilidad"): cuánto cuesta cada CP que produce cada área. Es el insumo principal para decisiones ejecutivas sobre headcount, comparativas internos vs externos, y justificación de la inversión en el equipo.

En MVP la captura de costos es manual (cuando estén los datos). Antes de tener costos, esta vista mostrará el desglose de CP/throughput sin el componente monetario.

---

## Criterios de aceptación

**AC-8.1** Existe vista `/ops/costs/by-area` accesible desde side nav "Costos > Por área" (sección solo visible para Admin/Owner/Director).

**AC-8.2** Selector de periodo:
- "Trimestre actual" (default).
- "Trimestre anterior".
- "Últimos 12 meses".
- Custom range (date pickers).

**AC-8.3** Tabla principal por área (BE, FE, Design, DB, QA):
- Área.
- # de players activos en el periodo.
- CP totales producidos (suma de `subtasks.cp` con `done_at` en el periodo).
- SP totales generados.
- Costo total del área (suma de costos individuales).
- Costo promedio por CP.
- Costo promedio por SP.
- Comparativa con periodo anterior (delta en %).

**AC-8.4** Cálculo del costo individual por player:
- Si `employment_type='internal'`: `monthly_salary` × meses en el periodo.
- Si `employment_type='external'`: estimación basada en horas (post-MVP) o costo manual.
- Si el player no tiene costo capturado: aparece con valor "—" y nota "Costo no capturado".

**AC-8.5** Vista expandida por área (click para desplegar):
- Tabla de players de esa área con sus métricas individuales.
- Columnas: Player, CP, SP, Costo total, Costo/CP, Costo/SP.
- Permite identificar el player más rentable y el menos rentable.

**AC-8.6** Comparativa interno vs externo:
- Card resumen con costo promedio por CP de internos vs externos por área.
- Insight automático: "Externos en Backend cuestan 2.3× más por CP que internos."

**AC-8.7** Gráfica de barras:
- Costo total por área en el periodo.
- Apilada con interno (azul) vs externo (amarillo).

**AC-8.8** Gráfica de evolución:
- Línea de costo/CP por área a lo largo de los últimos 12 meses.
- Permite ver si una área se está volviendo más cara o más eficiente.

**AC-8.9** Export:
- CSV con la tabla completa.
- Reporte ejecutivo PDF (post-MVP).

**AC-8.10** Privacidad y permisos:
- Solo visible para roles Admin, Owner, Director.
- Tech Leads NO ven esta vista.
- Players NO ven esta vista en absoluto.

**AC-8.11** Empty state:
- Si ningún player tiene costo capturado: mensaje claro con CTA "Capturar costos en /admin/devs".

---

## Entidades involucradas

- `players` — costos individuales (`monthly_salary`, `hourly_rate`)
- `subtasks` — CP y SP producidos en el periodo
- `projects` — filtro opcional
- `sprints` — para mapear periodos a sprints

---

## Reglas de negocio

- **Costos son privados**: solo Admin/Owner/Director pueden ver. Tech Leads y Players nunca.
- **Internos**: el costo del periodo = `monthly_salary` × meses completos en el periodo. Si el player se unió a mitad de mes, se prorratea.
- **Externos por horas**: en MVP el costo se captura manualmente (campo `hourly_rate` × horas estimadas). Post-MVP se podría integrar con sistema de timesheets.
- **Externos con tope**: si `monthly_hours_cap` está definido, el costo máximo del mes = `hourly_rate × monthly_hours_cap`.
- **CP/SP**: se cuentan los producidos en el periodo (`done_at` cae en el rango), no los asignados.
- **División por cero**: si un player tiene costo pero 0 CP producidos, se muestra "∞" o "—" con nota "Sin producción medible".

---

## Out of scope para MVP

- Captura automática de horas trabajadas (integración con timesheets).
- Forecast de costos futuros basado en velocity.
- Comparativa de costo con benchmark de mercado.
- Cálculo de ROI por feature/épica.
- Reporte de "costo de un bug" (tiempo invertido × tarifa).

---

## Dependencias

- **UC-01** (Sync Jira) — CP/SP histórico.
- **Captura de costos por player** — funcionalidad en `/admin/devs` (otro caso de uso administrativo).
- **UC-03** (Filtro proyecto) — opcional pero esperado.

---

## Definición de hecho (DoD)

- [ ] Endpoint GET `/api/costs/by-area?period=X` implementado.
- [ ] Endpoint GET `/api/costs/by-dev?period=X` implementado.
- [ ] Vista `/ops/costs/by-area` funcional con tabla y expansión.
- [ ] Cálculo prorrateado de costos internos correcto.
- [ ] Manejo de players sin costo capturado.
- [ ] Permisos: Tech Lead no puede acceder, redirect a 403.
- [ ] Gráficas (barras apiladas + evolución) funcionan.
- [ ] Export CSV funcional.
- [ ] Empty state con CTA cuando no hay costos.
