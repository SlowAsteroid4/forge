# UC-12 — Ver detalle de por qué mi SP es lo que es

**Tipo:** Forge Arena / Transparencia y feedback
**Audiencia:** Player
**Prioridad:** P0 — Principio fundamental del manifiesto (transparencia)
**Sprint objetivo:** Día 5 del MVP

---

## Historia de usuario

Como **Player**, quiero ver el detalle completo de cómo se calculó mi SP en cada sub-task — cada multiplicador, cada penalización, cada bono — para entender el sistema, validar que es justo y saber qué hacer para mejorar.

---

## Contexto

El manifiesto de Forge (sección 4 del PVD, principio 6) dice: **"El sistema es transparente o no funciona."** Sin la capacidad del player de auditar su propio score, el sistema pierde legitimidad y deja de motivar.

Este caso de uso materializa ese principio. No es decorativo: es la diferencia entre un sistema que el equipo respeta y uno que sospecha.

---

## Criterios de aceptación

**AC-12.1** Existe vista `/arena/me/feedback` accesible desde el perfil del player ("Ver detalle de mis SP") y desde cualquier sub-task de su quest log.

**AC-12.2** Selector de sprint (default: actual). Permite ver sprints históricos en read-only.

**AC-12.3** Tabla maestra "Mis sub-tasks del sprint":
- Columnas: Key, Summary, Status, CP, M_calidad, M_eficiencia, M_dificultad, M_lider, M_cooperacion, Bonos, Penalizaciones, **SP final**.
- Cada multiplicador como número decimal (`1.20`, `0.85`).
- SP final destacado.
- Ordenable por cualquier columna.

**AC-12.4** Click en una sub-task abre vista de detalle expandida:
- **Header:** Sub-task key, summary, area, status, link a Jira.
- **CP:** valor + cómo se obtuvo (talla X → CP Y aprobado por Z el día W).
- **Tiempos:** desglose de adj_ct_biz_hours, qa_biz_hours, blocked_biz_hours, dev_resp_biz_hours.
- **Multiplicadores:** sección por cada uno:
  - **M_calidad**: valor + razón ("Pasó QA en primer intento" → 1.20).
  - **M_eficiencia**: valor + ratio (adj_ct_biz real / esperado = 0.85 → 1.15).
  - **M_dificultad**: valor + tipo de trabajo (ej. "Integración a tercero documentado" → 1.00).
  - **M_lider**: valor + cuántos PRs aprobados / mentorías (en MVP solo manual).
  - **M_cooperacion**: valor + sub-task desbloqueada si aplica.
- **Bonos flat (SP planos):** lista de buffs aplicados (B14 Documenter +0.5, B16 Curator +1, etc.).
- **Penalizaciones:** lista de debuffs aplicados con SP delta y razón.
- **Fórmula final visible:** `SP = CP × M_calidad × M_eficiencia × M_dificultad × M_lider × M_cooperacion + bonos − penalizaciones = SP_final`.

**AC-12.5** Sección "Resumen del sprint":
- SP totales del sprint.
- SP totales por categoría: ganados por sub-tasks, ajustes manuales (MVP, bonos cualitativos), penalizaciones.
- Tendencia respecto al sprint anterior (+/- delta).

**AC-12.6** Sección "Cómo subir mi SP":
- Insights automáticos basados en patrones del player:
  - Si M_calidad promedio es bajo: "Tu M_calidad promedio es 0.95. Mejorar QA first-pass te subiría ~15% el SP."
  - Si tiene penalizaciones recurrentes: "Has tenido 3 debuffs por X razón este sprint. Revisa esta práctica."
  - Si está cerca de un achievement: "Te faltan 2 sub-tasks para Code Surgeon (ACH06): +20 SP."
- Insights cosméticos pero útiles. En MVP pueden ser texto estático según condiciones; con IA en v0.4.

**AC-12.7** CTA "Apelar penalización":
- Visible solo en penalizaciones del sprint actual.
- Botón abre modal con campo de texto "Razón de apelación".
- Al enviar: marca el `sp_adjustments.is_appealed = 1` (sin resolver todavía).
- En MVP local, la apelación se discute en weekly y el PM resuelve en UC-06.
- Confirmación en UI: "Tu apelación se discutirá en la próxima weekly."

**AC-12.8** Export:
- Botón "Descargar mi reporte de SP del sprint" → PDF (post-MVP) o CSV simple en MVP.

**AC-12.9** Privacidad:
- El player solo ve SU detalle. No el de otros.
- El admin/PM puede ver el feedback de cualquier player desde Ops para discutirlo en 1:1.

**AC-12.10** Tooltips educativos:
- Cada multiplicador tiene un tooltip "?" que explica qué es y cómo se calcula.
- Link al Codex (UC futuro / `/arena/codex/powers`) para profundizar.

**AC-12.11** Empty states:
- Si el player no tiene sub-tasks Done en el sprint: "Aún no has cerrado sub-tasks en este sprint. Tu SP es 0."
- Si el sprint es histórico y no tenía datos: mensaje claro.

---

## Entidades involucradas

- `subtasks` — todos los multiplicadores y SP
- `sp_adjustments` — bonos y penalizaciones
- `buffs`, `debuffs`, `achievements` — catálogos para descripciones narrativas
- `engine_versions` — para mostrar con qué versión se calculó

---

## Reglas de negocio

- **Transparencia total**: el player ve TODO sobre su propio SP. Sin escondites.
- **Apelación visible**: si el player apela, queda marcado pero no resuelto. Solo el PM resuelve.
- **Versión del motor visible**: cada sub-task muestra con qué `engine_version` se calculó. Si cambió la versión a mitad de sprint (no debería, pero por si acaso), el player ve la diferencia.
- **Datos del sprint actual son fluidos**: pueden cambiar si se aplican penalizaciones o se cierran nuevas sub-tasks. Los históricos son inmutables.

---

## Out of scope para MVP

- Flujo digital completo de apelación con conversación (en MVP es presencial en weekly).
- Comparativa con el promedio de la liga ("tu M_calidad vs promedio del área").
- Simulador "what-if" (si M_calidad fuera X, mi SP sería Y).
- Predicción de SP esperado del sprint actual basado en velocity.
- Sugerencias generadas por IA del estilo "deberías hacer X" (post-MVP v0.4).

---

## Dependencias

- **UC-10** (Mi perfil) — vista hermana.
- **UC-06** (Aplicar penalización) — para que el flujo de apelación exista del lado admin.
- **Motor de SP** — datos calculados.

---

## Definición de hecho (DoD)

- [ ] Endpoint GET `/api/arena/me/sp-breakdown?sprint_id=X` implementado.
- [ ] Endpoint POST `/api/arena/me/appeal/{adjustment_id}` implementado.
- [ ] Vista `/arena/me/feedback` funcional.
- [ ] Tabla maestra con todas las sub-tasks y multiplicadores.
- [ ] Detalle expandido por sub-task con fórmula visible.
- [ ] Sección "Resumen del sprint" con totales y tendencia.
- [ ] Sección "Cómo subir mi SP" con insights estáticos (3-5 reglas).
- [ ] Modal de apelación funcional.
- [ ] Tooltips educativos en multiplicadores.
- [ ] Empty states implementados.
- [ ] Export CSV funcional.
