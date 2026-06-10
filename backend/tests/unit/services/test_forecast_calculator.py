"""Tests unitarios para ForecastCalculator (UC-07)."""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session

from forge.db.models.cycle import Cycle
from forge.db.models.epic import Epic
from forge.db.models.story import Story
from forge.db.models.subtask import Subtask
from forge.services.engine.forecast import ForecastCalculator, _add_weeks


# ──────────────────────────────────────────────────────────────
# Factories
# ──────────────────────────────────────────────────────────────

def _cycle(session: Session, name: str, status: str = "closed", offset_weeks: int = 0) -> Cycle:
    start = date.today() - timedelta(weeks=offset_weeks)
    iso = start.isocalendar()
    c = Cycle(
        name=name,
        iso_year=iso[0],
        iso_week=iso[1],
        start_date=start,
        end_date=start + timedelta(days=4),
        status=status,
    )
    session.add(c)
    session.flush()
    return c


def _epic(
    session: Session,
    key: str,
    status: str = "In Progress",
    epic_kind: str = "normal",
) -> Epic:
    from datetime import datetime

    e = Epic(
        jira_key=key,
        summary=f"Epic {key}",
        status=status,
        epic_kind=epic_kind,
        cp_total=0.0,
        last_synced_at=datetime.utcnow(),
    )
    session.add(e)
    session.flush()
    return e


def _story(session: Session, key: str, epic_key: str) -> Story:
    from datetime import datetime

    s = Story(
        jira_key=key,
        parent_epic_key=epic_key,
        summary=f"Story {key}",
        status="In Progress",
        cp_raw=0.0,
        cp_total=0.0,
        n_areas=0,
        has_dependency_chain=False,
        overhead_factor=1.0,
        dependency_factor=1.0,
        last_synced_at=datetime.utcnow(),
    )
    session.add(s)
    session.flush()
    return s


def _subtask(
    session: Session,
    key: str,
    story_key: str,
    area: str,
    status: str,
    cp: float | None,
    cycle_id: int | None = None,
) -> Subtask:
    from datetime import datetime

    s = Subtask(
        jira_key=key,
        issue_type="Sub-task",
        area=area,
        summary=f"Sub {key}",
        status=status,
        cp=cp,
        parent_story_key=story_key,
        qa_attempts=0,
        review_rejections=0,
        m_calidad=1.0,
        m_eficiencia=1.0,
        m_dificultad=1.0,
        m_lider=1.0,
        m_cooperacion=1.0,
        sp_flat_bonus=0.0,
        sp_penalty=0.0,
        cp_approval_required=False,
        cp_modified_post_approval=False,
        last_synced_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        cycle_id=cycle_id,
        done_at=datetime.utcnow() if status == "Done" else None,
    )
    session.add(s)
    session.flush()
    return s


# ──────────────────────────────────────────────────────────────
# _add_weeks helper
# ──────────────────────────────────────────────────────────────

def test_add_weeks_rounds_up():
    base = date(2026, 6, 1)
    assert _add_weeks(base, 0.1) == base + timedelta(weeks=1)
    assert _add_weeks(base, 1.0) == base + timedelta(weeks=1)
    assert _add_weeks(base, 1.1) == base + timedelta(weeks=2)
    assert _add_weeks(base, 2.9) == base + timedelta(weeks=3)


# ──────────────────────────────────────────────────────────────
# Core: 3 escenarios se separan (opt < real < cons en semanas)
# ──────────────────────────────────────────────────────────────

