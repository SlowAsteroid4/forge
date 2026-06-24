---
type: incident
tags: [incidente, repo]
---
# INC-008 — `.gitignore lib/` escondía frontend/lib

**Síntoma.** Archivos nuevos en `frontend/lib/` jamás aparecían en `git status`.
**Causa raíz.** La regla `lib/` del .gitignore raíz (pensada para venvs de Python) ignoraba **también** `frontend/lib/`: 9 archivos (incl. `utils.ts`, `api.ts`) sin trackear — **un clone limpio no compilaba**. WP-08/09 los dejaron fuera en silencio.
**Fix.** Regla acotada + archivos agregados (`e475508`). Verificado en el clone actual: `frontend/lib/` completo.
**Lección.** Los footguns de repo son invisibles hasta que alguien clona desde cero; el "funciona en mi máquina" del control de versiones. Probar clones limpios periódicamente.
