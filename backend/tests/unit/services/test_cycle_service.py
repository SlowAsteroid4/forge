"""Tests unitarios para CycleService (UC-05 — cierre de ciclo + MVP semanal)."""

from __future__ import annotations

import pytest
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session

from forge.db.models.achievement import Achievement
from forge.db.models.achievement_unlock import AchievementUnlock
from forge.db.models.cycle import Cycle
from forge.db.models.leaderboard_snapshot import LeaderboardSnapshot
from forge.db.models.player import Player
from forge.db.models.sp_adjustment import SpAdjustment
from forge.db.models.subtask import Subtask
from forge.core.exceptions import NotFoundError, RuleViolationError
from forge.services.cycle_service import CycleService


# ── Helpers de fixtures ───────────────────────────────────────────────────


def _make_player(session: Session, *, name: str = "Dev Test", area: str = "BE", idx: int = 1) -> Player:
    p = Player(
        jira_account_id=f"jira-{idx}",
        display_name=name,
        email=f"dev{idx}@yapsi.com",
        area=area,
        employment_type="internal",
        is_lead=False,
        is_active=True,
    )
    session.add(p)
    session.flush()
    return p


def _make_cycle(
    session: Session,
    *,
    status: str = "active",
    iso_year: int = 2026,
    iso_week: int = 22,
) -> Cycle:
    c = Cycle(
        name=f"Ciclo {iso_year}-W{iso_week:02d}",
        iso_year=iso_year,
        iso_week=iso_week,
        start_date=date(2026, 5, 25),
        end_date=date(2026, 5, 29),
        status=status,
    )
    session.add(c)
    session.flush()
    return c


def _make_subtask(
    session: Session,
    *,
    jira_key: str,
    cycle_id: int,
    player_id: int,
    sp_final: float | None = 10.0,
    cp: int = 3,
    status: str = "Done",
) -> Subtask:
    st = Subtask(
        jira_key=jira_key,
        issue_type="Sub-task",
        area="BE",
        summary="Test subtask",
        status=status,
        assignee_player_id=player_id,
        cycle_id=cycle_id,
        sp_final=sp_final,
        cp=cp,
    )
    session.add(st)
    session.flush()
    return st


def _make_ach04(session: Session) -> Achievement:
    a = Achievement(
        code="ACH04",
        name="Primer MVP",
        description="Obtuviste el reconocimiento de MVP por primera vez.",
        rarity="rare",
        sp_bonus=0,
        unlock_condition_code="mvp_weekly_first",
        is_active=True,
    )
    session.add(a)
    session.flush()
    return a


def _make_planned_cycle(session: Session, iso_week: int = 23) -> Cycle:
    c = Cycle(
        name=f"Ciclo 2026-W{iso_week:02d}",
        iso_year=2026,
        iso_week=iso_week,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 5),
        status="planned",
    )
    session.add(c)
    session.flush()
    return c


# ── Tests: get_mvp_candidates ─────────────────────────────────────────────


def test_mvp_candidates_ranked_by_sp(test_session: Session) -> None:
    """Candidatos se ordenan de mayor a menor SP."""
    cycle = _make_cycle(test_session)
    p1 = _make_player(test_session, name="Alto SP", idx=1)
    p2 = _make_player(test_session, name="Bajo SP", idx=2)
    _make_subtask(test_session, jira_key="YAP-1", cycle_id=cycle.id, player_id=p1.id, sp_final=20.0)
    _make_subtask(test_session, jira_key="YAP-2", cycle_id=cycle.id, player_id=p2.id, sp_final=5.0)

    svc = CycleService(test_session)
    candidates = svc.get_mvp_candidates(cycle.id)

    assert len(candidates) == 2
    assert candidates[0]["player_id"] == p1.id
    assert candidates[0]["sp_total"] == 20.0
    assert candidates[1]["player_id"] == p2.id


def test_mvp_candidates_empty_cycle(test_session: Session) -> None:
    """Ciclo sin subtasks Done retorna lista vacía."""
    cycle = _make_cycle(test_session)
    svc = CycleService(test_session)
    assert svc.get_mvp_candidates(cycle.id) == []


def test_mvp_candidates_closed_cycle_raises(test_session: Session) -> None:
    """No se pueden pedir candidatos de un ciclo ya cerrado."""
    cycle = _make_cycle(test_session, status="closed")
    svc = CycleService(test_session)
    with pytest.raises(RuleViolationError):
        svc.get_mvp_candidates(cycle.id)


# ── Tests: get_close_summary ──────────────────────────────────────────────


def test_close_summary_can_close_true(test_session: Session) -> None:
    """Ciclo con todas Done con sp_final → can_close=True."""
    cycle = _make_cycle(test_session)
    player = _make_player(test_session, idx=1)
    _make_subtask(test_session, jira_key="YAP-10", cycle_id=cycle.id, player_id=player.id, sp_final=8.0)

    svc = CycleService(test_session)
    summary = svc.get_close_summary(cycle.id)

    assert summary["can_close"] is True
    assert summary["blocking_errors"] == []
    assert summary["kpis"]["subtasks_done"] == 1
    assert summary["kpis"]["sp_generated"] == 8.0


