"""Tests de reconciliación de borrados (prune) del SyncOrchestrator.

Cubre find_stale_keys (detección) y delete_stale (borrado FK-seguro).
No tocan Jira: fetch_live_keys se prueba aparte / con mocks.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from forge.db.models.epic import Epic
from forge.db.models.player import Player
from forge.db.models.sp_adjustment import SpAdjustment
from forge.db.models.story import Story
from forge.db.models.subtask import Subtask
from forge.etl.sync_orchestrator import SyncOrchestrator


def _orch(session: Session) -> SyncOrchestrator:
    # SyncOrchestrator.__init__ crea un JiraClient; no lo usamos en estos tests
    # (solo find_stale_keys/delete_stale, que son pura BD).
    orch = SyncOrchestrator.__new__(SyncOrchestrator)
    orch.session = session
    return orch


def _seed_hierarchy(session: Session) -> Player:
    pm = Player(
        jira_account_id="pm-1",
        display_name="PM",
        email="pm@yapsi.com",
        area="PM",
        employment_type="internal",
    )
    session.add(pm)
    session.add(Epic(jira_key="YAP-1", project_code="YAP", summary="E", status="Done"))
    session.add(Story(jira_key="YAP-2", parent_epic_key="YAP-1", summary="S", status="Done"))
    session.add_all(
        [
            Subtask(
                jira_key="YAP-3",
                parent_story_key="YAP-2",
                project_code="YAP",
                issue_type="Backend Sub-task",
                area="BE",
                summary="vive",
                status="Done",
            ),
            Subtask(
                jira_key="YAP-4",
                parent_story_key="YAP-2",
                project_code="YAP",
                issue_type="Backend Sub-task",
                area="BE",
                summary="borrada en jira",
                status="Done",
            ),
        ]
    )
    session.flush()
    session.add(
        SpAdjustment(
            subtask_key="YAP-4",
            adjustment_type="bonus",
            amount_sp=10.0,
            reason="x",
            applied_by=pm.id,
            applied_at=datetime.utcnow(),
        )
    )
    session.flush()
    return pm


def test_find_stale_keys_detects_missing(test_session: Session) -> None:
    _seed_hierarchy(test_session)
    orch = _orch(test_session)

    # YAP-4 ya no existe en Jira; el resto sí
    live = {"YAP-1", "YAP-2", "YAP-3"}
    stale = orch.find_stale_keys(live, "YAP")

    assert stale["subtasks"] == ["YAP-4"]
    assert stale["stories"] == []
    assert stale["epics"] == []


def test_find_stale_keys_scoped_by_project_prefix(test_session: Session) -> None:
    _seed_hierarchy(test_session)
    # subtask de otro proyecto — no debe entrar al scope de YAP
    test_session.add(
        Subtask(
            jira_key="ABC-9",
            project_code="ABC",
            issue_type="Backend Sub-task",
            area="BE",
            summary="otro proyecto",
            status="Done",
        )
    )
    test_session.flush()
    orch = _orch(test_session)

    stale = orch.find_stale_keys({"YAP-1", "YAP-2", "YAP-3", "YAP-4"}, "YAP")
    assert stale["subtasks"] == []  # ABC-9 no se considera


def test_delete_stale_removes_subtask_and_cascades_adjustment(test_session: Session) -> None:
    _seed_hierarchy(test_session)
    orch = _orch(test_session)

    counts = orch.delete_stale({"subtasks": ["YAP-4"], "stories": [], "epics": []})
    test_session.commit()

    assert counts["subtasks"] == 1
    assert counts["sp_adjustments"] == 1
    assert test_session.get(Subtask, "YAP-4") is None
    assert test_session.get(Subtask, "YAP-3") is not None  # la viva no se toca
    # el ajuste dependiente se borró (CASCADE manual, pragma off)
    assert (
        test_session.query(SpAdjustment).filter_by(subtask_key="YAP-4").count() == 0
    )


def test_delete_stale_story_nulls_children(test_session: Session) -> None:
    _seed_hierarchy(test_session)
    orch = _orch(test_session)

    # borrar la story YAP-2 → los subtasks vivos deben quedar con parent NULL
    orch.delete_stale({"subtasks": [], "stories": ["YAP-2"], "epics": []})
    test_session.commit()

    assert test_session.get(Story, "YAP-2") is None
    child = test_session.get(Subtask, "YAP-3")
    assert child is not None
    assert child.parent_story_key is None
