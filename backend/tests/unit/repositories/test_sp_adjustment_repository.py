"""Tests para SpAdjustmentRepository."""

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from forge.core.exceptions import AppendOnlyViolationError
from forge.db.models.player import Player
from forge.db.models.sp_adjustment import SpAdjustment
from forge.db.models.subtask import Subtask
from forge.repositories.sp_adjustment import SpAdjustmentRepository


def _seed_player(session: Session, jira_id: str = "pm-001", email: str = "pm@yapsi.com") -> Player:
    player = Player(
        jira_account_id=jira_id,
        display_name="PM",
        email=email,
        area="PM",
        employment_type="internal",
    )
    session.add(player)
    session.flush()
    return player


def _seed_subtask(session: Session, key: str = "TASK-ADJ-1") -> Subtask:
    subtask = Subtask(
        jira_key=key,
        issue_type="Backend Sub-task",
        area="BE",
        summary="Subtask for adjustments",
        status="Done",
    )
    session.add(subtask)
    session.flush()
    return subtask


def _make_adjustment(
    subtask_key: str,
    applied_by: int,
    amount: float = 10.0,
    adj_type: str = "bonus",
) -> SpAdjustment:
    return SpAdjustment(
        subtask_key=subtask_key,
        adjustment_type=adj_type,
        amount_sp=amount,
        reason="Test adjustment",
        applied_by=applied_by,
        applied_at=datetime.utcnow(),
    )


def test_create_persists_adjustment(test_session: Session) -> None:
    repo = SpAdjustmentRepository(test_session)
    player = _seed_player(test_session)
    subtask = _seed_subtask(test_session)

    adj = repo.create(_make_adjustment(subtask.jira_key, player.id, amount=15.0))

    assert adj.id is not None
    assert adj.amount_sp == 15.0


def test_list_by_subtask_returns_all(test_session: Session) -> None:
    repo = SpAdjustmentRepository(test_session)
    player = _seed_player(test_session, "pm-002", "pm2@yapsi.com")
    subtask = _seed_subtask(test_session, "TASK-ADJ-2")

    repo.create(_make_adjustment(subtask.jira_key, player.id, amount=5.0))
    repo.create(_make_adjustment(subtask.jira_key, player.id, amount=-3.0, adj_type="penalty"))

    results = repo.list_by_subtask(subtask.jira_key)

    assert len(results) == 2


def test_get_net_delta_sums_bonus_and_penalty(test_session: Session) -> None:
    repo = SpAdjustmentRepository(test_session)
    player = _seed_player(test_session, "pm-003", "pm3@yapsi.com")
    subtask = _seed_subtask(test_session, "TASK-ADJ-3")

    repo.create(_make_adjustment(subtask.jira_key, player.id, amount=20.0))
    repo.create(_make_adjustment(subtask.jira_key, player.id, amount=-8.0, adj_type="penalty"))

    net = repo.get_net_delta(subtask.jira_key)

    assert net == 12.0


def test_get_net_delta_returns_zero_when_none(test_session: Session) -> None:
    repo = SpAdjustmentRepository(test_session)

    assert repo.get_net_delta("TASK-NOEXISTE") == 0.0


def test_update_raises_not_implemented(test_session: Session) -> None:
    repo = SpAdjustmentRepository(test_session)
    player = _seed_player(test_session, "pm-004", "pm4@yapsi.com")
    subtask = _seed_subtask(test_session, "TASK-ADJ-4")
    adj = repo.create(_make_adjustment(subtask.jira_key, player.id))

    with pytest.raises(AppendOnlyViolationError):
        repo.update(adj)


def test_delete_raises_not_implemented(test_session: Session) -> None:
    repo = SpAdjustmentRepository(test_session)
    player = _seed_player(test_session, "pm-005", "pm5@yapsi.com")
    subtask = _seed_subtask(test_session, "TASK-ADJ-5")
    adj = repo.create(_make_adjustment(subtask.jira_key, player.id))

    with pytest.raises(AppendOnlyViolationError):
        repo.delete(adj)