def test_three_scenarios_separate(test_session: Session):
    """opt_weeks < real_weeks < cons_weeks para área con varianza."""
    c1 = _cycle(test_session, "W19", offset_weeks=7)
    c2 = _cycle(test_session, "W20", offset_weeks=6)
    c3 = _cycle(test_session, "W21", offset_weeks=5)
    c4 = _cycle(test_session, "W22", offset_weeks=4)
    test_session.commit()

    epic = _epic(test_session, "YAP-T01")
    story = _story(test_session, "YAP-S01", "YAP-T01")
    # Velocidad variable: 6, 18, 13, 12 → avg≈12.25, best=18, sigma≈4.26, cons≈7.99
    _subtask(test_session, "T001", "YAP-S01", "BE", "Done", 6.0, c1.id)
    _subtask(test_session, "T002", "YAP-S01", "BE", "Done", 18.0, c2.id)
    _subtask(test_session, "T003", "YAP-S01", "BE", "Done", 13.0, c3.id)
    _subtask(test_session, "T004", "YAP-S01", "BE", "Done", 12.0, c4.id)
    # Pendiente
    _subtask(test_session, "T005", "YAP-S01", "BE", "In Progress", 20.0)
    test_session.commit()

    calc = ForecastCalculator(test_session)
    ef = calc.compute_one("YAP-T01")
    assert ef is not None
    assert len(ef.areas) == 1
    af = ef.areas[0]

    assert af.weeks_optimistic < af.weeks_realistic
    assert af.weeks_realistic < af.weeks_conservative
    assert ef.date_optimistic is not None
    assert ef.date_realistic is not None
    assert ef.date_conservative is not None
    assert ef.date_optimistic <= ef.date_realistic <= ef.date_conservative


def test_three_scenarios_math(test_session: Session):
    """Verifica las fórmulas exactas contra el cálculo manual."""
    c1 = _cycle(test_session, "W19b", offset_weeks=7)
    c2 = _cycle(test_session, "W20b", offset_weeks=6)
    c3 = _cycle(test_session, "W21b", offset_weeks=5)
    c4 = _cycle(test_session, "W22b", offset_weeks=4)
    test_session.commit()

    epic = _epic(test_session, "YAP-T02")
    story = _story(test_session, "YAP-S02", "YAP-T02")
    # Velocidad fija = 10 CP/ciclo → sin varianza → cons = max(10-0, FLOOR) = 10
    for i, cid in enumerate([c1.id, c2.id, c3.id, c4.id], 1):
        _subtask(test_session, f"T0{i:02d}b", "YAP-S02", "FE", "Done", 10.0, cid)
    # 20 CP pendientes
    _subtask(test_session, "T005b", "YAP-S02", "FE", "In Progress", 20.0)
    test_session.commit()

    calc = ForecastCalculator(test_session)
    ef = calc.compute_one("YAP-T02")
    assert ef is not None
    af = ef.areas[0]

    # avg=10, best=10, sigma=0, cons=max(10-0, 1.0)=10
    assert abs(af.velocity_avg - 10.0) < 0.01
    assert abs(af.velocity_best - 10.0) < 0.01
    assert abs(af.velocity_cons - 10.0) < 0.01

    # opt = 20/10 × 1.0 = 2.0
    # real = 20/10 × 1.2 = 2.4
    # cons = 20/10 × 1.3 = 2.6
    assert abs(af.weeks_optimistic - 2.0) < 0.01
    assert abs(af.weeks_realistic - 2.4) < 0.01
    assert abs(af.weeks_conservative - 2.6) < 0.01

    today = date.today()
    assert af.date_optimistic == today + timedelta(weeks=math.ceil(2.0))
    assert af.date_realistic == today + timedelta(weeks=math.ceil(2.4))
    assert af.date_conservative == today + timedelta(weeks=math.ceil(2.6))


# ──────────────────────────────────────────────────────────────
# Área con cp_pending == 0 se ignora
# ──────────────────────────────────────────────────────────────

def test_area_zero_pending_ignored(test_session: Session):
    c1 = _cycle(test_session, "W19c", offset_weeks=7)
    c2 = _cycle(test_session, "W20c", offset_weeks=6)
    c3 = _cycle(test_session, "W21c", offset_weeks=5)
    c4 = _cycle(test_session, "W22c", offset_weeks=4)
    test_session.commit()

    epic = _epic(test_session, "YAP-T03")
    story = _story(test_session, "YAP-S03", "YAP-T03")
    # BE: 8 CP done, 10 CP pending
    for cid in [c1.id, c2.id, c3.id, c4.id]:
        _subtask(test_session, f"Tbe_{cid}", "YAP-S03", "BE", "Done", 2.0, cid)
    _subtask(test_session, "Tbe_pend", "YAP-S03", "BE", "In Progress", 10.0)
    # PO: 5 CP done, 0 CP pending → should be excluded from areas list
    _subtask(test_session, "Tpo_done", "YAP-S03", "PO", "Done", 5.0, c4.id)
    test_session.commit()

    calc = ForecastCalculator(test_session)
    ef = calc.compute_one("YAP-T03")
    assert ef is not None
    areas = [af.area for af in ef.areas]
    assert "BE" in areas
    assert "PO" not in areas, "PO has 0 cp_pending, should be excluded"