def test_close_summary_blocking_if_done_without_sp(test_session: Session) -> None:
    """Subtask Done con sp_final=None genera error bloqueante."""
    cycle = _make_cycle(test_session)
    player = _make_player(test_session, idx=1)
    _make_subtask(test_session, jira_key="YAP-11", cycle_id=cycle.id, player_id=player.id, sp_final=None)

    svc = CycleService(test_session)
    summary = svc.get_close_summary(cycle.id)

    assert summary["can_close"] is False
    assert len(summary["blocking_errors"]) == 1


# ── Tests: close_cycle ────────────────────────────────────────────────────


def test_close_cycle_applies_mvp_plus5(test_session: Session) -> None:
    """close_cycle inserta SpAdjustment +5 para el MVP."""
    cycle = _make_cycle(test_session)
    _make_ach04(test_session)
    player = _make_player(test_session, idx=1)
    _make_planned_cycle(test_session)
    _make_subtask(test_session, jira_key="YAP-20", cycle_id=cycle.id, player_id=player.id, sp_final=12.0)

    svc = CycleService(test_session)
    svc.close_cycle(
        cycle_id=cycle.id,
        mvp_player_id=player.id,
        mvp_reason="Excelente trabajo durante toda la semana con entregas de calidad",
        closed_by=player.id,
    )
    test_session.flush()

    adj = test_session.query(SpAdjustment).filter_by(
        player_id=player.id, adjustment_type="mvp_bonus"
    ).first()
    assert adj is not None
    assert adj.amount_sp == 5.0
    assert adj.catalog_code == "B17"
    assert adj.cycle_id == cycle.id


def test_close_cycle_unlocks_ach04_first_time(test_session: Session) -> None:
    """ACH04 se desbloquea en el primer MVP."""
    cycle = _make_cycle(test_session)
    _make_ach04(test_session)
    player = _make_player(test_session, idx=1)
    _make_planned_cycle(test_session)
    _make_subtask(test_session, jira_key="YAP-30", cycle_id=cycle.id, player_id=player.id, sp_final=5.0)

    svc = CycleService(test_session)
    svc.close_cycle(
        cycle_id=cycle.id,
        mvp_player_id=player.id,
        mvp_reason="Muy buena semana con entregas consistentes y de alta calidad",
        closed_by=player.id,
    )
    test_session.flush()

    unlock = test_session.query(AchievementUnlock).filter_by(
        player_id=player.id, achievement_code="ACH04"
    ).first()
    assert unlock is not None


def test_close_cycle_generates_weekly_snapshot(test_session: Session) -> None:
    """close_cycle genera LeaderboardSnapshot period_type='weekly'."""
    cycle = _make_cycle(test_session)
    _make_ach04(test_session)
    player = _make_player(test_session, idx=1)
    _make_planned_cycle(test_session)
    _make_subtask(test_session, jira_key="YAP-40", cycle_id=cycle.id, player_id=player.id, sp_final=7.0)

    svc = CycleService(test_session)
    svc.close_cycle(
        cycle_id=cycle.id,
        mvp_player_id=player.id,
        mvp_reason="Gran desempeño técnico y aporte al equipo durante el ciclo completo",
        closed_by=player.id,
    )
    test_session.flush()

    snap = test_session.query(LeaderboardSnapshot).filter_by(
        cycle_id=cycle.id, period_type="weekly"
    ).first()
    assert snap is not None
    assert snap.rank == 1
    assert snap.sp_total == 7.0


def test_close_cycle_activates_next_planned(test_session: Session) -> None:
    """close_cycle activa el siguiente ciclo 'planned'."""
    cycle = _make_cycle(test_session)
    _make_ach04(test_session)
    player = _make_player(test_session, idx=1)
    next_cycle = _make_planned_cycle(test_session, iso_week=23)
    _make_subtask(test_session, jira_key="YAP-50", cycle_id=cycle.id, player_id=player.id, sp_final=3.0)

    svc = CycleService(test_session)
    svc.close_cycle(
        cycle_id=cycle.id,
        mvp_player_id=player.id,
        mvp_reason="Buen ritmo de trabajo con entregas a tiempo y sin bugs detectados",
        closed_by=player.id,
    )
    test_session.flush()

    test_session.refresh(next_cycle)
    assert next_cycle.status == "active"


def test_close_cycle_validates_mvp_reason_min_length(test_session: Session) -> None:
    """mvp_reason < 20 chars lanza RuleViolationError."""
    cycle = _make_cycle(test_session)
    player = _make_player(test_session, idx=1)

    svc = CycleService(test_session)
    with pytest.raises(RuleViolationError, match="caracteres"):
        svc.close_cycle(
            cycle_id=cycle.id,
            mvp_player_id=player.id,
            mvp_reason="Corto",
            closed_by=player.id,
        )


