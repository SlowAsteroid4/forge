---
type: adr
estado: vigente
fecha: 2026-06
tags: [adr, analitica, filtros]
---
# ADR-012 — Apartados derivados dinámicamente con red de seguridad

**Contexto.** Los apartados ([YAPI]/[YPAPP]/[YPNX]/[CAY]/[PLD]) cambian con el negocio; WP-17b solo exponía 3.
**Problema.** Lista hardcodeada = mantenimiento eterno; derivación ciega = un typo `[YPAP]` crea un apartado fantasma silencioso.
**Alternativas.** (a) Lista fija; (b) derivación pura; (c) derivación + validación.
**Decisión.** (c), del PM: derivar del prefijo de épica lo que exista en datos, con `KNOWN_APARTADOS` solo para ordenar conocidos primero y señalar prefijos sospechosos; **"Sin apartado" de primera clase** (es el trabajo de los Version Containers, 36.4% — no se esconde). Filtro global a todas las secciones de Analítica (WP-21, `e5e5d47`).
**Consecuencias.** Un apartado nuevo aparece solo; los typos no se ocultan ni se normalizan en silencio.
**Tradeoffs.** La constante KNOWN_APARTADOS requiere actualización ocasional — costo mínimo y explícito.