# ──────────────────────────────────────────────────────────────
# Epic date = max de las áreas
# ──────────────────────────────────────────────────────────────

def test_epic_date_is_max_of_areas(test_session: Session):
    c1 = _cycle(test_session, "W19d", offset_weeks=7)
    c2 = _cycle(test_session, "W20d", offset_weeks=6)
    c3 = _cycle(test_session, "W21d", offset_weeks=5)
    c4 = _cycle(test_session, "W22d", offset_weeks=4)
    test_session.commit()

    epic = _epic(test_session, "YAP-T04")
    story = _story(test_session, "YAP-S04", "YAP-T04")
    # BE: velocidad alta → terminará rápido
    for cid in [c1.id, c2.id, c3.id, c4.id]:
        _subtask(test_session, f"Tbe2_{cid}", "YAP-S04", "BE", "Done", 20.0, cid)
    _subtask(test_session, "Tbe2_pend", "YAP-S04", "BE", "In Progress", 5.0)
    # DB: velocidad baja → tardará más
    _subtask(test_session, f"Tdb2_{c1.id}", "YAP-S04", "DB", "Done", 1.0, c1.id)
    _subtask(test_session, "Tdb2_pend", "YAP-S04", "DB", "In Progress", 50.0)
    test_session.commit()

    calc = ForecastCalculator(test_session)
    ef = calc.compute_one("YAP-T04")
    assert ef is not None
    assert len(ef.areas) == 2

    area_map = {af.area: af for af in ef.areas}
    assert ef.date_realistic == max(area_map["BE"].date_realistic, area_map["DB"].date_realistic)
    assert ef.date_conservative == max(
        area_map["BE"].date_conservative, area_map["DB"].date_conservative
    )


# ──────────────────────────────────────────────────────────────
# preliminary = True cuando <4 ciclos con datos
# ──────────────────────────────────────────────────────────────

def test_preliminary_with_less_than_4_cycles(test_session: Session):
    c1 = _cycle(test_session, "W22e", offset_weeks=4)
    c2 = _cycle(test_session, "W21e", offset_weeks=5)
    # Solo 2 ciclos cerrados
    test_session.commit()

    epic = _epic(test_session, "YAP-T05")
    story = _story(test_session, "YAP-S05", "YAP-T05")
    _subtask(test_session, "Te1", "YAP-S05", "BE", "Done", 10.0, c1.id)
    _subtask(test_session, "Te2", "YAP-S05", "BE", "Done", 8.0, c2.id)
    _subtask(test_session, "Te3", "YAP-S05", "BE", "In Progress", 10.0)
    test_session.commit()

    calc = ForecastCalculator(test_session)
    ef = calc.compute_one("YAP-T05")
    assert ef is not None
    assert ef.preliminary is True
    assert ef.warning is not None and "preliminar" in ef.warning.lower()
    af = ef.areas[0]
    assert af.preliminary is True
    assert af.n_cycles_data < 4


# ──────────────────────────────────────────────────────────────
# División por cero: cons_velocity ≤ 0 → piso VELOCITY_FLOOR
# ──────────────────────────────────────────────────────────────

def test_cons_velocity_floor(test_session: Session):
    """Si sigma > avg, cons_velocity queda en VELOCITY_FLOOR, no en negativo."""
    c1 = _cycle(test_session, "W19f", offset_weeks=7)
    c2 = _cycle(test_session, "W20f", offset_weeks=6)
    c3 = _cycle(test_session, "W21f", offset_weeks=5)
    c4 = _cycle(test_session, "W22f", offset_weeks=4)
    test_session.commit()

    epic = _epic(test_session, "YAP-T06")
    story = _story(test_session, "YAP-S06", "YAP-T06")
    # Alta varianza: 0, 0, 0, 30 → avg=7.5, sigma≈12.99, avg-sigma<0 → floor
    _subtask(test_session, "Tf4", "YAP-S06", "PO", "Done", 30.0, c4.id)
    _subtask(test_session, "Tf_pend", "YAP-S06", "PO", "In Progress", 15.0)
    test_session.commit()

    from forge.services.engine.forecast import _VELOCITY_FLOOR

    calc = ForecastCalculator(test_session)
    ef = calc.compute_one("YAP-T06")
    assert ef is not None
    af = ef.areas[0]
    assert af.velocity_cons >= _VELOCITY_FLOOR
    assert af.weeks_conservative > 0
    assert af.weeks_conservative > af.weeks_realistic


