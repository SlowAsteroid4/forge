---
type: master-state
proyecto: Forge
tags: [estado-maestro, arranque, contexto]
ultima_actualizacion: 2026-06-15
actualiza: solo el chat maestro (arquitecto)
---

# ESTADO MAESTRO — Forge

> **LÉEME PRIMERO.** Este es el documento de arranque de TODOS los chats de Forge. Si eres un chat
> nuevo (maestro, herramientas, negocio, o vas a generar un prompt para Claude Code), lee este
> archivo completo antes de hacer nada. Luego lee, según tu rol, los enlaces de la sección 11.
>
> **Regla de oro:** el conocimiento vive en el vault (`vault/`), no en los chats. Los chats son
> trabajadores temporales que leen de aquí y escriben de vuelta. SOLO el chat maestro edita este
> archivo, al final de cada sesión de trabajo.

---

## 0. Identidad del proyecto en una frase

**Forge** = plataforma interna del equipo Yapsi (Guadalajara) que convierte los datos de Jira en
métricas confiables (**Forge Ops**, consola del PM) y en una capa de gamificación RPG para los
devs (**Forge Arena**). Nació porque el PM no confiaba en sus métricas: Jira decía *qué* pasaba,
pero los números derivados (WIP, QA, tiempos, velocity) **mentían**. La consigna de todo el
proyecto es **"el dato primero"**: ningún número se muestra sin haberse validado contra la realidad.

---

## 1. Dónde vamos (estado a 2026-06-15)

### Forge Ops — ✅ COMPLETO
Dashboard de ciclo, Aprobación de CP, Cierre de ciclo + MVP semanal, MVP del Mes, Penalizaciones +
apelaciones, Forecast (3 escenarios), Pulso operativo, Analítica (Quality, barras canónicas,
cycle/lead time, métricas por dev), Players admin, Costos por área. Todo sobre datos verificados
con cruce manual.

### Forge Arena — 🟡 SOLO LOGIN
- ✅ Login (WP-18) — selección de identidad sin password. **PERO el Handoff nunca se evaluó contra
  el DoD** (se ejecutó fuera del loop del chat maestro). Pendiente de revisión.
- ⬜ Falta TODO lo demás: onboarding (clase/avatar, UC-15), perfil (UC-10), leaderboard + detalle
  SP (UC-11/12), achievements + tienda (UC-13/14).

### Fase actual: AUDITORÍA antes de construir Arena
Antes de construir la mitad Arena, se va a correr una **auditoría de coherencia arquitectónica**
con Opus 4.8 en Claude Code (un "oficial externo" fresco que verifica que los cimientos están
sólidos). El prompt de esa auditoría ya está diseñado. **Próximo paso concreto:** correr esa
auditoría, traer el informe al chat maestro, separar hallazgos reales de falsos positivos, y
convertir lo real en work packages. DESPUÉS de eso, arrancar Arena.

---

## 2. Pendientes vivos (lo que NO se puede olvidar)

| # | Pendiente | Por qué importa | Prioridad |
|---|---|---|---|
| 1 | **Validar que Alondra (DB) da WIP=2 / Review=4** en el código actual | WP-20 quedó PARTIAL: el Handoff reportó 1/3 porque no contaba `In Code`. El código ya tiene `_WIP_STATES={In Progress, In Code}` pero la validación contra Jira y el test golden 2/4 nunca se cerraron. El tablero de saturación podría seguir mintiendo. | ALTA |
| 2 | **Evaluar el Handoff de WP-18 (login Arena)** contra su DoD | Arena va a construirse encima; si el login está flojo, todo lo hereda. Revisar: estética arcade, rechazo de inactivos, persistencia de sesión, banner de "ver como". | ALTA |
| 3 | **Auditar el commit `6a2268a`** ("excepción cierre primer mes") | Pudo haber tocado el gate de ≥4 ciclos del MVP mensual (ADR-011). Posible regresión silenciosa. | ALTA |
| 4 | **Versionar specs + Manifiesto en el repo** | YA HECHO en PR #1 (`backend/specs/`, 19 archivos). Verificar que sigan ahí tras merges. | Cerrado* |
| 5 | Capturar costos reales de los 14 players (hoy 6/14) | UC-08 (Costos) solo proyecta lo capturado. | MEDIA |
| 6 | Auth real de Ops (destrabar `admin_id=1`, conectar `require_cost_access()`) | Deuda desde WP-02a. Se cobra al construir Arena. | MEDIA |
| 7 | Trazabilidad WP→commit rota en WP-11/12/13/19/20 | Código presente, commits sin nombre propio. | MEDIA |
| 8 | Reconstruir el "puente" negocio↔código en Graphify | El grafo casi no conecta vault con código (ver sección 9). | MEDIA |

