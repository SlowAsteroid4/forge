"""Tests unitarios para MonthlyMvpService (UC-17 — cierre mensual y MVP del Mes)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError, RuleViolationError
from forge.db.models.achievement import Achievement
from forge.db.models.achievement_unlock import AchievementUnlock
from forge.db.models.cycle import Cycle
from forge.db.models.mvp_monthly import MvpMonthly
from forge.db.models.player import Player
from forge.db.models.sp_adjustment import SpAdjustment
from forge.db.models.subtask import Subtask
from forge.services.monthly_mvp_service import MonthlyMvpService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _player(session: Session, *, idx: int = 1, name: str | None = None) -> Player:
    p = Player(
        jira_account_id=f"jira-{idx}",
        display_name=name or f"Dev {idx}",
        email=f"dev{idx}@yapsi.com",
        area="BE",
        employment_type="internal",
        is_lead=False,
        is_active=True,
    )
    session.add(p)
    session.flush()
    return p


def _cycle(
    session: Session,
    *,
    year: int = 2026,
    month_start: int = 5,
    week: int = 22,
    status: str = "closed",
    mvp_player_id: int | None = None,
    day_start: int = 25,
) -> Cycle:
    c = Cycle(
        name=f"Ciclo {year}-W{week:02d}",
        iso_year=year,
        iso_week=week,
        start_date=date(year, month_start, day_start),
        end_date=date(year, month_start, day_start + 4),
        status=status,
        mvp_player_id=mvp_player_id,
    )
    session.add(c)
    session.flush()
    return c


def _ach04(session: Session) -> Achievement:
    ach = Achievement(
        code="ACH04",
        name="Primer MVP",
        description="Primer MVP del ciclo",
        rarity="epic",
        sp_bonus=0,
        unlock_condition_code="mvp_weekly",
    )
    session.add(ach)
    session.flush()
    return ach


def _admin(session: Session) -> Player:
    return _player(session, idx=99, name="Admin")


def _four_closed_cycles_with_mvps(
    session: Session, *, mvp_player_id: int, extra_player_id: int | None = None
) -> list[Cycle]:
    """Fixture AC-17.6: 4 ciclos closed del mismo mes, todos con MVP."""
    days = [4, 11, 18, 25]
    mvp_ids = [mvp_player_id, extra_player_id or mvp_player_id, mvp_player_id, mvp_player_id]
    cycles = []
    for week, day, pid in zip([19, 20, 21, 22], days, mvp_ids):
        cycles.append(
            _cycle(session, week=week, day_start=day, status="closed", mvp_player_id=pid)
        )
    return cycles


# ── list_candidates ───────────────────────────────────────────────────────────


def test_list_candidates_returns_weekly_mvps(test_session: Session) -> None:
    p1 = _player(test_session, idx=1)
    p2 = _player(test_session, idx=2)

    _cycle(test_session, week=19, day_start=4, status="archived", mvp_player_id=p1.id)
    _cycle(test_session, week=20, day_start=11, status="archived", mvp_player_id=p2.id)
    _cycle(test_session, week=21, day_start=18, status="archived", mvp_player_id=p1.id)
    _cycle(test_session, week=22, day_start=25, status="closed", mvp_player_id=p1.id)

    svc = MonthlyMvpService(test_session)
    candidates = svc.list_candidates(2026, 5)

    assert len(candidates) == 2
    player_ids = {c["player_id"] for c in candidates}
    assert p1.id in player_ids
    assert p2.id in player_ids


def test_list_candidates_no_cycles_raises(test_session: Session) -> None:
    svc = MonthlyMvpService(test_session)
    with pytest.raises(NotFoundError):
        svc.list_candidates(2099, 1)


def test_list_candidates_no_mvp_returns_empty(test_session: Session) -> None:
    _cycle(test_session, week=22, day_start=25, status="closed", mvp_player_id=None)
    svc = MonthlyMvpService(test_session)
    candidates = svc.list_candidates(2026, 5)
    assert candidates == []


# ── close_month ───────────────────────────────────────────────────────────────


def test_close_month_creates_record_and_adjustment(test_session: Session) -> None:
    p = _player(test_session, idx=1)
    admin = _admin(test_session)
    _four_closed_cycles_with_mvps(test_session, mvp_player_id=p.id)
    _ach04(test_session)

    svc = MonthlyMvpService(test_session)
    record = svc.close_month(2026, 5, p.id, "Excelente trabajo durante todo el mes de mayo con 4 ciclos cerrados", admin.id)

    assert record.year == 2026
    assert record.month == 5
    assert record.player_id == p.id
    assert record.sp_reward == 10

    adj = test_session.query(SpAdjustment).filter_by(
        player_id=p.id, catalog_code="B17M", adjustment_type="mvp_bonus"
    ).first()
    assert adj is not None
    assert adj.amount_sp == 10.0


def test_close_month_requires_4_closed_cycles(test_session: Session) -> None:
    """AC-17.6: mes (que no es el primero) con solo 3 ciclos cerrados con MVP es rechazado."""
    p = _player(test_session, idx=1)
    admin = _admin(test_session)
    # Ciclo con MVP en un mes previo (abril) para que mayo NO sea el primer mes de la
    # cadencia y aplique el gate pleno de >=4 (no la excepción de primer mes).
    _cycle(test_session, month_start=4, week=14, day_start=6, status="closed", mvp_player_id=p.id)
    # Solo 3 ciclos en mayo (no llegan a 4)
    for week, day in [(19, 4), (20, 11), (21, 18)]:
        _cycle(test_session, week=week, day_start=day, status="closed", mvp_player_id=p.id)
    _ach04(test_session)

    svc = MonthlyMvpService(test_session)
    with pytest.raises(RuleViolationError) as exc_info:
        svc.close_month(2026, 5, p.id, "Intentando cerrar con solo 3 ciclos en lugar de 4 requeridos", admin.id)

    errors = exc_info.value.details.get("blocking_errors", [])
    assert any("se requieren 4" in e for e in errors)


def test_close_month_first_month_exception_allows_one_cycle(test_session: Session) -> None:
    """Excepción de primer mes: el primer mes con MVP semanal puede cerrar con <4 ciclos."""
    p = _player(test_session, idx=1)
    admin = _admin(test_session)
    # Único mes con MVP en toda la BD -> mayo es el primer mes de la cadencia.
    _cycle(test_session, week=22, day_start=25, status="closed", mvp_player_id=p.id)
    _ach04(test_session)

    svc = MonthlyMvpService(test_session)
    summary = svc.get_month_close_summary(2026, 5)
    assert summary["can_close"] is True
    assert any("primer mes" in w.lower() for w in summary["warnings"])

    record = svc.close_month(
        2026, 5, p.id, "Primer mes de la cadencia mensual: cierre con un solo ciclo cerrado", admin.id
    )
    assert record.player_id == p.id
    assert record.sp_reward == 10


def test_close_month_blocking_rule_non_weekly_mvp(test_session: Session) -> None:
    """REGLA BLOQUEANTE AC-17.4: elegir un player que no fue MVP semanal debe lanzar error."""
    p_mvp = _player(test_session, idx=1)
    p_non_mvp = _player(test_session, idx=2)
    admin = _admin(test_session)
    _four_closed_cycles_with_mvps(test_session, mvp_player_id=p_mvp.id)

    svc = MonthlyMvpService(test_session)
    with pytest.raises(RuleViolationError) as exc_info:
        svc.close_month(2026, 5, p_non_mvp.id, "Este jugador no fue MVP semanal nunca en el mes de mayo", admin.id)

    assert "AC-17.4" in str(exc_info.value) or "MVP semanal" in str(exc_info.value)


def test_close_month_unlocks_ach04_first_time(test_session: Session) -> None:
    p = _player(test_session, idx=1)
    admin = _admin(test_session)
    _four_closed_cycles_with_mvps(test_session, mvp_player_id=p.id)
    _ach04(test_session)

    svc = MonthlyMvpService(test_session)
    svc.close_month(2026, 5, p.id, "Excelente trabajo durante todo el mes de mayo con 4 ciclos cerrados y validados", admin.id)

    unlock = test_session.query(AchievementUnlock).filter_by(
        player_id=p.id, achievement_code="ACH04"
    ).first()
    assert unlock is not None


def test_close_month_no_duplicate_ach04(test_session: Session) -> None:
    """ACH04 no se desbloquea si el player ya lo tiene (ej. por MVP semanal previo)."""
    p = _player(test_session, idx=1)
    admin = _admin(test_session)
    _four_closed_cycles_with_mvps(test_session, mvp_player_id=p.id)
    _ach04(test_session)

    existing_unlock = AchievementUnlock(
        player_id=p.id,
        achievement_code="ACH04",
        unlocked_at=datetime.utcnow(),
    )
    test_session.add(existing_unlock)
    test_session.flush()

    svc = MonthlyMvpService(test_session)
    svc.close_month(2026, 5, p.id, "Excelente trabajo durante todo el mes de mayo con 4 ciclos cerrados y validados", admin.id)

    unlocks = test_session.query(AchievementUnlock).filter_by(
        player_id=p.id, achievement_code="ACH04"
    ).all()
    assert len(unlocks) == 1  # no duplicó


def test_close_month_duplicate_rejected(test_session: Session) -> None:
    p = _player(test_session, idx=1)
    admin = _admin(test_session)
    _four_closed_cycles_with_mvps(test_session, mvp_player_id=p.id)
    _ach04(test_session)

    svc = MonthlyMvpService(test_session)
    svc.close_month(2026, 5, p.id, "Excelente trabajo durante todo el mes de mayo con 4 ciclos cerrados", admin.id)

    with pytest.raises(RuleViolationError):
        svc.close_month(2026, 5, p.id, "Intento de cierre duplicado del mes de mayo con 4 ciclos cerrados nuevamente", admin.id)


def test_close_month_reason_too_short(test_session: Session) -> None:
    p = _player(test_session, idx=1)
    admin = _admin(test_session)
    _four_closed_cycles_with_mvps(test_session, mvp_player_id=p.id)

    svc = MonthlyMvpService(test_session)
    with pytest.raises(RuleViolationError):
        svc.close_month(2026, 5, p.id, "Corto", admin.id)


# ── edit_monthly_mvp ──────────────────────────────────────────────────────────


def test_edit_monthly_mvp_reversal_append_only(test_session: Session) -> None:
    """Edición hace INSERT -10 al anterior + INSERT +10 al nuevo (append-only)."""
    p1 = _player(test_session, idx=1)
    p2 = _player(test_session, idx=2)
    admin = _admin(test_session)
    _four_closed_cycles_with_mvps(test_session, mvp_player_id=p1.id, extra_player_id=p2.id)
    _ach04(test_session)

    svc = MonthlyMvpService(test_session)
    svc.close_month(2026, 5, p1.id, "Excelente trabajo durante todo el mes de mayo en el proyecto BE con 4 ciclos", admin.id)

    svc.edit_monthly_mvp(2026, 5, p2.id, "Corregimos: p2 fue mejor MVP del mes de mayo en este ciclo cerrado", admin.id)

    # Reversal -10 al anterior (p1)
    reversal = test_session.query(SpAdjustment).filter_by(
        player_id=p1.id, adjustment_type="mvp_reversal", catalog_code="B17M"
    ).first()
    assert reversal is not None
    assert reversal.amount_sp == 10.0

    # Nuevo +10 al nuevo (p2)
    new_adj = test_session.query(SpAdjustment).filter_by(
        player_id=p2.id, adjustment_type="mvp_bonus", catalog_code="B17M"
    ).all()
    assert len(new_adj) == 1
    assert new_adj[0].amount_sp == 10.0


def test_edit_monthly_mvp_expired_window(test_session: Session) -> None:
    """Edición después de 72h hábiles es rechazada."""
    p = _player(test_session, idx=1)
    admin = _admin(test_session)
    _four_closed_cycles_with_mvps(test_session, mvp_player_id=p.id)
    _ach04(test_session)

    svc = MonthlyMvpService(test_session)
    svc.close_month(2026, 5, p.id, "Excelente trabajo durante todo el mes de mayo en el proyecto BE con 4 ciclos", admin.id)

    # Forzar assigned_at en el pasado (>72h hábiles = ~9 días calendario)
    record = test_session.query(MvpMonthly).filter_by(year=2026, month=5).first()
    assert record is not None
    record.assigned_at = datetime(2026, 1, 1)  # muy en el pasado
    test_session.flush()

    with pytest.raises(RuleViolationError) as exc_info:
        svc.edit_monthly_mvp(2026, 5, p.id, "Razón de edición expirada más de 72 horas hábiles", admin.id)

    assert "expiró" in str(exc_info.value) or "expirad" in str(exc_info.value)


def test_edit_monthly_mvp_blocking_rule(test_session: Session) -> None:
    """No se puede reasignar a un player que no fue MVP semanal."""
    p_mvp = _player(test_session, idx=1)
    p_other = _player(test_session, idx=2)
    admin = _admin(test_session)
    _four_closed_cycles_with_mvps(test_session, mvp_player_id=p_mvp.id)
    _ach04(test_session)

    svc = MonthlyMvpService(test_session)
    svc.close_month(2026, 5, p_mvp.id, "Excelente trabajo durante todo el mes de mayo en el proyecto BE con 4 ciclos", admin.id)

    with pytest.raises(RuleViolationError):
        svc.edit_monthly_mvp(2026, 5, p_other.id, "Razón correcta pero player no fue MVP semanal del mes de mayo", admin.id)


# ── get_history ───────────────────────────────────────────────────────────────


def test_get_history_returns_records(test_session: Session) -> None:
    p = _player(test_session, idx=1)
    admin = _admin(test_session)
    _four_closed_cycles_with_mvps(test_session, mvp_player_id=p.id)
    _ach04(test_session)

    svc = MonthlyMvpService(test_session)
    svc.close_month(2026, 5, p.id, "Excelente trabajo durante todo el mes de mayo en el proyecto backend con 4 ciclos", admin.id)

    history = svc.get_history()
    assert len(history) == 1
    assert history[0]["period_label"] == "2026-05"
    assert history[0]["player_id"] == p.id
    assert history[0]["sp_reward"] == 10


# ── inmutabilidad CP ──────────────────────────────────────────────────────────


def test_close_month_does_not_touch_cp(test_session: Session) -> None:
    """Cerrar el mes NO modifica cp de ninguna subtask."""
    p = _player(test_session, idx=1)
    admin = _admin(test_session)
    cycles = _four_closed_cycles_with_mvps(test_session, mvp_player_id=p.id)
    c = cycles[0]

    st = Subtask(
        jira_key="YAP-999",
        issue_type="Sub-task",
        area="BE",
        summary="Test subtask",
        status="Done",
        assignee_player_id=p.id,
        cycle_id=c.id,
        sp_final=10.0,
        cp=5,
        cp_approved_at=datetime.utcnow(),
    )
    test_session.add(st)
    test_session.flush()

    _ach04(test_session)

    svc = MonthlyMvpService(test_session)
    svc.close_month(2026, 5, p.id, "Excelente trabajo durante todo el mes de mayo en el proyecto backend con 4 ciclos", admin.id)

    # CP no cambió
    test_session.refresh(st)
    assert st.cp == 5
    assert st.cp_approved_at is not None
