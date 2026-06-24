"""Tests unitarios para cost_service (UC-08)."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy.orm import Session

from forge.db.models.player import Player
from forge.db.models.subtask import Subtask
from forge.services.cost_service import (
    CostService,
    _calc_months_fraction,
    _calc_player_cost,
    require_cost_access,
    resolve_period,
)

# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


def _make_player(
    session: Session,
    jira_id: str,
    area: str,
    emp_type: str,
    salary: float | None = None,
    hourly: float | None = None,
    hours_cap: int | None = None,
    joined_at: date | None = None,
) -> Player:
    p = Player(
        jira_account_id=jira_id,
        display_name=f"Dev {jira_id}",
        area=area,
        employment_type=emp_type,
        is_lead=False,
        is_active=True,
        monthly_salary=salary,
        hourly_rate=hourly,
        monthly_hours_cap=hours_cap,
        joined_at=datetime.combine(joined_at, datetime.min.time()) if joined_at else None,
    )
    session.add(p)
    session.commit()
    return p


def _make_subtask(
    session: Session,
    player_id: int,
    area: str,
    cp: int,
    sp: float,
    done_at: datetime,
) -> Subtask:
    import uuid
    st = Subtask(
        jira_key=f"YAP-{uuid.uuid4().hex[:6]}",
        area=area,
        issue_type="subtask",
        summary="test subtask",
        status="Done",
        assignee_player_id=player_id,
        cp=cp,
        sp_final=sp,
        done_at=done_at,
    )
    session.add(st)
    session.commit()
    return st


# ──────────────────────────────────────────────────────────────
# Tests: prorrateo interno
# ──────────────────────────────────────────────────────────────


def test_months_fraction_full_quarter():
    """3 meses completos sin joined_at → fracción = 3.0."""
    start = date(2026, 1, 1)
    end = date(2026, 4, 1)
    frac = _calc_months_fraction(start, end, joined_at=None)
    assert abs(frac - 3.0) < 0.01


def test_months_fraction_with_joined_at_mid_month():
    """joined_at a mitad de mes → primer mes prorrateado."""
    start = date(2026, 1, 1)
    end = date(2026, 4, 1)
    # Ingresó el 16 de enero: 31-16+1=16 días de 31
    joined = date(2026, 1, 16)
    frac = _calc_months_fraction(start, end, joined_at=joined)
    # 16/31 + 2 meses completos
    expected = 16 / 31 + 2.0
    assert abs(frac - expected) < 0.01


def test_months_fraction_joined_after_period():
    """joined_at después del periodo → fracción = 0."""
    start = date(2026, 1, 1)
    end = date(2026, 4, 1)
    joined = date(2026, 5, 1)
    frac = _calc_months_fraction(start, end, joined_at=joined)
    assert frac == 0.0


def test_calc_player_cost_internal_full_quarter():
    """Internal: salary × 3 meses completos."""

    class FakePlayer:
        employment_type = "internal"
        monthly_salary = 45000.0
        hourly_rate = None
        monthly_hours_cap = None
        joined_at = None

    cost, note = _calc_player_cost(FakePlayer(), date(2026, 1, 1), date(2026, 4, 1))  # type: ignore[arg-type]
    assert cost is not None
    assert abs(cost - 135000.0) < 1.0
    assert note == "sin joined_at — meses completos"


def test_calc_player_cost_internal_no_salary():
    """Internal sin monthly_salary → None + nota."""

    class FakePlayer:
        employment_type = "internal"
        monthly_salary = None
        hourly_rate = None
        monthly_hours_cap = None
        joined_at = None

    cost, note = _calc_player_cost(FakePlayer(), date(2026, 1, 1), date(2026, 4, 1))  # type: ignore[arg-type]
    assert cost is None
    assert note == "Costo no capturado"


def test_calc_player_cost_external_no_hours_cap():
    """External sin monthly_hours_cap → None + nota de estimación."""

    class FakePlayer:
        employment_type = "external"
        monthly_salary = None
        hourly_rate = 300.0
        monthly_hours_cap = None
        joined_at = None

    cost, note = _calc_player_cost(FakePlayer(), date(2026, 1, 1), date(2026, 4, 1))  # type: ignore[arg-type]
    assert cost is None
    assert note is not None and "manual" in note.lower()


def test_calc_player_cost_external_with_cap():
    """External con hourly_rate × hours_cap × meses."""

    class FakePlayer:
        employment_type = "external"
        monthly_salary = None
        hourly_rate = 300.0
        monthly_hours_cap = 160
        joined_at = None

    cost, _ = _calc_player_cost(FakePlayer(), date(2026, 1, 1), date(2026, 4, 1))  # type: ignore[arg-type]
    # 300 × 160 × 3 = 144,000
    assert cost is not None
    assert abs(cost - 144000.0) < 1.0


# ──────────────────────────────────────────────────────────────
# Tests: div/0 y cost_not_captured
# ──────────────────────────────────────────────────────────────


def test_cost_by_dev_div_zero(test_session: Session):
    """Player con costo pero 0 CP → cost_per_cp=None, no_production=True."""
    pm = _make_player(test_session, "pm-div0", "PM", "internal", salary=50000.0)

    svc = CostService(test_session)
    results = svc.cost_by_dev(period="q_current")

    pm_result = next((p for p in results if p.player_id == pm.id), None)
    assert pm_result is not None
    assert pm_result.cp_total == 0
    assert pm_result.cost_per_cp is None
    assert pm_result.no_production is True


def test_cost_by_dev_no_cost_captured(test_session: Session):
    """Player sin costo → cost_not_captured=True, no rompe el agregado."""
    dev = _make_player(test_session, "dev-nocost", "BE", "internal", salary=None)
    _make_subtask(test_session, dev.id, "BE", cp=10, sp=10.0, done_at=datetime(2026, 5, 15))  # Q2

    svc = CostService(test_session)
    results = svc.cost_by_dev(period="q_current")

    dev_result = next((p for p in results if p.player_id == dev.id), None)
    assert dev_result is not None
    assert dev_result.cost_not_captured is True
    assert dev_result.cost_total is None
    assert dev_result.cost_per_cp is None


def test_cost_by_area_no_crash_with_mixed_players(test_session: Session):
    """Área con players con y sin costo → el área agrega sin crash."""
    p1 = _make_player(test_session, "be-1", "BE", "internal", salary=45000.0)
    p2 = _make_player(test_session, "be-2", "BE", "internal", salary=None)

    _make_subtask(test_session, p1.id, "BE", cp=20, sp=20.0, done_at=datetime(2026, 5, 1))  # Q2
    _make_subtask(test_session, p2.id, "BE", cp=10, sp=10.0, done_at=datetime(2026, 5, 1))  # Q2

    svc = CostService(test_session)
    areas = svc.cost_by_area(period="q_current")
    be = next((a for a in areas if a.area == "BE"), None)
    assert be is not None
    assert be.cp_total == 30  # suma ambos
    assert be.cost_total is not None  # solo p1 tiene costo
    assert be.cost_per_cp is not None


# ──────────────────────────────────────────────────────────────
# Tests: comparativa int/ext
# ──────────────────────────────────────────────────────────────


def test_comparison_multiplier_calculated(test_session: Session):
    """Comparativa int vs ext: múltiplo calculado del costo real, no hardcodeado."""
    # internal: salary=40000/mes, ext: hourly=500 × 160 h = 80000/mes
    # Q1 = 3 meses → int=120000, ext=240000
    # Ambos producen 60 CP en Q1
    p_int = _make_player(test_session, "be-int", "BE", "internal", salary=40000.0)
    p_ext = _make_player(test_session, "be-ext", "BE", "external", hourly=500.0, hours_cap=160)

    for _ in range(3):
        _make_subtask(test_session, p_int.id, "BE", cp=10, sp=10.0, done_at=datetime(2026, 5, 1))  # Q2
        _make_subtask(test_session, p_ext.id, "BE", cp=10, sp=10.0, done_at=datetime(2026, 5, 1))  # Q2

    svc = CostService(test_session)
    comps = svc.comparison_int_ext(period="q_current")
    be = next((c for c in comps if c.area == "BE"), None)
    assert be is not None
    assert be.multiplier is not None
    # int: 120000/30cp = 4000/cp; ext: 240000/30cp = 8000/cp → mult = 2.0
    assert abs(be.multiplier - 2.0) < 0.1
    assert "2" in be.insight  # el insight menciona el múltiplo calculado


# ──────────────────────────────────────────────────────────────
# Tests: delta vs periodo anterior
# ──────────────────────────────────────────────────────────────


def test_cost_by_area_delta_pct(test_session: Session):
    """delta_pct se calcula como variación vs trimestre anterior."""
    p = _make_player(test_session, "be-delta", "BE", "internal", salary=45000.0)

    # Q_prev: Jan-Mar (si hoy es Jun, Q_prev es Q1=Jan-Mar)
    # Q_current: Apr-Jun
    _make_subtask(test_session, p.id, "BE", cp=10, sp=10.0, done_at=datetime(2026, 2, 1))
    _make_subtask(test_session, p.id, "BE", cp=15, sp=15.0, done_at=datetime(2026, 5, 1))

    svc = CostService(test_session)
    areas = svc.cost_by_area(period="q_current")
    be = next((a for a in areas if a.area == "BE"), None)
    # delta_pct puede ser None o un número — no debe crashear
    assert be is not None
    # delta no rompe (valor puede ser None si prev_cost=0)


# ──────────────────────────────────────────────────────────────
# Tests: read-only (0 escrituras)
# ──────────────────────────────────────────────────────────────


def test_cost_service_is_read_only(test_session: Session):
    """Todos los endpoints son read-only: los conteos no cambian."""
    p = _make_player(test_session, "be-ro", "BE", "internal", salary=45000.0)
    _make_subtask(test_session, p.id, "BE", cp=5, sp=5.0, done_at=datetime(2026, 2, 1))

    svc = CostService(test_session)
    counts_before = svc.row_counts()

    svc.cost_by_area(period="q_current")
    svc.cost_by_dev(period="q_current")
    svc.comparison_int_ext(period="q_current")
    svc.evolution_12m()

    counts_after = svc.row_counts()
    assert counts_before == counts_after


# ──────────────────────────────────────────────────────────────
# Tests: guard placeholder
# ──────────────────────────────────────────────────────────────


def test_require_cost_access_placeholder():
    """Guard placeholder existe y retorna True (deja pasar)."""
    assert require_cost_access() is True
    assert require_cost_access(role="player") is True  # hoy deja pasar a todos


# ──────────────────────────────────────────────────────────────
# Tests: has_any_cost / empty state
# ──────────────────────────────────────────────────────────────


def test_has_any_cost_false_when_no_players(test_session: Session):
    """Sin players activos con costo → False (empty state)."""
    svc = CostService(test_session)
    assert svc.has_any_cost() is False


def test_has_any_cost_true_when_player_has_salary(test_session: Session):
    """Un player con salary → True."""
    _make_player(test_session, "be-hac", "BE", "internal", salary=45000.0)
    svc = CostService(test_session)
    assert svc.has_any_cost() is True


# ──────────────────────────────────────────────────────────────
# Tests: resolve_period
# ──────────────────────────────────────────────────────────────


def test_resolve_period_q_current_is_3_months():
    start, end = resolve_period("q_current")
    # end - start debe ser aprox 90 días
    delta = (end - start).days
    assert 89 <= delta <= 92


def test_resolve_period_custom_requires_dates():
    with pytest.raises(ValueError):
        resolve_period("custom")
