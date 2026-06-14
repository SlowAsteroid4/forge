---
type: moc
tags: [adr, decisiones]
---
# MOC — Decisiones de Arquitectura (ADRs)

El conocimiento más frágil del proyecto: vivía solo en el chat maestro. Cada ADR explica **por qué** Forge es como es.

| ADR | Decisión | Capa |
|---|---|---|
| [[ADR-001 Sprint a Ciclo]] | Ritmo Operativo reemplaza Sprint | Modelo temporal |
| [[ADR-002 Talla y sync-full]] | La talla era la correcta; el bug era la ventana JQL | ETL |
| [[ADR-003 Atribucion por convencion de estado]] | El tiempo se atribuye por estado, no por assignee | Tiempo |
| [[ADR-004 RfQA dev In QA Edgar]] | Ready for QA = dev; In QA/Testing = Edgar | Tiempo |
| [[ADR-005 Canonicos para agrupar]] | Canónicos = mostrar; WP-07h = atribuir (capas separadas) | Tiempo/Display |
| [[ADR-006 Lead desde lt_biz_hours]] | created_at es fecha de import; lead viene de WP-07h | Tiempo |
| [[ADR-007 Identidades]] | Jesús = PO + DESIGN; Equipo de Producto → DESIGN agregado | Personas |
| [[ADR-008 Clasificaciones durables]] | Lo de Forge vive donde el sync no pisa | ETL/Datos |
| [[ADR-009 WIP igual In Progress mas In Code]] | WIP estricto + semáforo 3/3/4/5 | Pulso |
| [[ADR-010 epic_kind y contenedores]] | Version Containers fuera del forecast | Forecast |
| [[ADR-011 Umbral 4 ciclos MVP mensual]] | Gate estricto ≥4; demo revertido append-only | Negocio |
| [[ADR-012 Apartados dinamicos]] | Filtro derivado de datos + KNOWN_APARTADOS | Analítica |
| [[ADR-013 Arena sin password]] | Selección de identidad, modelo local | Arena |
| [[ADR-014 Pulso read-only]] | El Pulso jamás escribe gamificación | Pulso |
| [[ADR-015 Forecast on-the-fly]] | Sin snapshots; ventana 4 ciclos; 3 fórmulas | Forecast |
