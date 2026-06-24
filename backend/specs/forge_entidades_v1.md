# FORGE — Modelo de Entidades v1.0
*Schema SQLite para MVP Local. Yapsi / Mayo 2026.*

---

## Convenciones generales

- Motor: **SQLite** (un archivo `forge.db` local).
- PKs: `INTEGER PRIMARY KEY AUTOINCREMENT` salvo entidades con código natural estable (catálogos seed).
- Timestamps: `TEXT ISO 8601` (`YYYY-MM-DD HH:MM:SS`). SQLite no tiene tipo nativo `TIMESTAMP`, pero soporta funciones `datetime()` sobre TEXT.
- Booleans: `INTEGER` 0/1.
- Decimales (SP, multiplicadores, costos): `REAL`.
- JSON (changelogs, configs, metadata): `TEXT` con validación a nivel app.
- FK: `ON DELETE` definido explícitamente por relación (CASCADE para hijos, RESTRICT para refs maestras).
- Auditoría: toda tabla mutable tiene `created_at` y `updated_at`.
- Naming: snake_case, tablas en plural, columnas en singular.

---

## Mapa de entidades (16 tablas)

**Identidad y catálogos estáticos** (seed inicial, baja mutación):
1. `players` — personas del equipo
2. `classes` — clases RPG (catálogo)
3. `avatars` — sprites predefinidos (catálogo)
4. `projects` — Dungeons (catálogo)
5. `buffs` — multiplicadores positivos (catálogo)
6. `debuffs` — penalizaciones (catálogo)
7. `achievements` — logros desbloqueables (catálogo)
8. `shop_items` — items de tienda (catálogo)

**Trabajo (sincronizado desde Jira)**:
9. `epics` — épicas con rollup CP
10. `stories` — historias con rollup CP
11. `subtasks` — unidad de ejecución, dueña del CP/SP

**Operación (mutación constante)**:
12. `sprints` — periodos de 2 semanas
13. `sp_adjustments` — bonos/penalizaciones aplicadas
14. `achievement_unlocks` — relación player ↔ achievement
15. `redemptions` — canjes de tienda
16. `engine_versions` — config del motor versionado

**Apoyo**:
17. `audit_log` — registro de toda acción administrativa (transversal)
18. `leaderboard_snapshots` — caché regenerable

(Son 18 contando apoyo; las 16 son el modelo de negocio.)

---

## 1. `players`

Identidad del miembro del equipo. Una fila por persona.

```sql
CREATE TABLE players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jira_account_id TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    email TEXT UNIQUE,
    area TEXT NOT NULL CHECK(area IN ('BE','FE','DESIGN','DB','QA','PO','PM')),
    employment_type TEXT NOT NULL CHECK(employment_type IN ('internal','external')),
    is_lead INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    
    -- Identidad gamificada
    class_code TEXT REFERENCES classes(code) ON DELETE RESTRICT,
    avatar_code TEXT REFERENCES avatars(code) ON DELETE RESTRICT,
    
    -- Costos (privados, solo PM/Owner ven)
    monthly_salary REAL,
    hourly_rate REAL,
    monthly_hours_cap INTEGER,
    
    -- Fechas
    joined_at TEXT,
    class_last_changed_at TEXT,
    
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_players_area ON players(area);
CREATE INDEX idx_players_active ON players(is_active);
```

**Notas:**
- `area` cubre todas las disciplinas + roles no-player (PO/PM). Solo BE/FE/DESIGN/DB/QA participan en leaderboards.
- `is_lead` se usa para activar M_lider (Hector, Daniel Rios).
- Cambio de clase: 1 vez por trimestre, validado a nivel app contra `class_last_changed_at`.
- Costos son nullable porque al inicio no tienes los datos.

---

## 2. `classes`

Catálogo de clases RPG. Seed del catálogos doc.

