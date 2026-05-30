"""Integración: endpoints UC-04 cp-approvals."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from forge.db.base import Base
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
        "status": "Done",
        "last_synced_at": datetime.utcnow(),
        "complexity_size": "L",
        "cp": 5,
        "cp_approval_required": True,
        "cp_modified_post_approval": False,
    }
    defaults.update(kwargs)
    st = Subtask(**defaults)
    session.add(st)
    session.commit()
    return st


def test_list_pending_empty(client: TestClient) -> None:
    r = client.get("/api/cp-approvals/pending")
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_list_pending_returns_item(client: TestClient, session: Session) -> None:
    _add_subtask(session)
    r = client.get("/api/cp-approvals/pending")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["jira_key"] == "YAP-API1"


def test_list_xxl_detected(client: TestClient, session: Session) -> None:
    _add_subtask(
        session,
        jira_key="YAP-XXL9",
        complexity_size="XXL",
        cp=13,
        cp_approval_required=False,
    )
    r = client.get("/api/cp-approvals/xxl-detected")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["jira_key"] == "YAP-XXL9"


def test_get_detail_not_found(client: TestClient) -> None:
    r = client.get("/api/cp-approvals/YAP-NOPE")
    assert r.status_code == 404


def test_get_detail_ok(client: TestClient, session: Session) -> None:
    _add_subtask(session)
    r = client.get("/api/cp-approvals/YAP-API1")
    assert r.status_code == 200
    assert r.json()["complexity_size"] == "L"


def test_approve_endpoint(client: TestClient, session: Session) -> None:
    _add_subtask(session)
    r = client.post("/api/cp-approvals/YAP-API1/approve")
    assert r.status_code == 200
    data = r.json()
    assert data["cp_approved_at"] is not None
    assert data["cp_approval_required"] is False


def test_approve_immutable_409(client: TestClient, session: Session) -> None:
    _add_subtask(session, cp_approved_at=datetime.utcnow(), cp_approved_by=1)
    r = client.post("/api/cp-approvals/YAP-API1/approve")
    assert r.status_code == 409


def test_adjust_endpoint(client: TestClient, session: Session) -> None:
    _add_subtask(session)
    r = client.post(
        "/api/cp-approvals/YAP-API1/adjust",
        json={"new_size": "M", "reason": "Reestimación con el equipo"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["complexity_size"] == "M"
    assert data["cp"] == 3


def test_adjust_xxl_forbidden(client: TestClient, session: Session) -> None:
    _add_subtask(session)
    r = client.post(
        "/api/cp-approvals/YAP-API1/adjust",
        json={"new_size": "XXL", "reason": "No deberia pasar esto"},
    )
    assert r.status_code == 422


def test_reject_endpoint(client: TestClient, session: Session) -> None:
    _add_subtask(session)
    r = client.post(
        "/api/cp-approvals/YAP-API1/reject",
        json={"reason": "Falta descripción técnica completa"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["cp_rejection_reason"] == "Falta descripción técnica completa"
    assert data["cp_approved_at"] is None


def test_mark_xxl_notified(client: TestClient, session: Session) -> None:
    _add_subtask(
        session,
        jira_key="YAP-XXL8",
        complexity_size="XXL",
        cp=13,
        cp_approval_required=False,
    )
    r = client.post("/api/cp-approvals/YAP-XXL8/mark-xxl-notified")
    assert r.status_code == 200


def test_filter_by_area(client: TestClient, session: Session) -> None:
    _add_subtask(session, jira_key="YAP-BE1", area="BE")
    _add_subtask(session, jira_key="YAP-FE1", area="FE")
    r = client.get("/api/cp-approvals/pending?area=FE")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["jira_key"] == "YAP-FE1"
