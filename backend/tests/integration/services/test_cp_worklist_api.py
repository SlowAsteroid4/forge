"""Integración: GET /api/cp-worklist — subtasks sin CP por apartado + XXL (WP-24)."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from forge.db.base import Base
from forge.db.models.audit_log import AuditLog
from forge.db.models.epic import Epic
from forge.db.models.story import Story
from forge.db.models.subtask import Subtask
from forge.db.session import get_session
from forge.main import app


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def session(db_engine):
    SessionLocal = sessionmaker(bind=db_engine)
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture
def client(session: Session):
    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _add_subtask(session: Session, **kwargs) -> Subtask:
    defaults = {
        "jira_key": "YAP-API1",
        "issue_type": "Sub-task",
        "area": "BE",
        "summary": "API test subtask",
        "status": "Backlog",
        "last_synced_at": datetime.utcnow(),
        "complexity_size": None,
        "cp": None,
    }
    defaults.update(kwargs)
    st = Subtask(**defaults)
    session.add(st)
    session.commit()
    return st


def _add_hierarchy(session: Session, epic_summary: str, epic_key: str, story_key: str) -> None:
    session.add(Epic(jira_key=epic_key, summary=epic_summary, status="In Progress"))
    session.add(
        Story(
            jira_key=story_key,
            parent_epic_key=epic_key,
            summary=f"Story de {epic_key}",
            status="In Progress",
        )
    )
    session.commit()


def test_worklist_empty(client: TestClient) -> None:
    r = client.get("/api/cp-worklist")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["groups"] == []
    assert data["xxl_total"] == 0


def test_worklist_groups_by_apartado_with_sin_apartado(
    client: TestClient, session: Session
) -> None:
    """Agrupa por prefijo [XXX] de la épica; sin prefijo/sin story → 'Sin apartado' al final."""
    _add_hierarchy(session, "[YPAPP] Módulo pagos", "YAP-E1", "YAP-S1")
    _add_hierarchy(session, "Version Container - [3.0]", "YAP-E2", "YAP-S2")

    # Sin CP, bajo apartado YPAPP
    _add_subtask(session, jira_key="YAP-1", parent_story_key="YAP-S1")
    # Sin CP, bajo épica sin prefijo de área → Sin apartado
    _add_subtask(session, jira_key="YAP-2", parent_story_key="YAP-S2")
    # Sin CP, huérfana de story → Sin apartado
    _add_subtask(session, jira_key="YAP-3", parent_story_key=None)
    # CON CP → no aparece en el worklist
    _add_subtask(session, jira_key="YAP-4", complexity_size="M", cp=3)

    r = client.get("/api/cp-worklist")
    assert r.status_code == 200
    data = r.json()

    assert data["total"] == 3
    names = [g["apartado"] for g in data["groups"]]
    assert names == ["YPAPP", "Sin apartado"]

    ypapp = data["groups"][0]
    assert ypapp["count"] == 1
    assert ypapp["items"][0]["jira_key"] == "YAP-1"

    sin_ap = data["groups"][1]
    assert sin_ap["count"] == 2
    assert {i["jira_key"] for i in sin_ap["items"]} == {"YAP-2", "YAP-3"}


def test_worklist_includes_xxl_section(client: TestClient, session: Session) -> None:
    """XXL detectadas van en su sección aparte, no en los grupos sin-CP."""
    _add_subtask(session, jira_key="YAP-XXL", complexity_size="XXL", cp=13)
    _add_subtask(session, jira_key="YAP-NOCP")

    r = client.get("/api/cp-worklist")
    data = r.json()

    assert data["xxl_total"] == 1
    assert data["xxl_items"][0]["jira_key"] == "YAP-XXL"
    # La XXL tiene cp=13 (no NULL) → no cuenta en el worklist sin-CP
    assert data["total"] == 1


def test_worklist_excludes_pruned(client: TestClient, session: Session) -> None:
    _add_subtask(session, jira_key="YAP-PRUNED", pruned_at=datetime.utcnow())
    r = client.get("/api/cp-worklist")
    assert r.json()["total"] == 0


def test_worklist_is_read_only(client: TestClient, session: Session) -> None:
    """GET no escribe nada: ni audit_log ni cambios en la subtask."""
    st = _add_subtask(session, jira_key="YAP-RO")
    before = (st.cp, st.complexity_size, st.cp_approved_at, st.updated_at)

    r = client.get("/api/cp-worklist")
    assert r.status_code == 200

    session.expire_all()
    st2 = session.get(Subtask, "YAP-RO")
    assert st2 is not None
    assert (st2.cp, st2.complexity_size, st2.cp_approved_at, st2.updated_at) == before
    audit_count = session.scalar(select(func.count()).select_from(AuditLog))
    assert audit_count == 0


def test_old_approval_endpoints_are_gone(client: TestClient) -> None:
    """WP-24: el flujo manual fue retirado — los endpoints viejos no existen."""
    assert client.get("/api/cp-approvals/pending").status_code in (404, 405)
    assert client.post("/api/cp-approvals/YAP-1/approve", json={}).status_code in (404, 405)
    assert client.post("/api/cp-approvals/YAP-1/adjust", json={}).status_code in (404, 405)
    assert client.post("/api/cp-approvals/YAP-1/reject", json={}).status_code in (404, 405)