```sql
CREATE TABLE classes (
    code TEXT PRIMARY KEY,                  -- 'C01', 'C02'...
    name TEXT NOT NULL,                     -- 'Archmage'
    archetype TEXT NOT NULL,                -- 'Sabio, dominio técnico'
    flavor_description TEXT,                -- pasiva cosmética narrativa
    sprite_url TEXT,                        -- ruta al asset visual
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## 3. `avatars`

Sprites predefinidos.

```sql
CREATE TABLE avatars (
    code TEXT PRIMARY KEY,                  -- 'A01'...
    name TEXT NOT NULL,
    style TEXT,                             -- 'Armadura plata, espada'
    sprite_url TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);
```

---

## 4. `projects`

Dungeons. Identificados por prefijo en summary de épica padre.

```sql
CREATE TABLE projects (
    code TEXT PRIMARY KEY,                  -- 'P01'
    jira_prefix TEXT UNIQUE NOT NULL,       -- '[YAPAPP]'
    internal_name TEXT NOT NULL,            -- 'Yapsi App'
    arena_name TEXT NOT NULL,               -- 'The Citadel'
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Nota:** matching de épica a proyecto es por `substring` o `regex` sobre `epic.summary` buscando el `jira_prefix`. Lógica vive en `etl/project_matcher.py`.

---

## 5. `buffs`

Multiplicadores positivos.

```sql
CREATE TABLE buffs (
    code TEXT PRIMARY KEY,                  -- 'B01'
    narrative_name TEXT NOT NULL,           -- 'First Strike'
    multiplier_type TEXT NOT NULL,          -- 'M_calidad','M_eficiencia','M_dificultad','M_lider','M_cooperacion','SP_flat_bonus'
    trigger_description TEXT NOT NULL,
    value REAL NOT NULL,                    -- 1.20 para multiplicador, 0.5 para flat
    mechanic TEXT NOT NULL CHECK(mechanic IN ('multiply','add','add_to_multiplier')),
    applies_to_area TEXT,                   -- NULL = todas; 'BE','FE','DESIGN','DB','QA'
    icon_code TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);
```

---

## 6. `debuffs`

Penalizaciones. Mismo esquema conceptual que buffs.

```sql
CREATE TABLE debuffs (
    code TEXT PRIMARY KEY,                  -- 'D01'
    narrative_name TEXT NOT NULL,
    trigger_description TEXT NOT NULL,
    penalty_type TEXT NOT NULL,             -- 'multiplier_cap','sp_pct_reduction','sp_flat','wip_lock'
    value REAL NOT NULL,                    -- ej. 0.85 para mult, -50 para %, -15 para flat
    applies_to_area TEXT,
    icon_code TEXT,
    is_appealable INTEGER NOT NULL DEFAULT 1,  -- según OQ-12, todas apelables en weekly
    is_active INTEGER NOT NULL DEFAULT 1
);
```

---

## 7. `achievements`

Logros desbloqueables.

```sql
CREATE TABLE achievements (
    code TEXT PRIMARY KEY,                  -- 'ACH01'
    name TEXT NOT NULL,                     -- 'First Blood'
    description TEXT NOT NULL,
    rarity TEXT NOT NULL CHECK(rarity IN ('common','rare','epic','legendary','mythic')),
    sp_bonus INTEGER NOT NULL DEFAULT 0,
    unlock_condition_code TEXT NOT NULL,    -- string canónico, ej. 'FIRST_SUBTASK_DONE'
    unlock_condition_params TEXT,           -- JSON con parámetros (umbrales, ventanas)
    icon_code TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);
```

**Nota:** la lógica de evaluación de cada `unlock_condition_code` vive en `engine/achievement_engine.py` como un dispatcher. Cada código mapea a una función Python. Esto evita meter lógica en strings o SQL.

---

## 8. `shop_items`

Items canjeables.

```sql
CREATE TABLE shop_items (
    code TEXT PRIMARY KEY,                  -- 'S01'
    name TEXT NOT NULL,                     -- 'Día de home office extra'
    category TEXT NOT NULL CHECK(category IN ('perk_time','perk_communal','perk_consumption','perk_physical','perk_large')),
    price_sp INTEGER NOT NULL,
    operational_notes TEXT,                 -- 'Usar en el sprint siguiente'
    stock_limit INTEGER,                    -- NULL = ilimitado
    min_rank_required TEXT,                 -- NULL = sin restricción
    icon_code TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);
```

---

## 9. `epics`

Épicas de Jira con rollup CP.

```sql
CREATE TABLE epics (
    jira_key TEXT PRIMARY KEY,
    project_code TEXT REFERENCES projects(code) ON DELETE RESTRICT,
    summary TEXT NOT NULL,
    status TEXT NOT NULL,
    cp_total REAL DEFAULT 0,                -- suma de cp_total de historias hijas
    created_at TEXT,
    last_synced_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_calculated_at TEXT
);

CREATE INDEX idx_epics_project ON epics(project_code);
CREATE INDEX idx_epics_status ON epics(status);
```

---

## 10. `stories`

Historias con CP agregado.

```sql
CREATE TABLE stories (
    jira_key TEXT PRIMARY KEY,
    parent_epic_key TEXT REFERENCES epics(jira_key) ON DELETE SET NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL,
    
    -- Rollup CP
    cp_raw REAL DEFAULT 0,                  -- suma directa de subtasks
    cp_total REAL DEFAULT 0,                -- cp_raw × overhead × dep_factor
    n_areas INTEGER DEFAULT 0,
    has_dependency_chain INTEGER DEFAULT 0,
    overhead_factor REAL DEFAULT 1.0,
    dependency_factor REAL DEFAULT 1.0,
    
    created_at TEXT,
    last_synced_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_calculated_at TEXT
);

CREATE INDEX idx_stories_epic ON stories(parent_epic_key);
```

---

## 11. `subtasks`

Núcleo del modelo. Dueña de CP y SP.

```sql
CREATE TABLE subtasks (
    jira_key TEXT PRIMARY KEY,
    parent_story_key TEXT REFERENCES stories(jira_key) ON DELETE SET NULL,
    parent_epic_key TEXT,                   -- denormalizado para queries rápidas
    project_code TEXT REFERENCES projects(code) ON DELETE RESTRICT,
    
    issue_type TEXT NOT NULL,               -- 'Backend Sub-task', 'Frontend Sub-task'...
    area TEXT NOT NULL CHECK(area IN ('BE','FE','DESIGN','DB','QA','INFRA','TASK','BUGFIX','DISCOVERY')),
    summary TEXT NOT NULL,
    status TEXT NOT NULL,
    assignee_player_id INTEGER REFERENCES players(id) ON DELETE SET NULL,
    sprint_id INTEGER REFERENCES sprints(id) ON DELETE SET NULL,
    
    -- Complexity Points (estática)
    complexity_size TEXT CHECK(complexity_size IN ('XS','S','M','L','XL','XXL')),
    cp INTEGER,
    cp_proposed_by INTEGER REFERENCES players(id),
    cp_proposed_at TEXT,
    cp_approved_by INTEGER REFERENCES players(id),
    cp_approved_at TEXT,
    cp_approval_required INTEGER DEFAULT 0,  -- 1 si L o XL
    
    -- Tiempos calculados (horas hábiles)
    created_at TEXT,
    done_at TEXT,
    lt_biz_hours REAL,                      -- Lead Time
    ct_biz_hours REAL,                      -- Cycle Time
    adj_ct_biz_hours REAL,                  -- Cycle ajustado (sin blocked/waiting)
    dev_resp_biz_hours REAL,                -- zona de responsabilidad del dev
    qa_biz_hours REAL,
    blocked_biz_hours REAL,
    waiting_biz_hours REAL,
    review_biz_hours REAL,
    
    -- Calidad
    qa_first_pass INTEGER,                  -- 0/1, NULL si no aplica
    qa_attempts INTEGER DEFAULT 0,
    review_rejections INTEGER DEFAULT 0,
    
    -- SP calculado (recalculable con cambio de engine_version)
    engine_version_id INTEGER REFERENCES engine_versions(id),
    sp_base REAL,                           -- = cp
    m_calidad REAL DEFAULT 1.0,
    m_eficiencia REAL DEFAULT 1.0,
    m_dificultad REAL DEFAULT 1.0,
    m_lider REAL DEFAULT 1.0,
    m_cooperacion REAL DEFAULT 1.0,
    sp_flat_bonus REAL DEFAULT 0,
    sp_penalty REAL DEFAULT 0,
    sp_final REAL,                          -- valor que entra al leaderboard
    sp_last_calculated_at TEXT,
    
    -- Difficulty modifier (custom field de Jira)
    difficulty_modifier_raw TEXT,           -- string del campo Jira
    
    -- Auditoría
    last_synced_at TEXT NOT NULL DEFAULT (datetime('now')),
    raw_changelog TEXT                      -- JSON del changelog completo
);

CREATE INDEX idx_subtasks_assignee ON subtasks(assignee_player_id);
CREATE INDEX idx_subtasks_sprint ON subtasks(sprint_id);
CREATE INDEX idx_subtasks_status ON subtasks(status);
CREATE INDEX idx_subtasks_area ON subtasks(area);
CREATE INDEX idx_subtasks_project ON subtasks(project_code);
CREATE INDEX idx_subtasks_done_at ON subtasks(done_at);
CREATE INDEX idx_subtasks_story ON subtasks(parent_story_key);
```

**Notas críticas:**
- `sp_final` se recalcula cuando: (a) cambia el estado en Jira, (b) se aplica un `sp_adjustment`, (c) se publica nueva `engine_version`.
- `cp` no cambia una vez aprobado (regla de oro JPDS v2.0). Si una sub-task se reestima, se crea una nueva.
- `area` repite enum por flexibilidad: una sub-task INFRA o BUGFIX no tiene "área" pero sí tipo.

---

## 12. `sprints`

```sql
CREATE TABLE sprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                     -- 'Sprint 2026-05-W19'
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0,
    is_closed INTEGER NOT NULL DEFAULT 0,
    mvp_player_id INTEGER REFERENCES players(id),
    mvp_reason TEXT,
    closed_at TEXT,
    closed_by INTEGER REFERENCES players(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_sprints_active ON sprints(is_active);
CREATE INDEX idx_sprints_dates ON sprints(start_date, end_date);
```

**Nota:** solo un sprint activo a la vez. Se valida a nivel app y con constraint parcial:
```sql
CREATE UNIQUE INDEX idx_one_active_sprint ON sprints(is_active) WHERE is_active = 1;
```

---

## 13. `sp_adjustments`

Bonos y penalizaciones aplicadas. Inmutable, append-only.

```sql
CREATE TABLE sp_adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE RESTRICT,
    sprint_id INTEGER NOT NULL REFERENCES sprints(id) ON DELETE RESTRICT,
    subtask_key TEXT REFERENCES subtasks(jira_key) ON DELETE SET NULL,
    
    adjustment_type TEXT NOT NULL,          -- 'debuff_auto','debuff_manual','buff_manual','mvp_bonus','achievement_bonus'
    source_code TEXT,                       -- ref a buffs.code, debuffs.code, achievements.code
    sp_delta REAL NOT NULL,                 -- positivo o negativo
    reason TEXT NOT NULL,
    
    -- Apelación (OQ-12)
    is_appealed INTEGER NOT NULL DEFAULT 0,
    appeal_resolution TEXT,                 -- 'upheld','reversed','reduced'
    appeal_resolved_by INTEGER REFERENCES players(id),
    appeal_resolved_at TEXT,
    appeal_notes TEXT,
    
    -- Auditoría
    applied_by INTEGER REFERENCES players(id),  -- NULL si fue automático
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_adj_player_sprint ON sp_adjustments(player_id, sprint_id);
CREATE INDEX idx_adj_subtask ON sp_adjustments(subtask_key);
CREATE INDEX idx_adj_type ON sp_adjustments(adjustment_type);
```

**Notas:**
- Append-only: una corrección no UPDATE, crea nuevo registro con `sp_delta` opuesto y `reason='reversal of #N'`.
- Si una penalización es apelada y revertida, se crea adjustment de signo opuesto en lugar de borrar el original. Esto preserva trazabilidad.

---

## 14. `achievement_unlocks`

Relación many-to-many player ↔ achievement.

```sql
CREATE TABLE achievement_unlocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    achievement_code TEXT NOT NULL REFERENCES achievements(code) ON DELETE RESTRICT,
    sprint_id INTEGER REFERENCES sprints(id),
    unlocked_at TEXT NOT NULL DEFAULT (datetime('now')),
    trigger_context TEXT,                   -- JSON con info del evento (subtask_key, etc.)
    UNIQUE(player_id, achievement_code)
);

CREATE INDEX idx_unlocks_player ON achievement_unlocks(player_id);
CREATE INDEX idx_unlocks_achievement ON achievement_unlocks(achievement_code);
```

**Nota:** UNIQUE constraint previene desbloquear el mismo achievement 2 veces. Si en el futuro hay achievements repetibles, se cambia.

---

## 15. `redemptions`

Canjes de tienda.

```sql
CREATE TABLE redemptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE RESTRICT,
    item_code TEXT NOT NULL REFERENCES shop_items(code) ON DELETE RESTRICT,
    sprint_id INTEGER REFERENCES sprints(id),
    sp_spent INTEGER NOT NULL,
    
    status TEXT NOT NULL DEFAULT 'requested'
        CHECK(status IN ('requested','approved','delivered','rejected','cancelled')),
    
    requested_at TEXT NOT NULL DEFAULT (datetime('now')),
    approved_at TEXT,
    approved_by INTEGER REFERENCES players(id),
    delivered_at TEXT,
    delivered_by INTEGER REFERENCES players(id),
    delivery_notes TEXT,
    rejection_reason TEXT
);

CREATE INDEX idx_redemptions_player ON redemptions(player_id);
CREATE INDEX idx_redemptions_status ON redemptions(status);
CREATE INDEX idx_redemptions_requested ON redemptions(requested_at);
```

**Nota:** flujo bajo modelo local es `requested → approved → delivered` casi inmediato en la weekly. Si se rechaza, `sp_spent` se devuelve al wallet via `sp_adjustment` de signo opuesto.

---

## 16. `engine_versions`

Config del motor versionada.

```sql
CREATE TABLE engine_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_label TEXT UNIQUE NOT NULL,     -- 'v2.0','v2.1'
    config_json TEXT NOT NULL,              -- JSON con todos los multiplicadores, rangos, premios
    is_active INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    activated_at TEXT,
    activated_by INTEGER REFERENCES players(id)
);

CREATE UNIQUE INDEX idx_one_active_engine ON engine_versions(is_active) WHERE is_active = 1;
```

**Nota:** cambios de engine entran al inicio de sprint, nunca a mitad (JPDS v2.0 sec 5.2). El `config_json` contiene la estructura completa: rangos por talla, multiplicadores, premios económicos, techos, etc.

---

## 17. `audit_log`

Toda acción administrativa.

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_player_id INTEGER REFERENCES players(id),
    action_type TEXT NOT NULL,              -- 'penalty_applied','penalty_appealed','mvp_assigned','engine_published','redemption_approved'...
    entity_type TEXT NOT NULL,              -- 'subtask','player','sprint','redemption','engine_version'
    entity_id TEXT NOT NULL,                -- PK como string
    before_state TEXT,                      -- JSON
    after_state TEXT,                       -- JSON
    reason TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_actor ON audit_log(actor_player_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
```

---

## 18. `leaderboard_snapshots`

Caché regenerable de rankings.

```sql
CREATE TABLE leaderboard_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sprint_id INTEGER REFERENCES sprints(id),
    period_type TEXT NOT NULL CHECK(period_type IN ('sprint','monthly','quarterly')),
    period_label TEXT NOT NULL,             -- '2026-05', '2026-Q2', 'Sprint-19'
    category TEXT NOT NULL,                 -- 'BE','FE','DESIGN','DB','QA','MVP','GLOBAL'
    project_code TEXT REFERENCES projects(code),  -- NULL = todos los proyectos
    
    player_id INTEGER NOT NULL REFERENCES players(id),
    rank INTEGER NOT NULL,
    sp_total REAL NOT NULL,
    sp_per_hour REAL,
    cp_total REAL,
    metadata TEXT,                          -- JSON con breakdown
    
    calculated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_lb_period ON leaderboard_snapshots(period_type, period_label, category);
CREATE INDEX idx_lb_player ON leaderboard_snapshots(player_id);
```

**Nota:** regenerable. Si cambia engine_version y se recalculan SPs, se invalidan y regeneran.

---

## Relaciones (diagrama lógico)

```
players ──┬── (1:N) ── subtasks (assignee)
          ├── (1:N) ── sp_adjustments
          ├── (1:N) ── achievement_unlocks ──→ achievements
          ├── (1:N) ── redemptions ──→ shop_items
          ├── (N:1) ── classes
          └── (N:1) ── avatars

projects ──┬── (1:N) ── epics
           └── (1:N) ── subtasks (denormalizado)

epics ── (1:N) ── stories ── (1:N) ── subtasks

sprints ──┬── (1:N) ── subtasks
          ├── (1:N) ── sp_adjustments
          └── (1:1) ── mvp (player)

engine_versions ── (1:N) ── subtasks (sp recalculable)

buffs/debuffs ── (referenciados por código en sp_adjustments.source_code)
```

---

## Computed values — vistas SQL útiles

Estas no son tablas, son vistas que la app consulta directo. Evitan duplicación de lógica.

### Vista: `player_wallet`

Balance de SP gastables por player.

```sql
CREATE VIEW player_wallet AS
SELECT 
    p.id AS player_id,
    p.display_name,
    -- SP histórico ganado en subtasks Done
    COALESCE((
        SELECT SUM(s.sp_final) 
        FROM subtasks s 
        WHERE s.assignee_player_id = p.id 
          AND s.status = 'Done'
    ), 0) AS sp_earned_total,
    -- SP de ajustes (bonos manuales, MVP, achievements)
    COALESCE((
        SELECT SUM(a.sp_delta) 
        FROM sp_adjustments a 
        WHERE a.player_id = p.id
    ), 0) AS sp_adjustments_total,
    -- SP gastado en redenciones aprobadas/delivered
    COALESCE((
        SELECT SUM(r.sp_spent) 
        FROM redemptions r 
        WHERE r.player_id = p.id 
          AND r.status IN ('approved','delivered')
    ), 0) AS sp_spent_total,
    -- Balance final
    COALESCE((
        SELECT SUM(s.sp_final) FROM subtasks s 
        WHERE s.assignee_player_id = p.id AND s.status = 'Done'
    ), 0) + COALESCE((
        SELECT SUM(a.sp_delta) FROM sp_adjustments a WHERE a.player_id = p.id
    ), 0) - COALESCE((
        SELECT SUM(r.sp_spent) FROM redemptions r 
        WHERE r.player_id = p.id AND r.status IN ('approved','delivered')
    ), 0) AS wallet_balance
FROM players p
WHERE p.is_active = 1;
```

### Vista: `monthly_spent_by_player`

Para validar el techo de gasto mensual de 100 SP (OQ-10).

```sql
CREATE VIEW monthly_spent_by_player AS
SELECT 
    player_id,
    strftime('%Y-%m', requested_at) AS month,
    SUM(sp_spent) AS sp_spent_in_month
FROM redemptions
WHERE status IN ('approved','delivered')
GROUP BY player_id, strftime('%Y-%m', requested_at);
```

### Vista: `subtask_full` (con joins comunes)

```sql
CREATE VIEW subtask_full AS
SELECT 
    s.*,
    p.display_name AS assignee_name,
    p.area AS assignee_area,
    proj.arena_name AS project_arena_name,
    sp.name AS sprint_name
FROM subtasks s
LEFT JOIN players p ON s.assignee_player_id = p.id
LEFT JOIN projects proj ON s.project_code = proj.code
LEFT JOIN sprints sp ON s.sprint_id = sp.id;
```

---

## Reglas de integridad operativa

Validaciones que viven a nivel app (Python), no en SQL:

1. **CP inmutable post-aprobación.** Una vez `cp_approved_at IS NOT NULL`, no se puede UPDATE `cp` ni `complexity_size`.
2. **Una sola sprint activa.** Constraint parcial ya lo asegura, app valida antes.
3. **Aprobación CP obligatoria para L/XL.** App rechaza paso a `Ready` si `cp >= 5` y `cp_approved_at IS NULL`.
4. **Techo de gasto mensual.** App valida `monthly_spent_by_player <= 100` antes de aprobar redemption.
5. **Cambio de clase 1 vez por trimestre.** App valida `class_last_changed_at` antes de UPDATE en `players.class_code`.
6. **No XXL aceptado.** App rechaza `complexity_size = 'XXL'`, requiere romper la sub-task primero.
7. **WIP máximo por área.** App calcula WIP actual antes de permitir mover sub-task adicional a estado activo. Si excede, marca debuff `Greedy Hoarder` (D11).
8. **Atribución de bug derivado.** Cuando se crea un Bug Sub-task con link `is caused by` a otra sub-task, app dispara debuff D07/D08/D09 sobre el assignee original.

---

## Datos seed mínimos para arrancar

Al iniciar la BD, se cargan:

- 12 filas en `classes` (catálogo doc, sección 1).
- 16 filas en `avatars` (catálogo doc, sección 2).
- 3 filas en `projects` (P01, P02, P03).
- 17 filas en `buffs`.
- 16 filas en `debuffs`.
- 12 filas en `achievements`.
- 8 filas en `shop_items`.
- 1 fila en `engine_versions` con la config v2.0 del JPDS marcada como activa.
- 14 filas en `players` (tu equipo actual + tú como PM).
- 1 fila en `sprints` con el sprint en curso marcado como activo.

Total: ~100 filas de seed antes de la primera sincronización con Jira.

---

## Notas de evolución

Cuando se migre de SQLite a PostgreSQL (cuando salga del modelo local), los cambios son menores:

- Cambiar `INTEGER PRIMARY KEY AUTOINCREMENT` por `SERIAL` o `BIGSERIAL`.
- Cambiar `TEXT` con timestamps por `TIMESTAMPTZ`.
- Cambiar JSON strings por `JSONB` (con índices GIN).
- Cambiar booleans 0/1 por `BOOLEAN`.
- Cambiar constraints parciales (sintaxis idéntica, ambos soportan).
- Agregar `tenant_id` a todas las tablas si se activa multi-tenant.

SQLAlchemy abstrae la mayoría de estas diferencias con sus tipos `DateTime`, `Boolean`, `JSON`. Si se usa SQLAlchemy desde día 1, la migración es ~1 día.

---

*v1.0 — Mayo 2026. Listo para mergear al PVD v0.2 como Anexo E. Próximo entregable: 15 casos de uso enganchados a este schema.*