\* El #4 figura para que ningún chat vuelva a asumir que los specs no están versionados.

---

## 3. Cómo trabajamos (el protocolo — esto define la cultura del proyecto)

### El loop maestro
1 sesión de Claude Code = **1 Work Package (WP)**. Los roles:
- **Chat maestro (arquitecto):** conoce la historia y el dominio. Diseña el prompt del WP con las
  decisiones YA cerradas. Evalúa el Handoff Report. Responde APROBADO / AJUSTE / BLOQUEADO.
  Actualiza este ESTADO_MAESTRO al terminar.
- **Claude Code (ejecutor):** recibe el prompt, ejecuta, entrega un Handoff Report con **salidas
  reales de BD** (no "los tests pasan" — los números reales).
- **El humano (PM):** pega prompts y Handoffs entre chats, y aporta el conocimiento de dominio que
  solo él tiene (cruza números contra Jira).

### Reglas duras (no negociables)
1. **PASO 0 de auditoría OBLIGATORIO** antes de construir: leer el código real + correr queries de
   diagnóstico. Las veces que se saltó, salió un bug (ver INC-009).
2. **Backup de la BD + branch + checkpoint commit** antes de cualquier WP que escriba datos.
3. **Validación con salidas reales + cruce manual** de los números clave. Sumar a mano y comparar
   contra el servicio. Esto cazó bugs que ningún test sintético vio.
