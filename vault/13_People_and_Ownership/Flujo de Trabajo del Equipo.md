---
type: domain
tags: [personas, flujo]
---
# Flujo de Trabajo del Equipo (canónico, del PM)

1. **Adán** crea la épica → la analiza y la llena → genera las **historias de usuario** con todos sus datos → las pasa a **refinamiento**.
2. **Jesús (PO)** revisa cada historia; si necesita cambios, los hace él → la pasa a **diseño** → genera las **subtasks de diseño** → las trabajan los diseñadores (Jesús + Equipo de Producto).
3. Con el diseño listo, Jesús pasa la historia a **Ready** con su subtask interna de diseño ya en Done.
4. Los **devs** generan sus propias subtasks bajo la historia. Las recién creadas pueden quedar **sin assignee**: son la **cola de trabajo disponible del área** (por eso el Pulso las muestra etiquetadas "Sin asignar", no las esconde).
5. Cuando un dev **empieza una subtask**, la historia pasa a **In Progress**.

## Implicaciones en métricas
- El diseño es una **fase real con tiempos propios** → sección de tiempos de Design en Analítica.
- Las subtasks sin assignee son legítimas (cola), no datos sucios — pero 9 activas sin dueño es señal a vigilar ([[Knowledge Gaps]]).
- DB nombra su trabajo activo `In Code` ([[Definicion de WIP]]).

Enlaces: [[Equipo Yapsi]] · [[Estados Crudos vs Canonicos]]
