---
type: integration
tags: [jira, integracion]
---
# Jira — Mapa de Integración

- **Instancia**: `beyapsi-org.atlassian.net` · **Proyecto**: YAP (único; los "proyectos" del PM son [[Apartados de Proyecto]]).
- **Jerarquía**: Épica → Story → Subtask. Los terceros viven como subtasks `Coordination` **sin padre** ([[Terceros - Coordinacion]]).
- **Campos clave**: `customfield_10851` = **talla** (XS–XL → CP); `priority` (estándar, usado en la cola Ready del Pulso); changelog (`raw_changelog`) = fuente de transiciones (37 estados históricos, histories sin ordenar — [[ETL Jira - Conocimiento Critico]]).
- **Lo que Jira NO da**: fecha de creación en el changelog (por eso lead = `lt_biz_hours`), `block_reason`, estado `Waiting` poblado — huecos conocidos ([[Knowledge Gaps]]).
- **Identidades**: la cuenta-grupo **"Equipo de Producto"** (`712020:e855360b-…`, player 14) agrupa el trabajo de diseño de Sasha y Fran, que **no tienen cuenta Jira propia** ([[ADR-007 Identidades]]). Detección actual por `display_name` — frágil si renombran la cuenta.
- **Dirección del flujo**: Jira → Forge únicamente. Forge **jamás escribe a Jira**. Las clasificaciones propias de Forge (area, epic_kind, role, costos) viven en campos que el sync no toca ([[ADR-008 Clasificaciones durables]]).

Enlaces: [[ETL Jira - Conocimiento Critico]] · [[Estados Crudos vs Canonicos]]
