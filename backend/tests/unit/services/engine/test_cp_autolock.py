"""Tests del auto-lock de CP (WP-24/ADR-016).

Invariante golden reformulado: toda subtask con CP válido no-XXL queda lockeada
(cp_approved_at NOT NULL) tras el auto-lock, y la inmutabilidad se mantiene.
Las filas históricas aprobadas manualmente quedan intactas.
"""

import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from forge.db.models.audit_log import AuditLog
from forge.db.models.subtask import Subtask
from forge.services.engine.cp_autolock import auto_lock_cp


def _make_subtask(
    key: str,
    complexity_size: str | None = None,
    cp: int | None = None,
    cp_approved_at: datetime | None = None,
    cp_approved_by: int | None = None,
    cp_approval_required: bool = False,
    pruned_at: datetime | None = None,
) -> Subtask:
    return Subtask(
        jira_key=key,
        issue_type="Backend Sub-task",
        area="BE",
        summary=f"Summary {key}",
        status="Backlog",
        complexity_size=complexity_size,
        cp=cp,
        cp_approved_at=cp_approved_at,
        cp_approved_by=cp_approved_by,
        cp_approval_required=cp_approval_required,
        pruned_at=pruned_at,
    )


def test_autolock_locks_valid_non_xxl(test_session: Session) -> None:
    """CP válido no-XXL sin lock → queda lockeado con sentinela de sistema + audit."""
    test_session.add(_make_subtask("T-M", complexity_size="M", cp=3))
    test_session.add(_make_subtask("T-XL", complexity_size="XL", cp=8, cp_approval_required=True))
    test_session.flush()

    locked = auto_lock_cp(test_session)
    test_session.flush()

    assert locked == 2
    for key, expected_cp in (("T-M", 3), ("T-XL", 8)):
        st = test_session.get(Subtask, key)
        assert st is not None
        assert st.cp_approved_at is not None
        assert st.cp_approved_by is None, "sentinela de sistema = NULL"
        assert st.cp_approval_required is False
        assert st.cp == expected_cp, "el lock no cambia el valor de cp"

    logs = list(
        test_session.scalars(select(AuditLog).where(AuditLog.event_type == "cp_auto_locked"))
    )
    assert {log.entity_id for log in logs} == {"T-M", "T-XL"}
    assert all(log.actor_player_id is None for log in logs)
    changes = json.loads(logs[0].changes)
    assert "cp" in changes and "complexity_size" in changes


def test_autolock_skips_xxl(test_session: Session) -> None:
    """XXL es talla rechazada: nunca se lockea (debe partirse)."""
    test_session.add(_make_subtask("T-XXL", complexity_size="XXL", cp=13))
    test_session.flush()

    assert auto_lock_cp(test_session) == 0
    st = test_session.get(Subtask, "T-XXL")
    assert st is not None
    assert st.cp_approved_at is None


def test_autolock_skips_without_cp(test_session: Session) -> None:
    """Sin talla/cp no hay nada que lockear."""
    test_session.add(_make_subtask("T-NOCP"))
    test_session.flush()

    assert auto_lock_cp(test_session) == 0
    st = test_session.get(Subtask, "T-NOCP")
    assert st is not None
    assert st.cp_approved_at is None


def test_autolock_skips_pruned(test_session: Session) -> None:
    """Subtasks podadas están fuera del flujo: no se lockean."""
    test_session.add(
        _make_subtask("T-PRUNED", complexity_size="M", cp=3, pruned_at=datetime.utcnow())
    )
    test_session.flush()

    assert auto_lock_cp(test_session) == 0


def test_autolock_is_idempotent(test_session: Session) -> None:
    """Segunda corrida = 0 cambios; el timestamp del primer lock no se mueve."""
    test_session.add(_make_subtask("T-IDEM", complexity_size="S", cp=2))
    test_session.flush()

    assert auto_lock_cp(test_session) == 1
    test_session.flush()
    st = test_session.get(Subtask, "T-IDEM")
    assert st is not None
    first_lock = st.cp_approved_at

    assert auto_lock_cp(test_session) == 0
    test_session.flush()
    assert st.cp_approved_at == first_lock

    audit_count = test_session.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.event_type == "cp_auto_locked")
    )
    assert audit_count == 1


def test_autolock_does_not_touch_historical_approvals(test_session: Session) -> None:
    """Filas ya aprobadas manualmente (históricas) quedan byte-idénticas."""
    approved_at = datetime(2026, 5, 1, 12, 0, 0)
    test_session.add(
        _make_subtask(
            "T-HIST",
            complexity_size="L",
            cp=5,
            cp_approved_at=approved_at,
            cp_approved_by=1,
        )
    )
    test_session.flush()

    assert auto_lock_cp(test_session) == 0
    st = test_session.get(Subtask, "T-HIST")
    assert st is not None
    assert st.cp_approved_at == approved_at
    assert st.cp_approved_by == 1


def test_golden_invariant_all_valid_non_xxl_locked(test_session: Session) -> None:
    """Golden reformulado (antes 'cp_approved_at count = 56'):

    tras el auto-lock, NO existe ninguna subtask activa con CP válido no-XXL
    sin lockear, y las lockeadas conservan su cp exacto.
    """
    test_session.add(_make_subtask("G-1", complexity_size="XS", cp=1))
    test_session.add(_make_subtask("G-2", complexity_size="L", cp=5))
    test_session.add(_make_subtask("G-3", complexity_size="XXL", cp=13))
    test_session.add(_make_subtask("G-4"))  # sin CP
    test_session.add(
        _make_subtask(
            "G-5", complexity_size="M", cp=3, cp_approved_at=datetime(2026, 4, 1), cp_approved_by=1
        )
    )
    test_session.flush()

    auto_lock_cp(test_session)
    test_session.flush()

    unlocked_valid = test_session.scalar(
        select(func.count())
        .select_from(Subtask)
        .where(
            Subtask.cp.is_not(None),
            Subtask.complexity_size != "XXL",
            Subtask.cp_approved_at.is_(None),
            Subtask.pruned_at.is_(None),
        )
    )
    assert unlocked_valid == 0