4. **Los casos golden del PM van como criterio de aceptación LITERAL** en el prompt (ej. "Alondra
   debe dar WIP=2"). Si el resultado no los cumple, es AJUSTE.
5. **El dato primero:** nunca inventar números. Admitir incertidumbre ("preliminar", "sin
   comparativa", "—") es preferible a un número bonito y falso.
6. **No creerle al log; contar.** "150 actualizadas" no significa nada; `COUNT(*)` antes/después sí.
7. **Migraciones siempre aditivas** (Alembic), idempotentes (SQLite no tiene DDL transaccional).
8. **Traducción de specs:** los UC fueron escritos pre-migración Sprint→Ciclo. Donde digan
   "sprint"/"semana", se usa "ciclo". Esto va recordado en cada prompt.

### Plantilla mínima de un prompt de WP
- Contexto + qué WP es + "ya hice backup".
- **DECISIONES DEL CHAT MAESTRO (NO las cambies):** lista de decisiones cerradas.
- **PASO 0 — auditoría:** qué leer, qué queries correr, qué reportar antes de construir.
- Pasos de implementación.
- **VALIDACIÓN:** salidas reales que debe pegar (demos, cruces, inmutabilidad, no-escritura).
- **Handoff Report** con estructura fija + Autoevaluación vs DoD (checklist).

---

## 4. Arquitectura de chats (cómo no volver a contaminar un chat)

Todos los chats leen y escriben al **mismo vault** (el bus de contexto). NO se hablan entre sí
directamente; el contexto viaja en artefactos (prompts y Handoffs) y en este documento.

```
                  VAULT (en el repo) — única fuente de verdad
                  ESTADO_MAESTRO.md  ← todos leen al empezar
                          │            solo el maestro escribe al terminar
        ┌─────────┬───────┴───────┬─────────────┐
   CHAT MAESTRO   CLAUDE CODE   CHAT HERRAMIENTAS  CHAT NEGOCIO
   (arquitectura, (ejecuta WPs)  (Obsidian,        (dominio, UCs,
    diseña WPs,                   Graphify, dudas   reglas de negocio)
    aprueba)                      de tooling)
```

- **Solo el chat maestro edita el ESTADO_MAESTRO** (evita conflictos).
- Cada chat arranca leyendo este archivo, así nunca está más de una sesión atrás.
- Cuándo abrir chat nuevo: cuando el actual se sienta lento o cambies de tipo de tarea.
- El prompt de arranque de un chat maestro nuevo está en la sección 11.

---

## 5. Dominio canónico (las reglas que rigen TODO)

### Economía CP / SP
- **CP (Complexity Points):** complejidad por talla — XS=1, S=2, M=3, L=5, XL=8 (de Jira
  `customfield_10851`). El PM los aprueba (UC-04). **Una vez aprobado, el CP es INMUTABLE**
  (`CPImmutableError`). Invariante en cada WP: conteo de `cp_approved_at` igual antes/después.
- **SP (Score Points):** la moneda de Arena. **SP = CP × multiplicadores + bonos − penalizaciones.**
  Bonos: B17 (+5, MVP semanal), B17M (+10, MVP del Mes). Penalizaciones: catálogo D01–D16.
- **Regla de oro append-only:** `sp_adjustments` NUNCA se UPDATEa para cambiar SP. Revertir =
  INSERT de signo opuesto. Reducción parcial = INSERT por la diferencia. La metadata de apelación
  SÍ se actualiza (es estado, no valor). Piso 0: nunca SP negativo.

### Ritmo Operativo (reemplazó "Sprint")
- **Pulso:** el AHORA, live, read-only, no compite.
- **Ciclo:** semana Lun–Vie, cierre ritual el viernes. Unidad de competencia. Solo 1 activo.
- **Ventana Móvil:** últimos **4 ciclos cerrados** (no semanas calendario). Base de velocity/forecast.

### Estados: crudos vs canónicos
- **Crudos:** 37 strings reales en el changelog (incluye variantes en español: `En progreso`,
  `Cerrado`, etc.). 12 activos hoy.
- **Canónicos:** 9 categorías del Manifiesto (Backlog, Ready, In Progress, In Review, In QA,
  Waiting, Blocked, Done, Cancelled). Mapeo único en `CANONICAL_STATUS_MAP`.
- Mapeos que confunden: "Code Review" NO existe (es `In Review`); `In Code` = trabajo activo SOLO
  de DB; `Ready For QA`→Ready y `Testing`→In Review (para AGRUPAR), pero su TIEMPO se atribuye
  distinto (ver abajo).

### WIP (definición estricta del PM)
- **WIP = `In Progress` + `In Code`**, nada más. `In Code` es el "activo" propio de Database.
- NO son WIP: In Review, Ready for QA, In QA, Waiting, Ready, Backlog, Blocked, Done.
- **Semáforo** solo sobre WIP, contra límite de área: BE=3, FE=3, DESIGN=4, DB=5.
- Caso golden: **Alondra (DB) = WIP 2** (1 In Progress + 1 In Code) + 4 In Review aparte.

### Atribución de tiempo (WP-07h — LÍNEA ROJA, intocable)
- `dev_resp` (incluye `Ready for QA` = cola/cuello del dev) ≠ `qa_biz_hours` (`In QA`/`Testing` =
  tiempo de Edgar/QA). `dev_resp` EXCLUYE In QA.
- **Categoría canónica (cómo se agrupa/muestra) ≠ Atribución de tiempo (a quién se carga).** Son
  capas separadas A PROPÓSITO. Adoptar canónicos para mostrar NO cambia la atribución validada.
- **Cycle time** = primer In Progress canónico → Done (histories ordenadas por timestamp).
  **Lead time** = `lt_biz_hours` (única fuente con la creación real; `created_at` es fecha de
  import, no de creación en Jira). Todo en horas hábiles MX (America/Mexico_City).

### Contenedores y apartados
- **`epic_kind`:** normal (46, va al forecast) / version_container (2: YAP-66 [2.1], YAP-130 [3.0],
  fuera del forecast) / coordination (0 épicas — los terceros NO son épicas).
- **Terceros (Coordinación):** 8 subtasks flotantes sin padre, siempre vivas (STP, CNBV, CONDUSEF,
  Nubarium, Cierto, Felix Pago, MoSi, Transnetwork). No contaminan el forecast.
- **Apartados (sub-divisiones de YAP):** [YAPI], [YPAPP], [YPNX], [CAY], [PLD] + "Sin apartado".
  Todos son producto propio (normal). Derivados dinámicamente del prefijo de la épica.

### Identidades (clave para Arena)
- **Jesús** = `role='PO'` (gobierno) Y `area=DESIGN` (su diseño SÍ produce CP/SP/leaderboard).
- **"Equipo de Producto"** (player 14) = cuenta-grupo de Jira que agrega el trabajo de Sasha y Fran
  (que NO tienen cuenta Jira propia). `area=DESIGN`, etiquetado "(equipo agregado)" — **nunca
  compite como individuo**.
- **Diego Candia** es dev BE, NO diseñador (pese al nombre).
- `LEADERBOARD_AREAS = {BE, FE, DESIGN, DB, QA}` — el PO se excluye como área.

### Flujo del equipo
Adán crea épica → la llena → genera historias → refinamiento → **Jesús (PO)** revisa → diseño →
los diseñadores trabajan las subtasks de diseño → Jesús pasa la historia a Ready con su subtask de
diseño en Done → **devs** generan sus subtasks → al empezar una, la historia pasa a In Progress.
(Las subtasks sin assignee son la cola de trabajo disponible del área — legítimas, no son error.)

---

## 6. Las 15 decisiones de arquitectura (ADRs) — resumen

El detalle completo vive en `vault/08_Decisions/`. Resumen para arranque:

1. **ADR-001** Sprint→Ciclo (tabla `cycles`, modelo de Ritmo Operativo).
2. **ADR-002** La talla era correcta; el bug era la ventana JQL −14d → `make sync-full`.
3. **ADR-003** El tiempo se atribuye por estado, no por assignee (el sync reescribe assignee).
4. **ADR-004** Ready for QA = dev; In QA/Testing = Edgar. **LÍNEA ROJA.**
5. **ADR-005** Canónicos para AGRUPAR; WP-07h para ATRIBUIR. Capas separadas.
6. **ADR-006** Lead desde `lt_biz_hours`; cycle recalculado canónico (histories ordenadas).
7. **ADR-007** Jesús = PO + DESIGN; "Equipo de Producto" → DESIGN agregado.
8. **ADR-008** Las clasificaciones de Forge viven en campos que el sync NO pisa.
9. **ADR-009** WIP = In Progress + In Code; semáforo 3/3/4/5. (Validación Alondra pendiente.)
10. **ADR-010** epic_kind; Version Containers fuera del forecast.
11. **ADR-011** Gate estricto ≥4 ciclos para MVP del Mes; demo revertido append-only.
12. **ADR-012** Apartados derivados dinámicamente + KNOWN_APARTADOS como red de seguridad.
13. **ADR-013** Arena: selección de identidad, sin password (modelo local).
14. **ADR-014** El Pulso es read-only (solo "marcar para revisión" escribe).
15. **ADR-015** Forecast on-the-fly, ventana 4 ciclos, 3 fórmulas (opt/real/cons).

---

## 7. Golden Cases (los números que NUNCA deben romperse)

- **YAP-721:** cycle canónico = 107.44h; dev_resp = 79.74h; qa_biz_hours = 19.70h; ready_for_qa =
  47.74h; lead = 120.15h. Cualquier WP que toque tiempo debe demostrarlos byte-idénticos.
- **Alondra (DB):** objetivo golden WIP=2/Review=4. ⚠️ Verificado 2026-06-16: **NO reproducible hoy** — no tiene tareas activas (Backlog 1, Done 38, In Review 2) → WIP real = 0; `In Code` no existe en la BD (0 filas en toda la tabla). El código sí incluye `In Code` en `_WIP_STATES` (`pulse_service.py:111`), pero el dato no lo soporta → reformular el golden como test sintético de la lógica (sembrar In Progress+In Code, assert 2).
- **Velocity BE:** W19–W22 = 6+13+18+12 = 49 / 4 = 12.25 exacto.
- **Dev metrics (Juan):** canónico agrega los crudos; suma = 3318.69.
- **Inmutabilidad:** `cp_approved_at` count = **56** (igual antes/después en cada WP). ✅ Verificado 2026-06-16: sigue en 56.

---

## 8. Stack y repo

- **Backend:** FastAPI + SQLAlchemy + Alembic + SQLite (`backend/forge.db`). Tooling: `uv`, `ruff`,
  `mypy` (baseline ~56 errores pre-existentes; los WP exigen 0 errores *nuevos*).
- **Frontend:** Next.js 16 + React 19 + Tailwind (`frontend/`). Server Components `force-dynamic`.
- **Repo:** `github.com/SlowAsteroid4/forge`. Rama por defecto: `feat/wp18-arena-login`.
  ✅ Verificado 2026-06-16: default = `feat/wp18-arena-login`; último commit `4c63c10` "Merge pull request #1 from SlowAsteroid4/docs/knowledge-base" (2026-06-13).
- **13 servicios** en `backend/src/forge/services/` + `engine/` (único que recalcula SP).
- **Comandos clave:** `make sync` (−14d) · `make sync-full` (backfill) · `make recalc --all-cycles`
  · `make seed-epic-kinds` · `make test` · `make typecheck`.
- **Tests:** **504 verdes, 0 fallidos** (`uv run pytest -q`). ✅ Verificado 2026-06-16 (incluye `tests/unit/etl/test_prune.py`, aún sin commitear).
- **Footgun conocido:** la regla `lib/` del `.gitignore` llegó a ignorar `frontend/lib/` (9
  archivos). Ya corregido, pero revisar en clones limpios.

---

## 9. Base de conocimiento (Obsidian + Graphify)

- **Vault:** `vault/` en el repo (54 notas, FASE A). Estructura `00_Home` … `17_References`.
  Es el "por qué" del proyecto. Se edita en Obsidian apuntando al clon del repo, se commitea.
- **Graphify:** CLI (`graphifyy`) que indexa el CÓDIGO en un grafo (`graphify-out/graph.json`,
  gitignored). Es el "cómo". ⚠️ NO captura los `[[wikilinks]]` de Obsidian — su visión del vault
  es ciega; úsalo solo como mapa del código.
- **Puente débil:** vault y código casi no se conectan en el grafo. Para mejorarlo, al escribir
  notas mencionar el nombre real del símbolo/archivo (`pulse_service.py`, `Subtask`,
  `calculate_cp()`) — Graphify enlaza por coincidencia de nombres.
- **Pendiente de Graphify:** correr `graphify . --cluster-only` para generar `GRAPH_REPORT.md` y
  `graph.html` (no se hizo aún).
- **Refresco:** `GRAPHIFY_CLAUDE_CLI_MODEL=haiku graphify . --update --backend claude-cli` tras
  cada WP.

---

## 10. Historial de Work Packages (resumen)

Ops construido en ~21 WPs. El detalle UC→WP→commit vive en
`vault/14_Roadmap/Historial de Work Packages.md`. Hitos:
- **WP-01..06:** migración Sprint→Ciclo, aprobación CP, cierre + MVP semanal, dashboard.
- **WP-07a–j (el "pozo de datos"):** se cerraron 8+ mentiras de datos ANTES de construir Ops
  (qa_first_pass falso, talla desincronizada, tiempo de Edgar mal atribuido, sp_final, etc.).
- **WP-08..17:** Pulso, MVP del Mes, penalizaciones, forecast, players, costos, identidades,
  rediseño de Pulso y Analítica.
- **WP-18..21:** login Arena (sin revisar), epic_kind, WIP estricto (PARTIAL), apartados dinámicos.
- ✅ Verificado 2026-06-16: **no existen commits con esos nombres** (`git log --all --grep` → 0 resultados). La convención del repo es `feat(wpNN)`; WP-11/12/13/19/20 no aparecen — el código está presente pero quedó folded en otros commits sin etiqueta propia. Trazabilidad WP→commit rota, confirmada (sin hashes que reportar).

---

## 11. Arranque por rol (qué leer según quién eres)

### Si eres un CHAT MAESTRO nuevo, pega esto al iniciar:
> Eres el chat maestro (arquitecto) del proyecto Forge. Tu rol: diseñar work packages con prompts
> copiables para Claude Code, evaluar Handoff Reports, y mantener la coherencia del proyecto.
> Antes de responder NADA, lee del repo: este ESTADO_MAESTRO.md, vault/00_Home.md,
> vault/08_Decisions/MOC Decisiones ADR.md, y vault/14_Roadmap/Pendientes y Deuda.md.
> Reglas: 1 sesión Claude Code = 1 WP con PASO 0 obligatorio; decisiones cerradas en el prompt;
> validación con salidas reales + cruce manual; casos golden como criterio literal; el dato
> primero. Confírmame que leíste el estado y dime en qué punto estamos antes de proponer nada.

### Si eres CLAUDE CODE:
Lee el prompt del WP que te paso (es autocontenido, trae las decisiones cerradas). Si necesitas
contexto extra, lee este archivo y el vault. Ejecuta el PASO 0 antes de construir. Entrega Handoff
con salidas reales.

### Si eres el CHAT DE HERRAMIENTAS:
Dudas de Obsidian, Graphify, tooling. Lee secciones 4 y 9. No tocas código ni dominio.

### Si eres el CHAT DE NEGOCIO:
Dominio, UCs, reglas. Lee secciones 5, 6, 7 y los specs en `backend/specs/`. No diseñas WPs (eso
es del maestro).

---

## 12. Bitácora de actualizaciones (el maestro añade una línea por sesión)

| Fecha | Qué cambió | Por quién |
|---|---|---|
| 2026-06-15 | Creación del ESTADO_MAESTRO (FASE A del vault completa, 54 notas). Pendiente: refinar con Claude Code los campos `[VERIFICAR EN CÓDIGO]`. | chat maestro |

---

> **Recordatorio final para el maestro:** al terminar cada sesión, actualiza la sección 1 (dónde
> vamos), la 2 (pendientes), y añade una línea a la bitácora (12). Mantén este archivo por debajo de
> lo que un chat pueda leer cómodo al arrancar — si crece demasiado, mueve detalle al vault y deja
> aquí solo el resumen + el enlace.
