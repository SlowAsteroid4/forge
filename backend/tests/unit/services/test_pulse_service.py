"""Tests para PulseService (UC-16) — Pulso Operativo (rediseño WP-16)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from forge.db.models.area_wip_limit import AreaWipLimit
from forge.db.models.player import Player
from forge.db.models.project import Project
from forge.db.models.subtask import Subtask
from forge.schemas.pulse import FlowCounter, PulseSnapshot
from forge.services.pulse_service import PulseService

# ── Factories ─────────────────────────────────────────────────────────────────


def _seed_wip_limits(session: Session) -> None:
    """Sembrar catálogo de áreas vía ORM (define qué áreas reciben card)."""
    for area, limit, excluded in [
        ("BE", 3, False),
        ("FE", 3, False),
        ("DESIGN", 4, False),
        ("DB", 5, False),
        ("QA", 5, True),
        ("PO", 5, True),
    ]:
        existing = session.get(AreaWipLimit, area)
        if existing is None:
            session.add(AreaWipLimit(area=area, wip_limit=limit, exclude_from_wip=excluded))
    session.commit()


def _player(session: Session, pid: int, area: str = "BE", name: str = "Dev") -> Player:
    p = Player(
        id=pid,
        jira_account_id=f"jira-{pid}",
        display_name=name,
        email=f"dev{pid}@test.com",
        area=area,
        employment_type="internal",
        is_active=True,
    )
    session.add(p)
    session.commit()
    return p


def _project(session: Session) -> Project:
    existing = session.get(Project, "YAP")
    if existing:
        return existing
    p = Project(
        code="YAP",
        jira_prefix="YAP",
        internal_name="Yapsi",
        arena_name="Yapsi Arena",
    )
    session.add(p)
    session.commit()
    return p


# La card del Pulso se deriva del issue_type, no del área del assignee. Para
# tests que expresan intención por `area`, mapeamos área → issue_type canónico.
_AREA_TO_ISSUE_TYPE = {
    "BE": "Backend Sub-task",
    "FE": "Frontend Sub-Task",
    "DB": "Database Sub-task",
    "DESIGN": "Design Sub-task",
    "BUG": "Bug Sub-task",
}


def _subtask(
    session: Session,
    key: str,
    status: str,
    area: str = "BE",
    player_id: int | None = None,
    project_code: str = "YAP",
    created_days_ago: int = 1,
    changelog_entries: list[dict] | None = None,
    issue_type: str | None = None,
) -> Subtask:
    now = datetime.utcnow()
    cl_data = {"histories": changelog_entries or []}
    s = Subtask(
        jira_key=key,
        summary=f"Subtask {key}",
        status=status,
        area=area,
        assignee_player_id=player_id,
        project_code=project_code,
        last_synced_at=now,
        issue_type=issue_type or _AREA_TO_ISSUE_TYPE.get(area, "Backend Sub-task"),
        raw_changelog=json.dumps(cl_data),
    )
    session.add(s)
    session.flush()
    if created_days_ago != 1:
        session.execute(
            text("UPDATE subtasks SET created_at = :dt WHERE jira_key = :key"),
            {"dt": (now - timedelta(days=created_days_ago)).isoformat(), "key": key},
        )
    session.commit()
    session.refresh(s)
    return s


def _status_changelog_entry(from_s: str, to_s: str, hours_ago: float) -> dict:
    ts = (datetime.now(UTC) - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%S.000+0000")
    return {
        "id": "1",
        "created": ts,
        "author": {"displayName": "bot"},
        "items": [{"field": "status", "fromString": from_s, "toString": to_s}],
    }


def _counter(snap: PulseSnapshot, key: str) -> FlowCounter:
    return next(c for c in snap.flow_counters if c.key == key)


# ── CAMBIO 1: Franja de contadores por estado ──────────────────────────────────


def test_flow_counters_siempre_7_en_orden(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    snap = PulseService(test_session).get_pulse()
    keys = [c.key for c in snap.flow_counters]
    assert keys == [
        "backlog",
        "ready",
        "in_progress",
        "in_review",
        "ready_for_qa",
        "in_qa",
        "done",
    ]


def test_flow_counters_incluye_backlog_y_done(test_session: Session):
    """La franja cuenta Backlog y Done (que el fetch operativo excluye)."""
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 1, "BE", "Dev1")
    _subtask(test_session, "YAP-B1", "Backlog", "BE", p.id)
    _subtask(test_session, "YAP-B2", "Backlog", "BE", p.id)
    _subtask(test_session, "YAP-D1", "Done", "BE", p.id)
    _subtask(test_session, "YAP-IP", "In Progress", "BE", p.id)

    snap = PulseService(test_session).get_pulse()
    assert _counter(snap, "backlog").count == 2
    assert _counter(snap, "done").count == 1
    assert _counter(snap, "in_progress").count == 1


def test_flow_counters_pliega_variantes_in_progress(test_session: Session):
    """Active/Implementation/In Design/UI Implementation se pliegan en In Progress."""
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 2, "BE", "Dev2")
    _subtask(test_session, "YAP-1", "In Progress", "BE", p.id)
    _subtask(test_session, "YAP-2", "Active", "BE", p.id)
    _subtask(test_session, "YAP-3", "Implementation", "BE", p.id)
    _subtask(test_session, "YAP-4", "In Design", "DESIGN", p.id)
    _subtask(test_session, "YAP-5", "UI Implementation", "FE", p.id)

    ip = _counter(PulseService(test_session).get_pulse(), "in_progress")
    assert ip.count == 5
    assert "Active" in ip.raw_statuses
    assert "UI Implementation" in ip.raw_statuses


def test_flow_counter_code_review_mapea_in_review(test_session: Session):
    """El contador 'Code Review' cuenta el status real 'In Review'."""
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 3, "BE", "Dev3")
    _subtask(test_session, "YAP-R1", "In Review", "BE", p.id)

    cr = _counter(PulseService(test_session).get_pulse(), "in_review")
    assert cr.label == "Code Review"
    assert cr.count == 1
    assert cr.raw_statuses == ["In Review"]


# ── CAMBIO 2: Cards por área ───────────────────────────────────────────────────


def test_area_card_agrupa_por_estado(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 4, "BE", "DevA")
    _subtask(test_session, "YAP-A1", "In Progress", "BE", p.id)
    _subtask(test_session, "YAP-A2", "In Progress", "BE", p.id)
    _subtask(test_session, "YAP-A3", "In Review", "BE", p.id)

    snap = PulseService(test_session).get_pulse()
    be = next(c for c in snap.area_cards if c.area == "BE")
    assert be.total_active == 3
    groups = {g.status: g for g in be.by_status}
    assert groups["In Progress"].count == 2
    assert groups["In Review"].count == 1
    # Cada tarea trae código + dueño + zona de color
    t = groups["In Progress"].tasks[0]
    assert t.jira_key.startswith("YAP-")
    assert t.assignee_name == "DevA"
    assert t.zone == "dev"


def test_area_card_muestra_backlog_excluye_done(test_session: Session):
    """Backlog aparece en by_status pero no cuenta en total_active. Done siempre excluido."""
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 5, "BE", "DevB")
    _subtask(test_session, "YAP-AC", "In Progress", "BE", p.id)
    _subtask(test_session, "YAP-BK", "Backlog", "BE", p.id)
    _subtask(test_session, "YAP-DN", "Done", "BE", p.id)

    be = next(c for c in PulseService(test_session).get_pulse().area_cards if c.area == "BE")
    assert be.total_active == 1, "Solo In Progress cuenta como activa"
    statuses = {g.status for g in be.by_status}
    assert "Backlog" in statuses, "Backlog debe aparecer en el desglose de la card"
    assert "Done" not in statuses, "Done nunca aparece en la card"


def test_card_se_deriva_del_issue_type_no_del_area_del_assignee(test_session: Session):
    """Regresión YAP-877: una Database Sub-task hecha por un dev de BE debe caer
    en la card DB, NO en BE. La card se decide por issue_type, no por assignee."""
    _seed_wip_limits(test_session)
    test_session.add(AreaWipLimit(area="BUG", wip_limit=3, exclude_from_wip=False))
    test_session.commit()
    _project(test_session)
    be_dev = _player(test_session, 5, "BE", "DevBE")

    # Todas asignadas a un dev cuya área (assignee) es BE:
    _subtask(test_session, "YAP-877", "In Review", player_id=be_dev.id, issue_type="Database Sub-task")
    _subtask(test_session, "YAP-BE1", "In Progress", player_id=be_dev.id, issue_type="Backend Sub-task")
    _subtask(test_session, "YAP-BUG1", "In QA", player_id=be_dev.id, issue_type="Bug")
    _subtask(test_session, "YAP-DB2", "In Review", player_id=be_dev.id, issue_type="Database")

    cards = {c.area: c for c in PulseService(test_session).get_pulse().area_cards}

    db_keys = {t.jira_key for g in cards["DB"].by_status for t in g.tasks}
    be_keys = {t.jira_key for g in cards["BE"].by_status for t in g.tasks}
    bug_keys = {t.jira_key for g in cards["BUG"].by_status for t in g.tasks}

    assert "YAP-877" in db_keys, "Database Sub-task debe ir a DB"
    assert "YAP-DB2" in db_keys, "Database (standalone) debe ir a DB"
    assert "YAP-877" not in be_keys, "Database Sub-task NO debe contaminar BE"
    assert be_keys == {"YAP-BE1"}, "BE solo contiene Backend Sub-task"
    assert bug_keys == {"YAP-BUG1"}, "Bug va a BUG"


def test_task_generico_no_aparece_en_ninguna_card(test_session: Session):
    """Tipos sin disciplina (Task) se excluyen del Pulso por completo."""
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 5, "BE", "DevBE")
    _subtask(test_session, "YAP-T1", "In Progress", player_id=p.id, issue_type="Task")
    _subtask(test_session, "YAP-CO", "In Progress", player_id=p.id, issue_type="Coordination")

    cards = PulseService(test_session).get_pulse().area_cards
    all_keys = {t.jira_key for c in cards for g in c.by_status for t in g.tasks}
    assert "YAP-T1" not in all_keys, "Task no pertenece a ninguna card"
    assert "YAP-CO" not in all_keys, "Coordination excluida"


def test_area_cards_excluyen_qa_y_po(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    areas = [c.area for c in PulseService(test_session).get_pulse().area_cards]
    assert "QA" not in areas
    assert "PO" not in areas
    assert set(areas) == {"BE", "FE", "DESIGN", "DB"}


def test_area_card_etiqueta_equipo_agregado(test_session: Session):
    """'Equipo de Producto' se marca como cuenta-grupo agregada, no dev individual."""
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 14, "DESIGN", "Equipo de Producto")
    _subtask(test_session, "YAP-EP", "In Design", "DESIGN", p.id)

    design = next(c for c in PulseService(test_session).get_pulse().area_cards if c.area == "DESIGN")
    task = design.by_status[0].tasks[0]
    assert task.is_aggregate_team is True
    assert task.assignee_name == "Equipo de Producto"


def test_area_card_dev_individual_no_es_agregado(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 12, "DESIGN", "Jesús Mancilla")
    _subtask(test_session, "YAP-JE", "In Design", "DESIGN", p.id)

    design = next(c for c in PulseService(test_session).get_pulse().area_cards if c.area == "DESIGN")
    task = design.by_status[0].tasks[0]
    assert task.is_aggregate_team is False


# ── CAMBIO 3: Drill-down de dev ────────────────────────────────────────────────


def test_dev_drilldown_lista_tareas_en_progreso(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 6, "BE", "DevDD")
    _subtask(test_session, "YAP-DD1", "In Progress", "BE", p.id)
    _subtask(test_session, "YAP-DD2", "In Review", "BE", p.id)
    _subtask(test_session, "YAP-DD3", "Done", "BE", p.id)  # terminal: no aparece

    dd = PulseService(test_session).get_dev_drilldown(p.id)
    assert dd.display_name == "DevDD"
    assert dd.total == 2
    keys = {t.jira_key for t in dd.tasks}
    assert keys == {"YAP-DD1", "YAP-DD2"}
    assert all(t.zone for t in dd.tasks)


def test_dev_drilldown_equipo_agregado(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 14, "DESIGN", "Equipo de Producto")
    _subtask(test_session, "YAP-G1", "In Design", "DESIGN", p.id)

    dd = PulseService(test_session).get_dev_drilldown(p.id)
    assert dd.is_aggregate_team is True
    assert dd.total == 1


def test_dev_drilldown_player_inexistente(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    dd = PulseService(test_session).get_dev_drilldown(999)
    assert dd.total == 0
    assert dd.tasks == []


# ── Bloqueos (conservado) ──────────────────────────────────────────────────────


def test_bloqueo_critico_mas_8h(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 7, "BE", "Bloq")
    entries = [_status_changelog_entry("In Progress", "Blocked", hours_ago=48)]
    _subtask(test_session, "YAP-BLK", "Blocked", "BE", p.id, changelog_entries=entries)

    snap = PulseService(test_session).get_pulse()
    assert len(snap.blocks) == 1
    assert snap.blocks[0].es_critico is True
    assert snap.blocks[0].horas_bloqueado >= 8.0


def test_bloqueo_no_critico_menos_8h(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 8, "BE", "Bloq2")
    entries = [_status_changelog_entry("In Progress", "Blocked", hours_ago=3)]
    _subtask(test_session, "YAP-BLK2", "Blocked", "BE", p.id, changelog_entries=entries)

    snap = PulseService(test_session).get_pulse()
    assert snap.blocks[0].es_critico is False


def test_block_reason_siempre_null(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 9, "BE", "Dev9")
    _subtask(test_session, "YAP-NR", "Blocked", "BE", p.id)

    snap = PulseService(test_session).get_pulse()
    assert snap.blocks[0].block_reason is None


# ── Aging (conservado) ─────────────────────────────────────────────────────────


def test_aging_critico_detectado(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 10, "BE", "Anciano")
    entries = [_status_changelog_entry("Ready", "In Progress", hours_ago=24 * 42)]
    _subtask(
        test_session, "YAP-OLD", "In Progress", "BE", p.id,
        created_days_ago=42, changelog_entries=entries,
    )

    snap = PulseService(test_session).get_pulse()
    keys = [a.jira_key for a in snap.aging_critical]
    assert "YAP-OLD" in keys


def test_aging_no_critico_1_dia(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 11, "FE", "Nuevo")
    entries = [_status_changelog_entry("Ready", "In Progress", hours_ago=4)]
    _subtask(
        test_session, "YAP-NEW", "In Progress", "FE", p.id,
        created_days_ago=1, changelog_entries=entries,
    )

    snap = PulseService(test_session).get_pulse()
    keys = [a.jira_key for a in snap.aging_critical]
    assert "YAP-NEW" not in keys


# ── Filtros (conservado, adaptado al nuevo schema) ─────────────────────────────


def test_filtro_por_area(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p_be = _player(test_session, 20, "BE", "DevBE")
    p_fe = _player(test_session, 21, "FE", "DevFE")
    _subtask(test_session, "YAP-F1", "In Progress", "BE", p_be.id)
    _subtask(test_session, "YAP-F2", "In Review", "FE", p_fe.id)

    snap = PulseService(test_session).get_pulse(areas=["BE"])
    assert _counter(snap, "in_progress").count == 1
    assert all(c.area == "BE" for c in snap.area_cards)


def test_filtro_por_project_code(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 22, "BE", "DevP")
    _subtask(test_session, "YAP-P1", "In Progress", "BE", p.id, project_code="YAP")

    snap_yap = PulseService(test_session).get_pulse(project_code="YAP")
    assert _counter(snap_yap, "in_progress").count >= 1

    snap_xxx = PulseService(test_session).get_pulse(project_code="XXX")
    assert _counter(snap_xxx, "in_progress").count == 0


def test_filtro_por_player_id(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p1 = _player(test_session, 23, "BE", "Uno")
    p2 = _player(test_session, 24, "BE", "Dos")
    _subtask(test_session, "YAP-PL1", "In Progress", "BE", p1.id)
    _subtask(test_session, "YAP-PL2", "In Review", "BE", p2.id)

    snap = PulseService(test_session).get_pulse(player_id=p1.id)
    assert _counter(snap, "in_progress").count == 1


# ── Anti-regresión: 0 escrituras ───────────────────────────────────────────────


def test_pulse_no_escribe_en_gamificacion(test_session: Session):
    """Llamar al Pulso NO debe escribir en sp_adjustments ni leaderboard_snapshots."""
    _seed_wip_limits(test_session)
    _project(test_session)

    def _count(table: str) -> int:
        r = test_session.execute(text(f"SELECT COUNT(*) FROM {table}"))
        return r.scalar() or 0

    before_sp = _count("sp_adjustments")
    before_lb = _count("leaderboard_snapshots")

    for _ in range(3):
        PulseService(test_session).get_pulse()

    assert _count("sp_adjustments") == before_sp, "PulseService escribió en sp_adjustments!"
    assert _count("leaderboard_snapshots") == before_lb, "PulseService escribió en leaderboard_snapshots!"


# ── WP-20: WIP canónico + semáforo ────────────────────────────────────────────


def test_wip_alondra_golden_case(test_session: Session):
    """CASO PM: Alondra (DB) 1 In Progress + 1 In Code + 4 In Review → WIP=2, Review=4.
    Auditado contra Jira 2026-06-09: YAP-979 In Progress, YAP-507 In Code, YAP-847/901/902/903 In Review.
    WIP=2 porque In Code cuenta igual que In Progress (estado activo de DB en Jira).
    Semáforo verde: WIP=2 < límite DB=5."""
    _seed_wip_limits(test_session)
    _project(test_session)
    alondra = _player(test_session, 100, "DB", "Alondra DB")
    _subtask(test_session, "YAP-A1", "In Progress", "DB", alondra.id)
    _subtask(test_session, "YAP-A2", "In Code", "DB", alondra.id)
    _subtask(test_session, "YAP-A3", "In Review", "DB", alondra.id)
    _subtask(test_session, "YAP-A4", "In Review", "DB", alondra.id)
    _subtask(test_session, "YAP-A5", "In Review", "DB", alondra.id)
    _subtask(test_session, "YAP-A6", "In Review", "DB", alondra.id)

    dd = PulseService(test_session).get_dev_drilldown(alondra.id)
    ws = dd.wip_summary

    assert ws.wip == 2, f"WIP esperado=2 (In Progress + In Code), obtenido={ws.wip}"
    assert ws.review == 4, f"Review esperado=4, obtenido={ws.review}"
    assert ws.qa == 0
    assert ws.semaphore == "green", f"WIP=2 vs límite DB=5 → verde, obtenido={ws.semaphore}"
    assert dd.total == 6, "total incluye todas las operativas (In Progress + In Code + In Review)"


def test_wip_in_code_counts_as_wip(test_session: Session):
    """'In Code' (estado activo de DB en Jira) cuenta como WIP igual que In Progress."""
    _seed_wip_limits(test_session)
    _project(test_session)
    dev = _player(test_session, 101, "DB", "Dev InCode")
    _subtask(test_session, "YAP-IC1", "In Progress", "DB", dev.id)
    _subtask(test_session, "YAP-IC2", "In Code", "DB", dev.id)
    _subtask(test_session, "YAP-IC3", "In Review", "DB", dev.id)

    dd = PulseService(test_session).get_dev_drilldown(dev.id)
    ws = dd.wip_summary
    assert ws.wip == 2, f"In Progress + In Code = 2, obtenido={ws.wip}"
    assert ws.review == 1


def test_wip_daniel_backlog_no_cuenta(test_session: Session):
    """CASO PM: dev con subtasks en Backlog → Backlog NO es WIP."""
    _seed_wip_limits(test_session)
    _project(test_session)
    daniel = _player(test_session, 102, "BE", "Daniel BE")
    for i in range(10):
        _subtask(test_session, f"YAP-DB{i}", "Backlog", "BE", daniel.id)
    _subtask(test_session, "YAP-DB10", "Ready for QA", "BE", daniel.id)

    dd = PulseService(test_session).get_dev_drilldown(daniel.id)
    ws = dd.wip_summary
    assert ws.wip == 0, f"Backlog no es WIP, obtenido={ws.wip}"
    assert ws.qa == 1
    assert dd.total == 1, "Backlog excluido del total operativo"


def test_semaphore_green_below_limit(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    dev = _player(test_session, 103, "BE", "DevGreen")  # límite BE=3
    _subtask(test_session, "YAP-G1", "In Progress", "BE", dev.id)
    _subtask(test_session, "YAP-G2", "In Progress", "BE", dev.id)

    dd = PulseService(test_session).get_dev_drilldown(dev.id)
    assert dd.wip_summary.wip == 2
    assert dd.wip_summary.wip_limit == 3
    assert dd.wip_summary.semaphore == "green"


def test_semaphore_yellow_at_limit(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    dev = _player(test_session, 104, "BE", "DevYellow")  # límite BE=3
    for i in range(3):
        _subtask(test_session, f"YAP-Y{i}", "In Progress", "BE", dev.id)

    dd = PulseService(test_session).get_dev_drilldown(dev.id)
    assert dd.wip_summary.wip == 3
    assert dd.wip_summary.semaphore == "yellow"


def test_semaphore_red_over_limit(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    dev = _player(test_session, 105, "BE", "DevRed")  # límite BE=3
    for i in range(4):
        _subtask(test_session, f"YAP-R{i}", "In Progress", "BE", dev.id)

    dd = PulseService(test_session).get_dev_drilldown(dev.id)
    assert dd.wip_summary.wip == 4
    assert dd.wip_summary.semaphore == "red"


def test_in_review_no_dispara_semaphore(test_session: Session):
    """Dev con muchos In Review y WIP=0 → verde. In Review no es WIP."""
    _seed_wip_limits(test_session)
    _project(test_session)
    dev = _player(test_session, 106, "BE", "DevReview")
    for i in range(10):
        _subtask(test_session, f"YAP-REV{i}", "In Review", "BE", dev.id)

    dd = PulseService(test_session).get_dev_drilldown(dev.id)
    assert dd.wip_summary.wip == 0
    assert dd.wip_summary.review == 10
    assert dd.wip_summary.semaphore == "green"


def test_area_card_wip_metrics(test_session: Session):
    """AreaCard expone wip_count, wip_limit y semáforo del área."""
    _seed_wip_limits(test_session)
    _project(test_session)
    dev1 = _player(test_session, 107, "FE", "FeDev1")  # límite FE=3
    dev2 = _player(test_session, 108, "FE", "FeDev2")
    # dev1: 2 WIP (verde), dev2: 1 WIP (verde) → área verde
    for i in range(2):
        _subtask(test_session, f"YAP-FE1{i}", "In Progress", "FE", dev1.id)
    _subtask(test_session, "YAP-FE20", "In Progress", "FE", dev2.id)
    _subtask(test_session, "YAP-FE21", "In Review", "FE", dev2.id)

    snap = PulseService(test_session).get_pulse()
    fe_card = next(c for c in snap.area_cards if c.area == "FE")

    assert fe_card.wip_count == 3
    assert fe_card.wip_limit == 3
    # Semáforo es per-dev: dev1=2 < límite=3 (verde), dev2=1 < límite=3 (verde) → área verde
    assert fe_card.semaphore == "green"
    assert fe_card.n_devs_over_limit == 0


def test_area_card_semaphore_red_if_dev_over_limit(test_session: Session):
    """Si algún dev del área supera su límite, el área sale roja."""
    _seed_wip_limits(test_session)
    _project(test_session)
    dev = _player(test_session, 109, "BE", "BEover")  # límite BE=3
    for i in range(4):
        _subtask(test_session, f"YAP-BEOV{i}", "In Progress", "BE", dev.id)

    snap = PulseService(test_session).get_pulse()
    be_card = next(c for c in snap.area_cards if c.area == "BE")
    assert be_card.semaphore == "red"
    assert be_card.n_devs_over_limit == 1
