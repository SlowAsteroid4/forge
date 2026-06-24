---
type: incident
tags: [incidente, qa]
---
# INC-001 — QA first-pass 100% falso

**Síntoma.** Todos los devs con 100% de first-pass — demasiado bueno para ser verdad.
**Causa raíz.** El cálculo buscaba **nombres de estados de QA que no existían** en los datos; al no encontrar rechazos, todo "pasaba a la primera". Un número perfecto que medía nada.
**Fix.** Estados reales de QA (`In QA`, `Ready for QA`, `Testing`) verificados con `SELECT DISTINCT` (`5409888`); luego comparativa vs ciclo anterior (WP-17a).
**Lección.** Un 100% (o 0%) uniforme es bandera roja, no éxito. Los nombres de estados **se verifican, nunca se asumen** → [[Estados Crudos vs Canonicos]].
