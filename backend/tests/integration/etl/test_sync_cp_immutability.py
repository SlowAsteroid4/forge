"""Integración: sync no sobreescribe CP post-aprobación y registra audit_log."""

import json
from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from forge.db.base import Base
from forge.db.models.audit_log import AuditLog
from forge.db.models.project import Project
from forge.db.models.subtask import Subtask
from forge.etl.sync_orchestrator import SyncOrchestrator


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SL = sessionmaker(bind=engine)
    s = SL()
    yield s
    s.close()
    engine.dispose()


def _seed_approved_subtask(session: Session) -> Subtask:
    project = Project(
        code="YAP", jira_prefix="YAP", internal_name="Yapsi", arena_name="Yapsi Dungeon"
    )
    session.add(project)
    session.flush()

    st = Subtask(
        jira_key="YAP-100",
        issue_type="Sub-task",
        area="BE",
        summary="Subtask ya aprobada",
        status="Done",
        complexity_size="L",
        cp=5,
        cp_approved_at=datetime(2026, 5, 1),
        cp_approved_by=1,
        cp_approval_required=False,
        cp_modified_post_approval=False,
        last_synced_at=datetime.utcnow(),
    )
    session.add(st)
    session.commit()
    return st


def _make_jira_issue(cp_size: str = "XL") -> dict:
    """Simula un issue de Jira donde el campo de talla cambió a XL."""
    return {
        "key": "YAP-100",
        "fields": {
            "issuetype": {"name": "Sub-task"},
            "summary": "Subtask ya aprobada",
            "status": {"name": "Done"},
            "assignee": None,
            "parent": {"key": "YAP-50"},
            "project": {"key": "YAP"},
            # No hay campo complexity en el ETL actual — se simula via time_metrics
        },
        "changelog": {"histories": []},
    }


def test_sync_does_not_overwrite_approved_cp(db_session: Session) -> None:
    """CP aprobado no debe cambiar aunque Jira devuelva valores distintos."""
    _seed_approved_subtask(db_session)

    orchestrator = SyncOrchestrator(session=db_session)

    # Simular que el ETL calcula cp=8 (XL) — diferente al aprobado (L=5)
    fake_time_metrics: dict = {
        "done_at": datetime(2026, 5, 2),
        "lt_biz_hours": 10.0,
        "ct_biz_hours": 8.0,
        "adj_ct_biz_hours": 7.0,
        "dev_resp_biz_hours": 5.0,
        "cp": 8,
        "complexity_size": "XL",
    }

    with (
        patch(
            "forge.etl.sync_orchestrator.extract_time_metrics",
            return_value=fake_time_metrics,
        ),
        patch(
            "forge.etl.sync_orchestrator.extract_quality_metrics",
            return_value={"qa_attempts": 0, "review_rejections": 0, "qa_first_pass": True},
        ),
        patch(
            "forge.etl.sync_orchestrator.match_project",
            return_value="YAP",
        ),
    ):
        orchestrator._sync_subtask(_make_jira_issue(), stats={
            "subtasks_created": 0, "subtasks_updated": 0, "errors": []
        })
        db_session.commit()

    st = db_session.get(Subtask, "YAP-100")
    assert st is not None
    assert st.cp == 5, "CP aprobado debe ser inmutable"
    assert st.complexity_size == "L", "complexity_size aprobado debe ser inmutable"
    assert st.cp_modified_post_approval is True, "flag debe setearse cuando Jira difiere"

    # Debe haber un audit_log del intento
    log = db_session.scalars(
        select(AuditLog).where(
            AuditLog.event_type == "cp_change_attempted_post_approval",
            AuditLog.entity_id == "YAP-100",
        )
    ).first()
    assert log is not None
    changes = json.loads(log.changes)  # type: ignore[arg-type]
    assert changes["approved_cp"] == 5
    assert changes["jira_cp"] == 8


def test_sync_no_flag_when_cp_unchanged(db_session: Session) -> None:
    """Si Jira devuelve el mismo CP, no se setea el flag."""
    _seed_approved_subtask(db_session)

    orchestrator = SyncOrchestrator(session=db_session)

    # Simular métricas sin cp/complexity_size (caso normal de ETL)
    fake_time_metrics: dict = {
        "done_at": datetime(2026, 5, 2),
        "lt_biz_hours": 10.0,
        "ct_biz_hours": 8.0,
    }

    with (
        patch(
            "forge.etl.sync_orchestrator.extract_time_metrics",
            return_value=fake_time_metrics,
        ),
        patch(
            "forge.etl.sync_orchestrator.extract_quality_metrics",
            return_value={"qa_attempts": 0, "review_rejections": 0, "qa_first_pass": True},
        ),
        patch(
            "forge.etl.sync_orchestrator.match_project",
            return_value="YAP",
        ),
    ):
        orchestrator._sync_subtask(_make_jira_issue(), stats={
            "subtasks_created": 0, "subtasks_updated": 0, "errors": []
        })
        db_session.commit()

    st = db_session.get(Subtask, "YAP-100")
    assert st is not None
    assert st.cp == 5
    assert st.cp_modified_post_approval is False
