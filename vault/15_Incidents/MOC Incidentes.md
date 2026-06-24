---
type: moc
tags: [incidentes]
---
# MOC — Incidentes (bugs con causa raíz)

Cada uno fue una **mentira de datos** o un footgun real. Patrón dominante: asumir en vez de auditar. Lecciones consolidadas en [[Patrones que Funcionan]].

| INC | Mentira / bug | Capa |
|---|---|---|
| [[INC-001 QA first-pass falso]] | 100% first-pass que no era | Métricas |
| [[INC-002 qa_biz_hours NULL]] | Tiempos de QA vacíos | Métricas |
| [[INC-003 Talla no sincronizada]] | Mitad de tallas ausentes | ETL |
| [[INC-004 Hero PO-Testing artefacto]] | Bottleneck señalando un fantasma | Analítica |
| [[INC-005 Tiempo de Edgar al dev]] | Devs cargando horas de QA | Tiempo |
| [[INC-006 Histories desordenadas]] | Cycle time arrancando tarde | Tiempo |
| [[INC-007 created_at es fecha de import]] | Lead time 0.0 | Datos |
| [[INC-008 gitignore lib]] | 9 archivos frontend invisibles para git | Repo |
| [[INC-009 WIP inflado e In Code]] | 666%, 43 WIP con Backlog, In Code sin contar | Pulso |
| [[INC-010 Sync parent null y 150 fantasma]] | Sync que crashea / reporta sin cambiar | ETL |
