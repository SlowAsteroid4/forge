-- WP-01a: Introduce Cycles (additive, no-destructive)
-- Alembic revision: c9d069c028f5
-- Applied: 2026-05-29
-- Branch: refactor/cycles

-- TABLE: cycles
CREATE TABLE cycles (
    id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    iso_year INTEGER NOT NULL,
    iso_week INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'planned' NOT NULL,
    mvp_player_id INTEGER REFERENCES players(id) ON DELETE SET NULL,
    mvp_reason TEXT,
    mvp_assigned_at DATETIME,
    mvp_assigned_by INTEGER REFERENCES players(id) ON DELETE SET NULL,
    opened_at DATETIME,
    closed_at DATETIME,
    closed_by INTEGER REFERENCES players(id) ON DELETE SET NULL,
    archived_at DATETIME,
    closing_snapshot_json TEXT,
    is_legacy BOOLEAN DEFAULT '0' NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT pk_cycles PRIMARY KEY (id),
    CONSTRAINT uq_cycles_name UNIQUE (name)
);
CREATE INDEX idx_cycles_status ON cycles (status);
CREATE INDEX idx_cycles_start_date ON cycles (start_date);
CREATE INDEX idx_cycles_end_date ON cycles (end_date);
CREATE UNIQUE INDEX idx_cycles_iso ON cycles (iso_year, iso_week);
CREATE UNIQUE INDEX idx_one_active_cycle ON cycles(status) WHERE status = 'active';

-- TABLE: mvp_monthly
CREATE TABLE mvp_monthly (
    id INTEGER NOT NULL PRIMARY KEY,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE RESTRICT,
    reason TEXT,
    sp_reward INTEGER DEFAULT 10 NOT NULL,
    assigned_at DATETIME NOT NULL,
    assigned_by INTEGER NOT NULL REFERENCES players(id) ON DELETE RESTRICT,
    period_label VARCHAR(20) NOT NULL
);
CREATE INDEX idx_mvp_monthly_period ON mvp_monthly (year, month);
CREATE INDEX idx_mvp_monthly_player ON mvp_monthly (player_id);

-- TABLE: forecast_snapshots
CREATE TABLE forecast_snapshots (
    id INTEGER NOT NULL PRIMARY KEY,
    generated_at DATETIME NOT NULL,
    trigger_cycle_id INTEGER NOT NULL REFERENCES cycles(id) ON DELETE RESTRICT,
    epic_key VARCHAR(20) NOT NULL,
    area VARCHAR(20) NOT NULL,
    p30_cp_per_cycle FLOAT,
    p50_cp_per_cycle FLOAT,
    p85_cp_per_cycle FLOAT,
    remaining_cp FLOAT,
    eta_p30_cycles FLOAT,
    eta_p50_cycles FLOAT,
    eta_p85_cycles FLOAT,
    snapshot_json TEXT
);
CREATE INDEX idx_forecast_generated_at ON forecast_snapshots (generated_at);
CREATE INDEX idx_forecast_cycle ON forecast_snapshots (trigger_cycle_id);
CREATE INDEX idx_forecast_epic ON forecast_snapshots (epic_key);

-- COLUMNS ADDED (nullable, coexist with sprint_id)
ALTER TABLE subtasks ADD COLUMN cycle_id INTEGER REFERENCES cycles(id) ON DELETE SET NULL;
CREATE INDEX idx_subtasks_cycle_id ON subtasks (cycle_id);

ALTER TABLE leaderboard_snapshots ADD COLUMN cycle_id INTEGER REFERENCES cycles(id) ON DELETE SET NULL;
CREATE INDEX idx_leaderboard_snapshots_cycle_id ON leaderboard_snapshots (cycle_id);

-- VIEWS
CREATE VIEW cycles_active AS
    SELECT * FROM cycles WHERE status = 'active';

CREATE VIEW cycle_metrics AS
    SELECT
        c.id          AS cycle_id,
        c.name        AS cycle_name,
        c.iso_year,
        c.iso_week,
        c.status,
        COUNT(s.jira_key)                              AS subtasks_total,
        SUM(CASE WHEN s.status = 'Done' THEN 1 ELSE 0 END) AS subtasks_done,
        COALESCE(SUM(s.cp), 0)                         AS cp_total,
        COALESCE(SUM(s.sp_final), 0)                   AS sp_total,
        AVG(s.ct_biz_hours)                            AS avg_ct_biz_hours
    FROM cycles c
    LEFT JOIN subtasks s ON s.cycle_id = c.id
    GROUP BY c.id;

CREATE VIEW rolling_window_4 AS
    SELECT cm.*
    FROM cycle_metrics cm
    JOIN cycles c ON c.id = cm.cycle_id
    WHERE c.status IN ('closed', 'archived')
    ORDER BY c.start_date DESC
    LIMIT 4;

CREATE VIEW rolling_window_4_by_area AS
    SELECT
        c.id          AS cycle_id,
        c.name        AS cycle_name,
        c.start_date,
        s.area,
        COUNT(s.jira_key)       AS subtasks_total,
        COALESCE(SUM(s.cp), 0)  AS cp_total,
        COALESCE(SUM(s.sp_final), 0) AS sp_total,
        AVG(s.ct_biz_hours)     AS avg_ct_biz_hours
    FROM cycles c
    JOIN subtasks s ON s.cycle_id = c.id
    WHERE c.status IN ('closed', 'archived')
      AND c.id IN (
          SELECT id FROM cycles
          WHERE status IN ('closed', 'archived')
          ORDER BY start_date DESC
          LIMIT 4
      )
    GROUP BY c.id, s.area;

CREATE VIEW pulse_now AS
    SELECT
        s.jira_key, s.summary, s.status, s.area,
        s.assignee_player_id, s.cp, s.sp_final,
        s.done_at, s.ct_biz_hours, s.cycle_id
    FROM subtasks s
    JOIN cycles_active ca ON s.cycle_id = ca.id;

CREATE VIEW current_forecast_by_epic AS
    SELECT
        fs.epic_key, fs.area,
        fs.p30_cp_per_cycle, fs.p50_cp_per_cycle, fs.p85_cp_per_cycle,
        fs.remaining_cp,
        fs.eta_p30_cycles, fs.eta_p50_cycles, fs.eta_p85_cycles,
        fs.generated_at
    FROM forecast_snapshots fs
    JOIN (
        SELECT epic_key, MAX(generated_at) AS max_gen
        FROM forecast_snapshots
        GROUP BY epic_key
    ) latest ON fs.epic_key = latest.epic_key AND fs.generated_at = latest.max_gen;

-- NOTE: Recommend removing alembic/versions/ from .gitignore for structural migrations.
