"""Tests para SprintRepository."""

from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session

from forge.core.exceptions import RuleViolationError
from forge.db.models.sprint import Sprint
from forge.repositories.sprint import SprintRepository


def _make_sprint(
    name: str,
    start_offset: int = -7,
    end_offset: int = 7,
    is_closed: bool = False,
) -> Sprint:
    today = date.today()
    return Sprint(
        name=name,
        start_date=today + timedelta(days=start_offset),
        end_date=today + timedelta(days=end_offset),
        is_closed=is_closed,
    )


def test_get_active_returns_current_sprint(test_session: Session) -> None:
    repo = SprintRepository(test_session)
    sprint = _make_sprint("Sprint-Active", start_offset=-5, end_offset=9)
    test_session.add(sprint)
    test_session.flush()

    result = repo.get_active()

    assert result is not None
    assert result.name == "Sprint-Active"


def test_get_active_returns_none_when_all_closed(test_session: Session) -> None:
    repo = SprintRepository(test_session)
    test_session.add(_make_sprint("Sprint-Closed", is_closed=True))
    test_session.flush()

    result = repo.get_active()

    assert result is None


def test_get_active_returns_none_when_future_sprint(test_session: Session) -> None:
    repo = SprintRepository(test_session)
    test_session.add(_make_sprint("Sprint-Future", start_offset=5, end_offset=19))
    test_session.flush()

    result = repo.get_active()

    assert result is None


def test_list_all_excludes_closed_by_default(test_session: Session) -> None:
    repo = SprintRepository(test_session)
    test_session.add(_make_sprint("Sprint-Open", is_closed=False))
    test_session.add(_make_sprint("Sprint-Old", start_offset=-30, end_offset=-16, is_closed=True))
    test_session.flush()

    results = repo.list_all()

    names = {s.name for s in results}
    assert "Sprint-Open" in names
    assert "Sprint-Old" not in names


def test_list_all_includes_closed_when_flagged(test_session: Session) -> None:
    repo = SprintRepository(test_session)
    test_session.add(_make_sprint("Sprint-Open2", is_closed=False))
    test_session.add(
        _make_sprint("Sprint-Old2", start_offset=-30, end_offset=-16, is_closed=True)
    )
    test_session.flush()

    results = repo.list_all(include_closed=True)

    names = {s.name for s in results}
    assert "Sprint-Open2" in names
    assert "Sprint-Old2" in names


def test_close_sets_is_closed_and_timestamp(test_session: Session) -> None:
    repo = SprintRepository(test_session)
    sprint = _make_sprint("Sprint-ToClose")
    test_session.add(sprint)
    test_session.flush()

    closed = repo.close(sprint.id, closed_by_id=99)

    assert closed.is_closed is True
    assert closed.closed_at is not None
    assert closed.closed_by == 99


def test_close_raises_if_already_closed(test_session: Session) -> None:
    repo = SprintRepository(test_session)
    sprint = _make_sprint("Sprint-AlreadyClosed", is_closed=True)
    test_session.add(sprint)
    test_session.flush()

    with pytest.raises(RuleViolationError):
        repo.close(sprint.id, closed_by_id=99)


def test_assign_mvp_sets_player_id(test_session: Session) -> None:
    repo = SprintRepository(test_session)
    sprint = _make_sprint("Sprint-MVP")
    test_session.add(sprint)
    test_session.flush()

    updated = repo.assign_mvp(sprint.id, player_id=42)

    assert updated.mvp_player_id == 42
