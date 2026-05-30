"""Tests para CycleRepository."""

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError, RuleViolationError
from forge.db.models.cycle import Cycle
from forge.repositories.cycle import CycleRepository


def _make_cycle(
    iso_year: int = 2026,
    iso_week: int = 22,
    name: str = "Ciclo 2026-W22",
    start_offset: int = -4,
    end_offset: int = 0,
    status: str = "active",
) -> Cycle:
    today = date.today()
    return Cycle(
        iso_year=iso_year,
        iso_week=iso_week,
        name=name,
        start_date=today + timedelta(days=start_offset),
        end_date=today + timedelta(days=end_offset),
        status=status,
    )


def test_get_active_returns_active_cycle(test_session: Session) -> None:
    repo = CycleRepository(test_session)
    cycle = _make_cycle(status="active")
    test_session.add(cycle)
    test_session.flush()

    result = repo.get_active()

    assert result is not None
    assert result.status == "active"


def test_get_active_returns_none_when_no_active(test_session: Session) -> None:
    repo = CycleRepository(test_session)
    test_session.add(_make_cycle(status="closed"))
    test_session.flush()

    result = repo.get_active()

    assert result is None


def test_get_by_iso_week(test_session: Session) -> None:
    repo = CycleRepository(test_session)
    cycle = _make_cycle(iso_year=2026, iso_week=22)
    test_session.add(cycle)
    test_session.flush()

    result = repo.get_by_iso_week(2026, 22)

    assert result is not None
    assert result.iso_week == 22


def test_get_by_iso_week_returns_none_for_missing(test_session: Session) -> None:
    repo = CycleRepository(test_session)
    result = repo.get_by_iso_week(2099, 99)
    assert result is None


def test_get_by_date_returns_covering_cycle(test_session: Session) -> None:
    repo = CycleRepository(test_session)
    today = date.today()
    cycle = _make_cycle(start_offset=-4, end_offset=0)
    test_session.add(cycle)
    test_session.flush()

    result = repo.get_by_date(today)

    assert result is not None


def test_get_by_date_returns_none_when_no_match(test_session: Session) -> None:
    repo = CycleRepository(test_session)
    result = repo.get_by_date(date(2099, 1, 1))
    assert result is None


def test_list_recent_closed_respects_limit(test_session: Session) -> None:
    repo = CycleRepository(test_session)
    today = date.today()
    for i in range(6):
        test_session.add(
            Cycle(
                iso_year=2026,
                iso_week=i + 1,
                name=f"Ciclo 2026-W0{i+1}",
                start_date=today - timedelta(days=60 - i * 7),
                end_date=today - timedelta(days=55 - i * 7),
                status="closed",
                closed_at=datetime.utcnow(),
            )
        )
    test_session.flush()

    result = repo.list_recent_closed(limit=4)

    assert len(result) == 4


def test_get_previous_returns_cycle_before(test_session: Session) -> None:
    repo = CycleRepository(test_session)
    today = date.today()
    prev = Cycle(
        iso_year=2026, iso_week=21, name="Ciclo 2026-W21",
        start_date=today - timedelta(days=11),
        end_date=today - timedelta(days=7),
        status="closed",
    )
    current = Cycle(
        iso_year=2026, iso_week=22, name="Ciclo 2026-W22",
        start_date=today - timedelta(days=4),
        end_date=today,
        status="active",
    )
    test_session.add_all([prev, current])
    test_session.flush()

    result = repo.get_previous(current.id)

    assert result is not None
    assert result.iso_week == 21


def test_get_previous_returns_none_for_first_cycle(test_session: Session) -> None:
    repo = CycleRepository(test_session)
    cycle = _make_cycle(status="active")
    test_session.add(cycle)
    test_session.flush()

    result = repo.get_previous(cycle.id)

    assert result is None


def test_close_cycle_sets_status_and_timestamps(test_session: Session, sample_player) -> None:
    repo = CycleRepository(test_session)
    cycle = _make_cycle(status="active")
    test_session.add(cycle)
    test_session.flush()

    result = repo.close_cycle(
        cycle_id=cycle.id,
        mvp_player_id=sample_player.id,
        mvp_reason="Best performer",
        closed_by=sample_player.id,
    )

    assert result.status == "closed"
    assert result.closed_at is not None
    assert result.mvp_player_id == sample_player.id


def test_close_cycle_raises_for_already_closed(test_session: Session, sample_player) -> None:
    repo = CycleRepository(test_session)
    cycle = _make_cycle(status="closed")
    test_session.add(cycle)
    test_session.flush()

    with pytest.raises(RuleViolationError):
        repo.close_cycle(
            cycle_id=cycle.id,
            mvp_player_id=None,
            mvp_reason=None,
            closed_by=sample_player.id,
        )


def test_close_cycle_raises_for_not_found(test_session: Session, sample_player) -> None:
    repo = CycleRepository(test_session)

    with pytest.raises(NotFoundError):
        repo.close_cycle(
            cycle_id=99999,
            mvp_player_id=None,
            mvp_reason=None,
            closed_by=sample_player.id,
        )


def test_archive_old_closed_archives_eligible(test_session: Session) -> None:
    repo = CycleRepository(test_session)
    today = date.today()
    old_closed = Cycle(
        iso_year=2026, iso_week=10, name="Ciclo 2026-W10",
        start_date=today - timedelta(days=60),
        end_date=today - timedelta(days=56),
        status="closed",
        closed_at=datetime.utcnow() - timedelta(days=10),
    )
    recent_closed = Cycle(
        iso_year=2026, iso_week=20, name="Ciclo 2026-W20",
        start_date=today - timedelta(days=18),
        end_date=today - timedelta(days=14),
        status="closed",
        closed_at=datetime.utcnow() - timedelta(days=3),
    )
    test_session.add_all([old_closed, recent_closed])
    test_session.flush()

    count = repo.archive_old_closed()

    assert count == 1
    test_session.refresh(old_closed)
    assert old_closed.status == "archived"
    test_session.refresh(recent_closed)
    assert recent_closed.status == "closed"
