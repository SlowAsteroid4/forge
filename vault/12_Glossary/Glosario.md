---
type: glossary
tags: [glosario]
---
# Glosario Forge / JPDS

- **Apartado** — sub-división del proyecto por prefijo de épica: [YAPI]/[YPAPP]/[YPNX]/[CAY]/[PLD] + "Sin apartado".
- **B17 / B17M** — bonos de MVP semanal (+5 SP) / MVP del Mes (+10 SP).
- **Canónico** — una de las 9 categorías de medición del Manifiesto. Opuesto: **crudo** (string real de Jira, 37 históricos).
- **Ciclo** — semana operativa Lun–Vie; reemplazó "Sprint". Estados: active/closed/archived.
- **Coordinación** — los 8 terceros vivos (subtasks flotantes), no épicas.
- **CP (Complexity Points)** — complejidad por talla (XS=1…XL=8); inmutables tras aprobación.
- **Cycle time** — primer In Progress canónico → Done, horas hábiles.
- **dev_resp** — horas de responsabilidad del dev (incluye su cola Ready for QA, excluye In QA).
- **Equipo de Producto** — cuenta-grupo de Jira (player 14) que agrega el diseño de Sasha y Fran; área DESIGN, etiquetada "(equipo agregado)".
- **First-pass (QA)** — % de tarjetas que pasan QA a la primera; se compara vs ciclo anterior.
- **In Code** — estado de trabajo activo exclusivo de DB; cuenta como WIP.
- **Lead time** — creación real en Jira → Done (`lt_biz_hours`).
- **MVP semanal / del Mes** — reconocimiento del ciclo (+5) / del mes (+10, solo entre MVPs semanales, gate ≥4 ciclos).
- **Pozo de datos** — la saga WP-07a–j que cerró 8 mentiras de datos antes de construir Ops.
- **Pulso** — vista live del AHORA; read-only, no compite.
- **Reversal** — INSERT de signo opuesto en `sp_adjustments` (jamás UPDATE).
- **SP (Score Points)** — moneda de Arena: CP × multiplicadores + bonos − penalizaciones.
- **Talla** — XS/S/M/L/XL desde `customfield_10851`; origen del CP.
- **Ventana Móvil** — últimos 4 **ciclos cerrados** (no semanas calendario); base de velocity/forecast.
- **Version Container** — épica-cajón para tareas sin épica (YAP-66, YAP-130); fuera del forecast.
- **WIP** — In Progress + In Code, nada más. Semáforo 3/3/4/5 por área.

Enlaces: [[JPDS - Contrato de Medicion]] · [[Estados Crudos vs Canonicos]]
