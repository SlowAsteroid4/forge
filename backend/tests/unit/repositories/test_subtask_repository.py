"""Tests para SubtaskRepository."""

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from forge.core.exceptions import CPImmutableError, NotFoundError
from forge.db.models.subtask import Subtask
from forge.repositories.subtask import SubtaskRepository


def _make_subtask(
    key: str,
    status: str = "In Progress",
    player_id: int | None = None,
    cycle_id: int | None = None,
    area: str = "BE",
    cp: int | None = None,
    sp_final: float | None = None,
    cp_approval_required: bool = False,
    cp_approved_at: datetime | None = None,
) -> Subtask:
    return Subtask(
        jira_key=key,
        issue_type="Backend Sub-task",
        area=area,
        summary=f"Summary of {key}",
        status=status,
        assignee_player_id=player_id,
        cycle_id=cycle_id,
        cp=cp,
        sp_final=sp_final,
        cp_approval_required=cp_approval_required,
        cp_approved_at=cp_approved_at,
    )


def test_get_by_key_found(test_session: Session) -> None:
    repo = SubtaskRepository(test_session)
    test_session.add(_make_subtask("TASK-1"))
    test_session.flush()

    result = repo.get("TASK-1")

    assert result is not None
    assert result.jira_key == "TASK-1"


def test_get_by_key_not_found(test_session: Session) -> None:
    repo = SubtaskRepository(test_session)

    result = repo.get("NONEXISTENT-99")

    assert result is None


def test_list_by_assignee_correct(test_session: Session) -> None:
    repo = SubtaskRepository(test_session)
    test_session.add(_make_subtask("T-10", player_id=1))
    test_session.add(_make_subtask("T-11", player_id=1))
    test_session.add(_make_subtask("T-12", player_id=2))
    test_session.flush()

    results = repo.list_by_assignee(player_id=1)

    keys = {s.jira_key for s in results}
    assert {"T-10", "T-11"} == keys


def test_list_by_assignee_with_cycle_filter(test_session: Session) -> None:
    repo = SubtaskRepository(test_session)
    test_session.add(_make_subtask("T-20", player_id=1, cycle_id=5))
    test_session.add(_make_subtask("T-21", player_id=1, cycle_id=6))
    test_session.flush()

    results = repo.list_by_assignee(player_id=1, cycle_id=5)

    assert len(results) == 1
    assert results[0].jira_key == "T-20"


def test_list_done_only_done_status(test_session: Session) -> None:
    repo = SubtaskRepository(test_session)
    test_session.add(_make_subtask("T-30", status="Done"))
    test_session.add(_make_subtask("T-31", status="In Progress"))
    test_session.add(_make_subtask("T-32", status="Done"))
    test_session.flush()

    results = repo.list_done()

    keys = {s.jira_key for s in results}
    assert "T-30" in keys
    assert "T-32" in keys
    assert "T-31" not in keys


def test_list_done_cycle_filter(test_session: Session) -> None:
    repo = SubtaskRepository(test_session)
    test_session.add(_make_subtask("T-40", status="Done", cycle_id=10))
    test_session.add(_make_subtask("T-41", status="Done", cycle_id=11))
    test_session.flush()

    results = repo.list_done(cycle_id=10)

    assert len(results) == 1
    assert results[0].jira_key == "T-40"


def test_list_pending_cp_approval_only_large_unapproved(test_session: Session) -> None:
    repo = SubtaskRepository(test_session)
    # Requiere aprobación, sin fecha → debe aparecer
    test_session.add(_make_subtask("T-50", cp_approval_required=True, cp_approved_at=None))
    # Requiere aprobación, ya aprobado → no debe aparecer
    test_session.add(
        _make_subtask("T-51", cp_approval_required=True, cp_approved_at=datetime.utcnow())
    )
    # No requiere aprobación → no debe aparecer
    test_session.add(_make_subtask("T-52", cp_approval_required=False))
    test_session.flush()

    results = repo.list_pending_cp_approval()

    keys = {s.jira_key for s in results}
    assert "T-50" in keys
    assert "T-51" not in keys
    assert "T-52" not in keys


def test_get_cp_sum_aggregates_correctly(test_session: Session) -> None:
    repo = SubtaskRepository(test_session)
    test_session.add(_make_subtask("T-60", status="Done", player_id=1, cp=3))
    test_session.add(_make_subtask("T-61", status="Done", player_id=1, cp=5))
    test_session.add(_make_subtask("T-62", status="In Progress", player_id=1, cp=8))
    test_session.flush()

    total = repo.get_cp_sum(player_id=1)

    assert total == 8.0  # Solo Done: 3 + 5


def test_get_cp_sum_returns_zero_when_no_subtasks(test_session: Session) -> None:
    repo = SubtaskRepository(test_session)

    assert repo.get_cp_sum(player_id=999) == 0.0


def test_get_sp_sum_aggregates_only_done(test_session: Session) -> None:
    repo = SubtaskRepository(test_session)
    test_session.add(_make_subtask("T-70", status="Done", player_id=2, sp_final=10.0))
    test_session.add(_make_subtask("T-71", status="Done", player_id=2, sp_final=5.5))
    test_session.add(_make_subtask("T-72", status="In Progress", player_id=2, sp_final=20.0))
    test_session.flush()

    total = repo.get_sp_sum(player_id=2)

    assert total == 15.5  # Solo Done: 10 + 5.5


def test_upsert_creates_new(test_session: Session) -> None:
    repo = SubtaskRepository(test_session)

    subtask = repo.upsert(
        {
            "jira_key": "T-80",
            "issue_type": "Backend Sub-task",
            "area": "BE",
            "summary": "New task",
            "status": "To Do",
        }
    )

    assert subtask.jira_key == "T-80"
    assert repo.get("T-80") is not None


def test_upsert_updates_existing(test_session: Session) -> None:
    repo = SubtaskRepository(test_session)
    test_session.add(_make_subtask("T-81", status="To Do"))
    test_session.flush()

    updated = repo.upsert(
        {
            "jira_key": "T-81",
            "issue_type": "Backend Sub-task",
            "area": "BE",
            "summary": "Updated summary",
            "status": "Done",
        }
    )

    assert updated.status == "Done"
    assert updated.summary == "Updated summary"


def test_approve_cp_sets_approved_at(test_session: Session) -> None:
    repo = SubtaskRepository(test_session)
    test_session.add(_make_subtask("T-90", cp_approval_required=True))
    test_session.flush()

    now = datetime.utcnow()
    result = repo.approve_cp("T-90", approver_id=1, approved_at=now)

    assert result.cp_approved_at == now
    assert result.cp_approved_by == 1


def test_approve_cp_raises_if_already_approved(test_session: Session) -> None:
    repo = SubtaskRepository(test_session)
    already = _make_subtask("T-91", cp_approved_at=datetime.utcnow())
    test_session.add(already)
    test_session.flush()

    with pytest.raises(CPImmutableError):
        repo.approve_cp("T-91", approver_id=1, approved_at=datetime.utcnow())
