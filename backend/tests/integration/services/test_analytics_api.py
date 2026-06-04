"""Integración: endpoints WP-07a analytics (throughput, cp-by-area, etc.)."""

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from forge.db.base import Base
from forge.db.models.cycle import Cycle
from forge.db.models.player import Player
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


def _seed(session: Session) -> None:
    today = date.today()
    start = today - timedelta(weeks=1)
    end = start + timedelta(days=4)
    iso = start.isocalendar()
    cycle = Cycle(
        id=1,
        iso_year=iso[0],
        iso_week=iso[1],
        name="Test-Cycle-01",
        start_date=start,
        end_date=end,
        status="closed",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(cycle)

    player = Player(
        id=1,
        jira_account_id="api-test-dev",
        display_name="API Dev",
        email="apidev@yapsi.com",
        area="BE",
        employment_type="internal",
        is_lead=False,
        is_active=True,
    )
    session.add(player)
    session.flush()

    for i in range(3):
        session.add(
            Subtask(
                jira_key=f"API-{i}",
                issue_type="Sub-task",
                summary=f"Test {i}",
                status="Done",
                area="BE",
                cp=5,
                cycle_id=1,
                assignee_player_id=1,
                qa_first_pass=True,
                dev_resp_biz_hours=10.0,
                qa_biz_hours=2.0,
                done_at=datetime.utcnow(),
                last_synced_at=datetime.utcnow(),
            )
        )
    session.commit()


class TestAnalyticsEndpoints:
    def test_throughput_returns_200(self, client: TestClient, session: Session) -> None:
        _seed(session)
        resp = client.get("/api/analytics/throughput?last_n=6")
        assert resp.status_code == 200
        data = resp.json()
        assert "cycles" in data
        assert data["total_cycles"] == 1

    def test_cp_by_area_returns_200(self, client: TestClient, session: Session) -> None:
        _seed(session)
        resp = client.get("/api/analytics/cp-by-area?scope=window")
        assert resp.status_code == 200
        data = resp.json()
        assert "areas" in data
        assert len(data["areas"]) == 1
        assert data["areas"][0]["area"] == "BE"
        assert data["areas"][0]["total_cp"] == 15

    def test_cp_per_day_by_dev_returns_200(self, client: TestClient, session: Session) -> None:
        _seed(session)
        resp = client.get("/api/analytics/cp-per-day-by-dev?scope=window")
        assert resp.status_code == 200
        data = resp.json()
        assert "devs" in data
        assert len(data["devs"]) == 1
        dev = data["devs"][0]
        assert dev["total_cp"] == 15
        assert dev["biz_days"] == 5
        assert dev["cp_per_day"] == 3.0

    def test_qa_first_pass_returns_200(
        self, client: TestClient, session: Session
    ) -> None:
        _seed(session)
        resp = client.get("/api/analytics/qa-first-pass-by-dev?scope=historical")
        assert resp.status_code == 200
        data = resp.json()
        assert "devs" in data
        assert "data_warning" not in data  # caveat removido tras fix ETL

    def test_time_in_status_returns_200(self, client: TestClient, session: Session) -> None:
        _seed(session)
        resp = client.get("/api/analytics/time-in-status?group_by=area&scope=window")
        assert resp.status_code == 200
        data = resp.json()
        assert "rows" in data
        assert data["group_by"] == "area"
        assert len(data["rows"]) == 1
        assert data["rows"][0]["display_name"] == "BE"
        assert data["rows"][0]["dev_resp_h"] == 30.0  # 3 subtasks × 10h

    def test_time_in_status_detail_returns_200(
        self, client: TestClient, session: Session
    ) -> None:
        _seed(session)
        resp = client.get("/api/analytics/time-in-status-detail?group_by=area&scope=window")
        assert resp.status_code == 200
        data = resp.json()
        assert "rows" in data
