"""Integración: endpoints UC-07 forecast (GET /epics, /epics/{key}, /recalculate)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from forge.db.base import Base
from forge.db.models.cycle import Cycle
from forge.db.models.epic import Epic
from forge.db.models.sp_adjustment import SpAdjustment
from forge.db.models.story import Story
from forge.db.models.subtask import Subtask
from forge.db.session import get_session
from forge.main import app

# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

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
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _setup_data(session: Session) -> Epic:
    """Crea 4 ciclos cerrados con data de velocity y 1 épica activa."""
    # 4 ciclos cerrados
    today = date.today()
    cycles = []
    for i in range(4):
        start = today - timedelta(weeks=4 - i)
        iso = start.isocalendar()
        c = Cycle(
            name=f"W-{i}",
            iso_year=iso[0],
            iso_week=iso[1],
            start_date=start,
            end_date=start + timedelta(days=4),
            status="closed",
        )
        session.add(c)
        cycles.append(c)
    session.flush()

    # Épica activa
    epic = Epic(
        jira_key="YAP-API01",
        summary="API Test Epic",
        status="In Progress",
        cp_total=0.0,
        last_synced_at=datetime.utcnow(),
    )
    session.add(epic)
    story = Story(
        jira_key="YAP-AS01",
        parent_epic_key="YAP-API01",
        summary="Story",
        status="In Progress",
        cp_raw=0.0,
        cp_total=0.0,
        n_areas=0,
        has_dependency_chain=False,
        overhead_factor=1.0,
        dependency_factor=1.0,
        last_synced_at=datetime.utcnow(),
    )
    session.add(story)
    session.flush()

    # Velocity data: BE hace 10 CP/ciclo
    for ci, c in enumerate(cycles):
        s = Subtask(
            jira_key=f"YAP-DONE-{ci}",
            issue_type="Sub-task",
            area="BE",
            summary="Done sub",
            status="Done",
            cp=10.0,
            parent_story_key="YAP-AS01",
            qa_attempts=0,
            review_rejections=0,
            m_calidad=1.0,
            m_eficiencia=1.0,
            m_dificultad=1.0,
            m_lider=1.0,
            m_cooperacion=1.0,
            sp_flat_bonus=0.0,
            sp_penalty=0.0,
            cp_approval_required=False,
            cp_modified_post_approval=False,
            last_synced_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            cycle_id=c.id,
            done_at=datetime.utcnow(),
        )
        session.add(s)

    # Subtask pendiente
    pend = Subtask(
        jira_key="YAP-PEND-01",
        issue_type="Sub-task",
        area="BE",
        summary="Pending",
        status="In Progress",
        cp=20.0,
        parent_story_key="YAP-AS01",
        qa_attempts=0,
        review_rejections=0,
        m_calidad=1.0,
        m_eficiencia=1.0,
        m_dificultad=1.0,
        m_lider=1.0,
        m_cooperacion=1.0,
        sp_flat_bonus=0.0,
        sp_penalty=0.0,
        cp_approval_required=False,
        cp_modified_post_approval=False,
        last_synced_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(pend)
    session.commit()
    return epic


# ──────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────

def test_list_epics_responds(client: TestClient, session: Session):
    _setup_data(session)
    r = client.get("/api/forecast/epics")
    assert r.status_code == 200
    body = r.json()
    assert "epics" in body
    assert body["total"] >= 1
    assert body["n_closed_cycles"] == 4


def test_list_epics_has_three_dates(client: TestClient, session: Session):
    _setup_data(session)
    r = client.get("/api/forecast/epics")
    assert r.status_code == 200
    epics = r.json()["epics"]
    with_cp = [e for e in epics if e["cp_total"] > 0]
    assert len(with_cp) >= 1
    e = with_cp[0]
    assert e["date_optimistic"] is not None
    assert e["date_realistic"] is not None
    assert e["date_conservative"] is not None
    # Fechas deben ser strings ISO
    assert e["date_optimistic"] <= e["date_realistic"] <= e["date_conservative"]


def test_epic_detail_has_areas(client: TestClient, session: Session):
    _setup_data(session)
    r = client.get("/api/forecast/epics/YAP-API01")
    assert r.status_code == 200
    body = r.json()
    assert "areas" in body
    assert len(body["areas"]) >= 1
    area = body["areas"][0]
    assert "velocity_avg" in area
    assert "weeks_optimistic" in area
    assert "weeks_realistic" in area
    assert "weeks_conservative" in area


def test_epic_detail_404(client: TestClient, session: Session):
    r = client.get("/api/forecast/epics/YAP-NOEXISTE")
    assert r.status_code == 404


def test_recalculate_returns_total(client: TestClient, session: Session):
    _setup_data(session)
    r = client.post("/api/forecast/recalculate")
    assert r.status_code == 200
    assert "total" in r.json()


def test_project_filter(client: TestClient, session: Session):
    _setup_data(session)
    r = client.get("/api/forecast/epics?project_code=NONEXISTENT")
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_epic_status_filter(client: TestClient, session: Session):
    _setup_data(session)
    r = client.get("/api/forecast/epics?epic_status=In+Progress")
    assert r.status_code == 200
    assert r.json()["total"] >= 1


# ──────────────────────────────────────────────────────────────
# Anti-regresión: 0 escrituras
# ──────────────────────────────────────────────────────────────

def test_read_only_no_writes(client: TestClient, session: Session):
    """GET forecast no escribe a sp_adjustments, subtasks ni cycles."""
    _setup_data(session)

    def count_rows(table_class) -> int:
        return session.execute(select(func.count()).select_from(table_class)).scalar_one()

    sp_before = count_rows(SpAdjustment)
    subtasks_before = count_rows(Subtask)
    cycles_before = count_rows(Cycle)

    # 3 GET requests
    client.get("/api/forecast/epics")
    client.get("/api/forecast/epics/YAP-API01")
    client.post("/api/forecast/recalculate")

    session.expire_all()
    sp_after = count_rows(SpAdjustment)
    subtasks_after = count_rows(Subtask)
    cycles_after = count_rows(Cycle)

    assert sp_before == sp_after, "sp_adjustments was modified"
    assert subtasks_before == subtasks_after, "subtasks was modified"
    assert cycles_before == cycles_after, "cycles was modified"