# ──────────────────────────────────────────────────────────────
# Sin CP estimado → warning "Sin CP"
# ──────────────────────────────────────────────────────────────

def test_epic_without_cp_no_crash(test_session: Session):
    epic = _epic(test_session, "YAP-T07")
    story = _story(test_session, "YAP-S07", "YAP-T07")
    # Subtask sin CP
    _subtask(test_session, "Tg1", "YAP-S07", "BE", "In Progress", None)
    test_session.commit()

    calc = ForecastCalculator(test_session)
    ef = calc.compute_one("YAP-T07")
    assert ef is not None
    assert ef.cp_total == 0.0
    assert ef.areas == []
    assert ef.warning is not None


# ──────────────────────────────────────────────────────────────
# WP-19: epic_kind — coordination y version_container excluidos
# ──────────────────────────────────────────────────────────────

def test_coordination_epic_excluded_from_compute_all(test_session: Session):
    """compute_all solo devuelve épicas 'normal'; coordination queda fuera."""
    _cycle(test_session, "WK19h", offset_weeks=4)
    _cycle(test_session, "WK20h", offset_weeks=3)
    test_session.commit()

    normal_epic = _epic(test_session, "YAP-N01", epic_kind="normal")
    coord_epic = _epic(test_session, "YAP-C01", epic_kind="coordination")
    vc_epic = _epic(test_session, "YAP-V01", epic_kind="version_container")
    test_session.commit()

    calc = ForecastCalculator(test_session)
    results = calc.compute_all()
    keys = [ef.epic_key for ef in results]

    assert "YAP-N01" in keys, "épica normal debe aparecer en forecast"
    assert "YAP-C01" not in keys, "coordination NO debe aparecer en forecast"
    assert "YAP-V01" not in keys, "version_container NO debe aparecer en forecast"


def test_compute_one_carries_epic_kind(test_session: Session):
    """compute_one devuelve epic_kind correcto en EpicForecast."""
    _epic(test_session, "YAP-K01", epic_kind="normal")
    _epic(test_session, "YAP-K02", epic_kind="version_container")
    test_session.commit()

    calc = ForecastCalculator(test_session)
    ef_normal = calc.compute_one("YAP-K01")
    ef_vc = calc.compute_one("YAP-K02")

    assert ef_normal is not None and ef_normal.epic_kind == "normal"
    assert ef_vc is not None and ef_vc.epic_kind == "version_container"


def test_epic_kind_default_is_normal(test_session: Session):
    """Epic creada sin epic_kind explícito debe tener 'normal'."""
    from datetime import datetime as _dt

    e = Epic(
        jira_key="YAP-DEF01",
        summary="Default kind test",
        status="In Progress",
        cp_total=0.0,
        last_synced_at=_dt.utcnow(),
    )
    test_session.add(e)
    test_session.flush()
    assert e.epic_kind == "normal"


def test_version_container_excluded_from_compute_all(test_session: Session):
    """version_container queda fuera del forecast aunque tenga CP pendiente."""
    c1 = _cycle(test_session, "WK19vc", offset_weeks=5)
    c2 = _cycle(test_session, "WK20vc", offset_weeks=4)
    c3 = _cycle(test_session, "WK21vc", offset_weeks=3)
    c4 = _cycle(test_session, "WK22vc", offset_weeks=2)
    test_session.commit()

    vc = _epic(test_session, "YAP-VC99", epic_kind="version_container")
    story = _story(test_session, "YAP-S99", "YAP-VC99")
    for cid in [c1.id, c2.id, c3.id, c4.id]:
        _subtask(test_session, f"Tvc_{cid}", "YAP-S99", "BE", "Done", 5.0, cid)
    _subtask(test_session, "Tvc_pend", "YAP-S99", "BE", "In Progress", 20.0)
    test_session.commit()

    calc = ForecastCalculator(test_session)
    results = calc.compute_all()
    assert all(ef.epic_key != "YAP-VC99" for ef in results)
