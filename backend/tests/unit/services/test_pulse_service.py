"""Tests para PulseService (UC-16) — Pulso Operativo."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import text

from forge.db.models.area_wip_limit import AreaWipLimit
from forge.db.models.player import Player
from forge.db.models.project import Project
from forge.db.models.subtask import Subtask
from forge.services.pulse_service import _semaforo, PulseService


# ── Factories ─────────────────────────────────────────────────────────────────


def _seed_wip_limits(session: Session) -> None:
    """Sembrar catálogo WIP vía ORM (respeta created_at del mixin base)."""
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


def _subtask(
    session: Session,
    key: str,
    status: str,
    area: str = "BE",
    player_id: int | None = None,
    project_code: str = "YAP",
    created_days_ago: int = 1,
    changelog_entries: list[dict] | None = None,
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
        issue_type="Sub-task",
        raw_changelog=json.dumps(cl_data),
    )
    # Forzar created_at más antiguo para tests de aging
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


# ── Tests: _semaforo ──────────────────────────────────────────────────────────


def test_semaforo_verde_bajo():
    assert _semaforo(0) == "verde"
    assert _semaforo(50) == "verde"
    assert _semaforo(79.9) == "verde"


def test_semaforo_amarillo():
    assert _semaforo(80) == "amarillo"
    assert _semaforo(100) == "amarillo"


def test_semaforo_rojo():
    assert _semaforo(100.1) == "rojo"
    assert _semaforo(150) == "rojo"


# ── Tests: WIP por área ───────────────────────────────────────────────────────


def test_wip_area_verde(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 1, "BE", "Dev1")
    _subtask(test_session, "YAP-1", "In Progress", "BE", p.id)
    _subtask(test_session, "YAP-2", "In Review", "BE", p.id)

    snap = PulseService(test_session).get_pulse()
    be = next(c for c in snap.wip_by_area if c.area == "BE")
    assert be.wip_actual == 2
    assert be.semaforo == "verde"


def test_wip_area_amarillo(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 2, "BE", "Dev2")
    _subtask(test_session, "YAP-3", "In Progress", "BE", p.id)
    _subtask(test_session, "YAP-4", "In Review", "BE", p.id)
    _subtask(test_session, "YAP-5", "Active", "BE", p.id)

    snap = PulseService(test_session).get_pulse()
    be = next(c for c in snap.wip_by_area if c.area == "BE")
    assert be.wip_actual == 3
    assert be.semaforo == "amarillo"


def test_wip_area_rojo(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 3, "FE", "Dev3")
    for i in range(4):
        _subtask(test_session, f"YAP-{10+i}", "In Progress", "FE", p.id)

    snap = PulseService(test_session).get_pulse()
    fe = next(c for c in snap.wip_by_area if c.area == "FE")
    assert fe.wip_actual == 4
    assert fe.semaforo == "rojo"


def test_qa_excluida_del_wip(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 4, "QA", "Edgar")
    for i in range(6):
        _subtask(test_session, f"YAP-Q{i}", "In QA", "QA", p.id)

    snap = PulseService(test_session).get_pulse()
    areas = [c.area for c in snap.wip_by_area]
    assert "QA" not in areas


# ── Tests: Bloqueos ───────────────────────────────────────────────────────────


def test_bloqueo_critico_mas_8h(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 5, "BE", "Bloq")
    # 48 calendar hours → garantiza >=8 horas hábiles incluso cruzando fin de semana
    entries = [_status_changelog_entry("In Progress", "Blocked", hours_ago=48)]
    _subtask(test_session, "YAP-BLK", "Blocked", "BE", p.id, changelog_entries=entries)

    snap = PulseService(test_session).get_pulse()
    assert len(snap.blocks) == 1
    assert snap.blocks[0].es_critico is True
    assert snap.blocks[0].horas_bloqueado >= 8.0


def test_bloqueo_no_critico_menos_8h(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 6, "BE", "Bloq2")
    entries = [_status_changelog_entry("In Progress", "Blocked", hours_ago=3)]
    _subtask(test_session, "YAP-BLK2", "Blocked", "BE", p.id, changelog_entries=entries)

    snap = PulseService(test_session).get_pulse()
    assert snap.blocks[0].es_critico is False


def test_block_reason_siempre_null(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 7, "BE", "Dev7")
    _subtask(test_session, "YAP-NR", "Blocked", "BE", p.id)

    snap = PulseService(test_session).get_pulse()
    assert snap.blocks[0].block_reason is None


# ── Tests: Aging ──────────────────────────────────────────────────────────────


def test_aging_critico_detectado(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 8, "BE", "Anciano")
    # 6 semanas atrás = garantiza >5 días hábiles en estado actual
    entries = [_status_changelog_entry("Ready", "In Progress", hours_ago=24 * 42)]
    _subtask(test_session, "YAP-OLD", "In Progress", "BE", p.id,
             created_days_ago=42, changelog_entries=entries)

    snap = PulseService(test_session).get_pulse()
    keys = [a.jira_key for a in snap.aging_critical]
    assert "YAP-OLD" in keys


def test_aging_no_critico_1_dia(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 9, "FE", "Nuevo")
    entries = [_status_changelog_entry("Ready", "In Progress", hours_ago=4)]
    _subtask(test_session, "YAP-NEW", "In Progress", "FE", p.id,
             created_days_ago=1, changelog_entries=entries)

    snap = PulseService(test_session).get_pulse()
    keys = [a.jira_key for a in snap.aging_critical]
    assert "YAP-NEW" not in keys


# ── Tests: Filtros ────────────────────────────────────────────────────────────


def test_filtro_por_area(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p_be = _player(test_session, 10, "BE", "DevBE")
    p_fe = _player(test_session, 11, "FE", "DevFE")
    _subtask(test_session, "YAP-F1", "In Progress", "BE", p_be.id)
    _subtask(test_session, "YAP-F2", "In Review", "FE", p_fe.id)

    snap = PulseService(test_session).get_pulse(areas=["BE"])
    assert snap.globals.activas == 1
    assert all(c.area == "BE" for c in snap.wip_by_area)


def test_filtro_por_project_code(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p = _player(test_session, 12, "BE", "DevP")
    _subtask(test_session, "YAP-P1", "In Progress", "BE", p.id, project_code="YAP")

    snap_yap = PulseService(test_session).get_pulse(project_code="YAP")
    assert snap_yap.globals.activas >= 1

    snap_xxx = PulseService(test_session).get_pulse(project_code="XXX")
    assert snap_xxx.globals.activas == 0


def test_filtro_por_player_id(test_session: Session):
    _seed_wip_limits(test_session)
    _project(test_session)
    p1 = _player(test_session, 13, "BE", "Uno")
    p2 = _player(test_session, 14, "BE", "Dos")
    _subtask(test_session, "YAP-PL1", "In Progress", "BE", p1.id)
    _subtask(test_session, "YAP-PL2", "In Review", "BE", p2.id)

    snap = PulseService(test_session).get_pulse(player_id=p1.id)
    assert snap.globals.activas == 1


# ── Test anti-regresión: 0 escrituras ────────────────────────────────────────


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
