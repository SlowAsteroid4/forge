---
type: adr
estado: vigente
fecha: 2026-06
tags: [adr, personas, design]
---
# ADR-007 — Jesús = PO + DESIGN; "Equipo de Producto" → DESIGN agregado

**Contexto.** El PM declaró: "los diseñadores son Jesús, Sasha, Fran y Diego; Jesús es el PO". La auditoría (WP-15) encontró otra realidad en los datos: **Sasha y Fran no existen en Jira** (trabajan bajo la cuenta-grupo "Equipo de Producto", player 14, 84 Design Sub-tasks), y "Diego" en BD es Diego Candia, dev **BE** — no diseñador.
**Problema.** El roster declarado ≠ los datos. Crear players fantasma habría poblado métricas con gente que no produce; excluir a Jesús por ser PO habría borrado su producción real de diseño.
**Alternativas.** (a) Crear Sasha/Fran sin historial; (b) reasignar assignees vía changelog (el sync los revierte); (c) modelo honesto con lo que hay.
**Decisión.** (c), confirmada por el PM: **Jesús** = `role='PO'` (gobierno) **y** `area=DESIGN` (su diseño produce CP/SP/leaderboard); **"Equipo de Producto"** = entrada **agregada** con `area=DESIGN`, etiquetada "(equipo agregado)" en toda UI — nunca como individuo; **Diego no se mueve** (es BE). `LEADERBOARD_AREAS={BE,FE,DESIGN,DB,QA}` excluye PO como área.
**Consecuencias.** SP de DESIGN: 0 → 127.8; el área fantasma "PO" desapareció (`cda322f`). Arena debe presentar al agregado sin que compita como persona.
**Tradeoffs.** Sasha/Fran no tienen métricas individuales — fiel a cómo trabajan. Detección del grupo por `display_name` (frágil, [[Knowledge Gaps]]).
