---
type: adr
estado: vigente
fecha: 2026-05
tags: [adr, tiempo]
---
# ADR-003 — El tiempo se atribuye por estado, no por assignee

**Contexto.** Para separar el tiempo del dev del de QA hay dos señales en el changelog: quién era assignee en cada momento, o en qué estado estaba la tarjeta.
**Problema.** El assignee en Jira es ruidoso (reasignaciones tardías, cuentas-grupo) y además **el sync lo reescribe en cada corrida** ([[ADR-008 Clasificaciones durables]]).
**Alternativas.** (a) Atribuir por assignee histórico; (b) por convención de estado (estado X ⇒ responsable Y); (c) híbrido.
**Decisión.** (b): el estado define al responsable — los estados de QA son tiempo de Edgar sin importar el assignee ([[ADR-004 RfQA dev In QA Edgar]]).
**Consecuencias.** Atribución robusta y reproducible; los buckets de [[Atribucion de Tiempo WP-07h]] se calculan solo del changelog de estados.
**Tradeoffs.** Si dos personas comparten un estado (no ocurre en el flujo actual), la convención no las distingue. Aceptado.
