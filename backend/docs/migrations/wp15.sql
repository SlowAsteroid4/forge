-- WP-15 — Fix de identidades y áreas (Ritmo Operativo)
-- Generado/documentado por la sesión WP-15. La columna `role` se aplica vía
-- Alembic (alembic/versions/20260605_1200_wp15_player_role.py). Este archivo
-- documenta el equivalente SQL y los cambios de datos (todos auditados en audit_logs).

-- 1) Migración aditiva: columna de rol de gobierno (independiente de area)
ALTER TABLE players ADD COLUMN role VARCHAR(20);

-- 2) PASO 2 — Jesús (id 12): rol PO de gobierno, SIN salir de DESIGN
UPDATE players SET role = 'PO' WHERE id = 12;   -- Jesús Mancilla (area sigue DESIGN)

-- 3) PASO 3 — "Equipo de Producto" (id 12 -> 14): area PO -> DESIGN
--    Mecanismo durable: el sync NO pisa players.area (WP-13), y subtasks.area
--    se re-infiere desde player.area del assignee (sync_orchestrator._infer_area).
UPDATE players SET area = 'DESIGN' WHERE id = 14;          -- Equipo de Producto

--    Corregir las filas subtasks.area ya almacenadas (84 Design Sub-tasks)
UPDATE subtasks SET area = 'DESIGN'
WHERE assignee_player_id = 14 AND area = 'PO';

-- NOTA: NO se reasigna assignee_player_id de las subtasks del grupo a Jesús,
-- porque el sync (sync_orchestrator.py:224) reescribe assignee_player_id desde
-- Jira en cada corrida y revertiría el cambio. La atribución por área (player.area)
-- es la capa durable, según decisión del chat maestro.
