---
type: learning
tags: [aprendizaje, patrones]
---
# Patrones que Funcionan (destilado de 21 WPs)

1. **Auditar antes de construir (PASO 0).** Leer el código real + queries de diagnóstico antes de escribir una línea. Las dos veces que se saltó (WP-20) o se hizo a medias, salió un bug. La auditoría también corrige al arquitecto: el roster de diseñadores (WP-15) y las 37 vs 22 estados (WP-17a) contradijeron lo declarado — y los datos ganaron.
2. **Cruce manual de números clave.** Sumar a mano y comparar contra el servicio cazó el bug de histories desordenadas y validó velocity/atribución. Ningún test sintético sustituye esto.
3. **No creerle al log; contar.** "150 actualizadas" no significa nada; `COUNT(*)` antes/después sí.
4. **Los casos del PM son criterio de aceptación literal.** Alondra=2, Daniel sin Backlog, YAP-721: van en el prompt y se demuestran con salidas reales.
5. **Append-only para valores sensibles.** Revertir = INSERT opuesto. La metadata sí se actualiza; el valor jamás.
6. **Un número honesto vale más que uno bonito.** "Preliminar", "sin comparativa", "—" (div/0), "sin apartado": admitir incertidumbre es lo opuesto del 100% falso.
7. **Separar capas que parecen una.** Categoría canónica ≠ atribución de tiempo; clasificación de Forge ≠ dato de Jira; WIP operativo ≠ agrupación de métricas. Cada confusión de capas fue un bug.
8. **Métricas imposibles como alarmas.** lead < cycle, 100% uniforme, 666% — programar invariantes que griten.
9. **Definiciones de negocio las define el negocio.** "Qué es WIP" lo decide el PM, no el código.
10. **1 sesión = 1 WP, con Handoff verificable.** Cuando el loop se saltó (WP-18, fixes extra), quedó deuda de revisión que aún se paga.

Enlaces: [[MOC Incidentes]] · [[Convenciones de Ingenieria]] · [[Golden Cases]]
