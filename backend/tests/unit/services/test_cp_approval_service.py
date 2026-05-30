"""Tests unitarios para CpApprovalService."""

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from forge.core.exceptions import CPImmutableError, NotFoundError, RuleViolationError
from forge.db.models.subtask import Subtask
from forge.services.cp_approval_service import CpApprovalService


def _make_subtask(session: Session, **kwargs) -> Subtask:
    defaults = {
        "jira_key": "YAP-999",
        "issue_type": "Sub-task",
        "area": "BE",
        "summary": "Test subtask",
        "status": "Done",
        "last_synced_at": datetime.utcnow(),
        "cp_approval_required": True,
        "cp_modified_post_approval": False,
    }
    defaults.update(kwargs)
    st = Subtask(**defaults)
    session.add(st)
    session.commit()
    return st


# ── list_pending ──────────────────────────────────────────────────────────


def test_list_pending_returns_l_xl(test_session: Session) -> None:
    _make_subtask(test_session, jira_key="YAP-L1", complexity_size="L", cp=5)
    _make_subtask(test_session, jira_key="YAP-XL1", complexity_size="XL", cp=8)
    _make_subtask(
        test_session,
        jira_key="YAP-M1",
        complexity_size="M",
        cp=3,
        cp_approval_required=False,
    )

    svc = CpApprovalService(test_session)
    pending = svc.list_pending()
    keys = {p["jira_key"] for p in pending}
    assert "YAP-L1" in keys
    assert "YAP-XL1" in keys
    assert "YAP-M1" not in keys


def test_list_pending_excludes_approved(test_session: Session) -> None:
    _make_subtask(
        test_session,
        jira_key="YAP-DONE",
        complexity_size="L",
        cp=5,
        cp_approved_at=datetime.utcnow(),
        cp_approved_by=1,
    )

    svc = CpApprovalService(test_session)
    pending = svc.list_pending()
    assert not any(p["jira_key"] == "YAP-DONE" for p in pending)


# ── list_xxl ─────────────────────────────────────────────────────────────


def test_list_xxl_returns_xxl_only(test_session: Session) -> None:
    _make_subtask(test_session, jira_key="YAP-BIG", complexity_size="XXL", cp=13)
    _make_subtask(test_session, jira_key="YAP-L2", complexity_size="L", cp=5)

    svc = CpApprovalService(test_session)
    xxl = svc.list_xxl()
    assert len(xxl) == 1
    assert xxl[0]["jira_key"] == "YAP-BIG"


# ── approve ───────────────────────────────────────────────────────────────


def test_approve_seals_cp(test_session: Session) -> None:
    _make_subtask(test_session, jira_key="YAP-A1", complexity_size="L", cp=5)

    svc = CpApprovalService(test_session)
    st = svc.approve("YAP-A1", admin_id=1)
    test_session.commit()

    assert st.cp_approved_at is not None
    assert st.cp_approved_by == 1
    assert st.cp_approval_required is False


def test_approve_raises_immutable_if_already_approved(test_session: Session) -> None:
    _make_subtask(
        test_session,
        jira_key="YAP-A2",
        complexity_size="L",
        cp=5,
        cp_approved_at=datetime.utcnow(),
        cp_approved_by=1,
    )

    svc = CpApprovalService(test_session)
    with pytest.raises(CPImmutableError):
        svc.approve("YAP-A2", admin_id=2)


def test_approve_raises_not_found(test_session: Session) -> None:
    svc = CpApprovalService(test_session)
    with pytest.raises(NotFoundError):
        svc.approve("YAP-MISSING", admin_id=1)


# ── adjust_and_approve ────────────────────────────────────────────────────


def test_adjust_recalculates_cp(test_session: Session) -> None:
    _make_subtask(test_session, jira_key="YAP-ADJ1", complexity_size="L", cp=5)

    svc = CpApprovalService(test_session)
    st = svc.adjust_and_approve("YAP-ADJ1", new_size="M", reason="Revisado con PM", admin_id=1)
    test_session.commit()

    assert st.complexity_size == "M"
    assert st.cp == 3  # M = 3 en CP_TABLE
    assert st.cp_approved_at is not None


def test_adjust_xxl_forbidden(test_session: Session) -> None:
    _make_subtask(test_session, jira_key="YAP-ADJ2", complexity_size="L", cp=5)

    svc = CpApprovalService(test_session)
    with pytest.raises(RuleViolationError):
        svc.adjust_and_approve("YAP-ADJ2", new_size="XXL", reason="Prueba", admin_id=1)


def test_adjust_raises_immutable_if_already_approved(test_session: Session) -> None:
    _make_subtask(
        test_session,
        jira_key="YAP-ADJ3",
        complexity_size="L",
        cp=5,
        cp_approved_at=datetime.utcnow(),
        cp_approved_by=1,
    )

    svc = CpApprovalService(test_session)
    with pytest.raises(CPImmutableError):
        svc.adjust_and_approve("YAP-ADJ3", new_size="M", reason="no deberia", admin_id=2)


# ── reject ────────────────────────────────────────────────────────────────


def test_reject_stores_reason_stays_in_queue(test_session: Session) -> None:
    _make_subtask(test_session, jira_key="YAP-REJ1", complexity_size="L", cp=5)

    svc = CpApprovalService(test_session)
    st = svc.reject("YAP-REJ1", reason="Descripción insuficiente", admin_id=1)
    test_session.commit()

    assert st.cp_rejection_reason == "Descripción insuficiente"
    assert st.cp_approved_at is None
    assert st.cp_approval_required is True  # sigue en cola


def test_reject_already_approved_raises_immutable(test_session: Session) -> None:
    _make_subtask(
        test_session,
        jira_key="YAP-REJ2",
        complexity_size="L",
        cp=5,
        cp_approved_at=datetime.utcnow(),
        cp_approved_by=1,
    )

    svc = CpApprovalService(test_session)
    with pytest.raises(CPImmutableError):
        svc.reject("YAP-REJ2", reason="intento tardío", admin_id=2)


# ── mark_xxl_notified ─────────────────────────────────────────────────────


def test_mark_xxl_notified_ok(test_session: Session) -> None:
    _make_subtask(
        test_session, jira_key="YAP-XXL1", complexity_size="XXL", cp=13, cp_approval_required=False
    )

    svc = CpApprovalService(test_session)
    st = svc.mark_xxl_notified("YAP-XXL1", admin_id=1)
    test_session.commit()
    assert st.jira_key == "YAP-XXL1"


def test_mark_xxl_notified_non_xxl_raises(test_session: Session) -> None:
    _make_subtask(test_session, jira_key="YAP-L3", complexity_size="L", cp=5)

    svc = CpApprovalService(test_session)
    with pytest.raises(RuleViolationError):
        svc.mark_xxl_notified("YAP-L3", admin_id=1)
