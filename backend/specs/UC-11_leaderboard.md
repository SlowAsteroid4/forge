# UC-11 — Ver leaderboard global y mi posición en mi liga

**Tipo:** Forge Arena / Vista competitiva
**Audiencia:** Player
**Prioridad:** P0 — Núcleo de la gamificación
**Sprint objetivo:** Día 5 del MVP

---

## Historia de usuario

Como **Player**, quiero ver el leaderboard global del sprint y mi posición en mi liga (por área), para entender dónde estoy parado, qué me separa del siguiente y qué tan competida está la temporada.

---

## Contexto

El leaderboard es la cara visible de la competencia. JPDS v2.0 sección 4.1 define 5 categorías que conviven: Backend, Frontend, Database, Quality, MVP del sprint. Cada liga tiene su propio ranking porque comparar BE con FE no tiene sentido — son trabajos distintos con curvas distintas.

Estéticamente debe sentirse a un menú de high scores de un arcade: claro, jerárquico, con personalidad.

---

## Criterios de aceptación

**AC-11.1** Existe vista `/arena/leaderboards` accesible desde side nav de Arena.

**AC-11.2** Header con tabs para cambiar entre vistas:
- **Throne** (vista global, top 3 de todas las ligas).
- **My League** (la liga del player actual, default si no es PM).
- **All Leagues** (vista completa de las 5 ligas).
- **History** (sprints pasados).

**AC-11.3** Vista "Throne":
- Top 3 global del sprint actual (no por liga, mezcla todos).
- 3 cards grandes con podio visual (1° más alto, 2° y 3° flanqueando).
- Cada card: avatar, nombre, clase, SP totales, área (badge).
- Decoración estilo trono/altar.

**AC-11.4** Vista "My League":
- Liga determinada automáticamente por el área del player logueado.
- Tabla con todos los players de esa liga, ordenados por SP del sprint.
- Columnas: Posición, Avatar+Nombre, Clase, SP, CP, QA first-pass %, Trend (↑↓).
- La fila del player actual está destacada visualmente.
- Indicador "X SP detrás del #1" / "Y SP de ventaja sobre el #N+1".

**AC-11.5** Vista "All Leagues":
- 5 secciones colapsables, una por liga (BE, FE, Design, DB, QA).
- Cada sección con su mini-leaderboard (top 5 + el actual si no está en top 5).
- Las ligas unipersonales (DB con Daniela, QA con Edgar) muestran su métrica vs benchmark histórico (no vs otros players).

**AC-11.6** Vista "History":
- Selector de periodo: sprint anterior, mensual (mes pasado), trimestral.
- Para cada periodo, muestra los ganadores top 3 de cada categoría.
- Reconocimientos visuales: 🥇 🥈 🥉 con MVP destacado.
- Click en un ganador lleva a su perfil.

**AC-11.7** Filtros adicionales:
- Por proyecto (UC-03 estilo, pero opcional). Si se filtra, muestra solo SP generado en sub-tasks de ese proyecto.
- Por sprint (default: actual).

**AC-11.8** Cada card de player en cualquier vista permite click para ir a su perfil público (sin datos privados).

**AC-11.9** Indicadores temporales:
- "Sprint termina en X días" siempre visible.
- "Última actualización: hace Y minutos" (refleja último sync).

**AC-11.10** Estética y motion:
- Estética arcade pixel-art consistente con perfil (UC-10).
- Animación al cambiar de posición entre refreshes (slide up/down).
- Brillo dorado en el #1, plata en #2, bronce en #3.
- El propio player tiene resaltado distintivo en su fila.

**AC-11.11** Empty states:
- Si no hay actividad medible en el sprint: "Aún no hay datos del sprint. Vuelve más tarde."
- Si una liga tiene un solo player: "Liga solitaria — competición contra tu propio histórico."

**AC-11.12** El leaderboard no expone datos privados:
- No muestra costos.
- No muestra penalizaciones específicas de otros (solo SP final).
- No muestra apelaciones de otros.

---

## Entidades involucradas

- `leaderboard_snapshots` — caché del leaderboard
- `players` — datos visuales
- `classes`, `avatars` — visualización
- `subtasks` — recálculo en vivo si la caché está desactualizada
- `sprints` — sprint actual y selección histórica

---

## Reglas de negocio

- **Ligas:** la liga del player se determina por `players.area`. Solo BE, FE, Design, DB, QA están en leaderboards. PO/PM están fuera.
- **Daniela y Edgar (ligas unipersonales):** sus métricas se publican pero su ranking no es comparable horizontalmente. Compiten contra sus benchmarks históricos (mes anterior, trimestre anterior).
- **Ordenamiento principal:** SP totales del sprint. Empate desempata por SP/hora.
- **Ranking se calcula con el último `sp_final` persistido.** No con cálculo en vivo desde Jira (modelo local).
- **Snapshots se regeneran** al cerrar sprint, al aplicar/revertir penalización, al publicar nueva engine_version.

---

## Out of scope para MVP

- Comentarios o reacciones en el leaderboard (likes, gifs, etc.).
- Apuestas / pronósticos sobre el ganador.
- Streaks (rachas históricas de top 3).
- Filtro por clase RPG (curiosidad cosmética).
- Notificaciones cuando alguien te rebasa.

---

## Dependencias

- **UC-09** (Login) — necesita sesión.
- **UC-01** (Sync Jira) — datos de origen.
- **Motor de SP** — `sp_final` calculado en sub-tasks.
- **UC-05** (MVP del sprint) — para destacar MVP en History.

---

## Definición de hecho (DoD)

- [ ] Endpoint GET `/api/arena/leaderboard?view=throne|my_league|all|history&sprint_id=X` implementado.
- [ ] Vista `/arena/leaderboards` con 4 tabs funcionales.
- [ ] Vista Throne con podio visual.
- [ ] Vista My League destaca al player actual.
- [ ] Vista All Leagues con secciones colapsables.
- [ ] Vista History con selector de periodo y top 3.
- [ ] Estética arcade consistente con UC-10.
- [ ] Filtro opcional por proyecto.
- [ ] Empty states implementados.
- [ ] Animaciones de cambio de posición.
- [ ] Performance: leaderboard carga en <1 segundo con datos reales.