def test_close_cycle_blocks_if_done_without_sp(test_session: Session) -> None:
    """close_cycle rechaza si hay subtasks Done sin sp_final."""
    cycle = _make_cycle(test_session)
    player = _make_player(test_session, idx=1)
    _make_subtask(
        test_session, jira_key="YAP-60", cycle_id=cycle.id, player_id=player.id, sp_final=None
    )

    svc = CycleService(test_session)
    with pytest.raises(RuleViolationError):
        svc.close_cycle(
            cycle_id=cycle.id,
            mvp_player_id=player.id,
            mvp_reason="Excelente semana con todos los entregables completados a tiempo",
            closed_by=player.id,
        )


def test_cannot_close_already_closed_cycle(test_session: Session) -> None:
    """No se puede cerrar un ciclo que ya está 'closed'."""
    cycle = _make_cycle(test_session, status="closed")
    player = _make_player(test_session, idx=1)

    svc = CycleService(test_session)
    with pytest.raises(RuleViolationError, match="active"):
        svc.close_cycle(
            cycle_id=cycle.id,
            mvp_player_id=player.id,
            mvp_reason="Excelente semana con todos los entregables completados a tiempo",
            closed_by=player.id,
        )


# ── Tests: edit_mvp ───────────────────────────────────────────────────────


def test_edit_mvp_within_window_reverts_and_reapplies(test_session: Session) -> None:
    """edit_mvp dentro de ventana inserta reversal y nuevo bonus."""
    cycle = _make_cycle(test_session, status="closed")
    cycle.closed_at = datetime.utcnow()
    cycle.mvp_player_id = None
    _make_ach04(test_session)
    old_player = _make_player(test_session, name="Old MVP", idx=1)
    new_player = _make_player(test_session, name="New MVP", idx=2)
    cycle.mvp_player_id = old_player.id
    cycle.mvp_reason = "Razon original larga para cumplir los veinte caracteres"
    test_session.flush()

    svc = CycleService(test_session)
    svc.edit_mvp(
        cycle_id=cycle.id,
        new_mvp_player_id=new_player.id,
        reason="Nueva razon suficientemente larga para pasar la validacion del sistema",
        edited_by=old_player.id,
    )
    test_session.flush()

    reversal = test_session.query(SpAdjustment).filter_by(
        player_id=old_player.id, adjustment_type="mvp_reversal"
    ).first()
    assert reversal is not None
    assert reversal.amount_sp == 5.0

    new_bonus = test_session.query(SpAdjustment).filter_by(
        player_id=new_player.id, adjustment_type="mvp_bonus"
    ).first()
    assert new_bonus is not None
    assert new_bonus.amount_sp == 5.0


def test_edit_mvp_outside_window_raises(test_session: Session) -> None:
    """edit_mvp después de 24h hábiles lanza RuleViolationError."""
    cycle = _make_cycle(test_session, status="closed")
    # Simular cierre hace 10 días (>> 24h hábiles)
    cycle.closed_at = datetime.utcnow() - timedelta(days=10)
    player = _make_player(test_session, idx=1)
    cycle.mvp_player_id = player.id
    test_session.flush()

    new_player = _make_player(test_session, name="New MVP", idx=2)

    svc = CycleService(test_session)
    with pytest.raises(RuleViolationError, match="ventana"):
        svc.edit_mvp(
            cycle_id=cycle.id,
            new_mvp_player_id=new_player.id,
            reason="Razon suficientemente larga para pasar la validacion de longitud minima",
            edited_by=player.id,
        )


def test_edit_mvp_ach04_not_duplicated(test_session: Session) -> None:
    """Si el nuevo MVP ya tiene ACH04, no se duplica el unlock."""
    cycle = _make_cycle(test_session, status="closed")
    cycle.closed_at = datetime.utcnow()
    ach = _make_ach04(test_session)
    player = _make_player(test_session, name="Old MVP", idx=1)
    new_player = _make_player(test_session, name="New MVP", idx=2)
    cycle.mvp_player_id = player.id
    cycle.mvp_reason = "Razon original suficientemente larga para la validacion"

    # Pre-unlock ACH04 para new_player
    existing = AchievementUnlock(
        player_id=new_player.id,
        achievement_code="ACH04",
        unlocked_at=datetime.utcnow(),
    )
    test_session.add(existing)
    test_session.flush()

    svc = CycleService(test_session)
    svc.edit_mvp(
        cycle_id=cycle.id,
        new_mvp_player_id=new_player.id,
        reason="Nueva razon suficientemente larga para pasar la validacion del sistema",
        edited_by=player.id,
    )
    test_session.flush()

    unlocks = (
        test_session.query(AchievementUnlock)
        .filter_by(player_id=new_player.id, achievement_code="ACH04")
        .all()
    )
    assert len(unlocks) == 1
