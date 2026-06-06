"""Integración: GET /api/pulse/* (UC-16 Pulso Operativo, rediseño WP-16)."""

from __future__ import annotations

import json
import time
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from forge.db.base import Base
from forge.db.models.area_wip_limit import AreaWipLimit
from forge.db.models.player import Player
from forge.db.models.project import Project
from forge.db.models.subtask import Subtask
from forge.db.session import get_session
from forge.main import app

# ── Fixtures ──────────────────────────────────────────────────────────────────


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


# ── Seed ──────────────────────────────────────────────────────────────────────


def _seed(session: Session) -> None:
    for area, limit, excluded in [
        ("BE", 3, False), ("FE", 3, False), ("DESIGN", 4, False),
        ("DB", 5, False), ("QA", 5, True), ("PO", 5, True),
    ]:
        session.add(AreaWipLimit(area=area, wip_limit=limit, exclude_from_wip=excluded))

    session.add(Project(code="YAP", jira_prefix="YAP", internal_name="Yapsi", arena_name="Yapsi Arena"))

    p1 = Player(id=1, jira_account_id="j1", display_name="DevBE", email="be@y.com",
                area="BE", employment_type="internal", is_active=True)
    p2 = Player(id=2, jira_account_id="j2", display_name="DevFE", email="fe@y.com",
                area="FE", employment_type="internal", is_active=True)
    session.add_all([p1, p2])
    session.flush()

    now = datetime.utcnow()
    cl = json.dumps({"histories": []})
    session.add(Subtask(jira_key="YAP-1", summary="Task 1", status="In Progress",
                        area="BE", assignee_player_id=1, project_code="YAP",
                        last_synced_at=now, issue_type="Sub-task", raw_changelog=cl))
    session.add(Subtask(jira_key="YAP-2", summary="Task 2", status="In Review",
                        area="BE", assignee_player_id=1, project_code="YAP",
                        last_synced_at=now, issue_type="Sub-task", raw_changelog=cl))
    session.add(Subtask(jira_key="YAP-3", summary="Task 3", status="Ready",
                        area="FE", assignee_player_id=2, project_code="YAP",
                        last_synced_at=now, issue_type="Sub-task", raw_changelog=cl))
    session.add(Subtask(jira_key="YAP-4", summary="Task 4", status="Blocked",
                        area="BE", assignee_player_id=1, project_code="YAP",
                        last_synced_at=now, issue_type="Sub-task", raw_changelog=cl))
    session.add(Subtask(jira_key="YAP-5", summary="Task 5 Done", status="Done",
                        area="BE", assignee_player_id=1, project_code="YAP",
                        last_synced_at=now, issue_type="Sub-task", raw_changelog=cl))
    session.commit()


def _counter(data: dict, key: str) -> dict:
    return next(c for c in data["flow_counters"] if c["key"] == key)


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_pulse_now_status_200(client: TestClient, session: Session):
    _seed(session)
    resp = client.get("/api/pulse/now")
    assert resp.status_code == 200


def test_pulse_now_tiene_todas_las_secciones(client: TestClient, session: Session):
    _seed(session)
    data = client.get("/api/pulse/now").json()
    assert "flow_counters" in data
    assert "area_cards" in data
    assert "blocks" in data
    assert "day_movements" in data
    assert "aging_critical" in data
    assert "ready_queue" in data
    assert "generated_at" in data


def test_flow_counters_conteos_correctos(client: TestClient, session: Session):
    _seed(session)
    data = client.get("/api/pulse/now").json()
    assert [c["key"] for c in data["flow_counters"]] == [
        "backlog", "ready", "in_progress", "in_review", "ready_for_qa", "in_qa", "done",
    ]
    assert _counter(data, "ready")["count"] == 1
    assert _counter(data, "in_progress")["count"] == 1
    assert _counter(data, "in_review")["count"] == 1
    assert _counter(data, "done")["count"] == 1
    # 'Code Review' mapea a 'In Review'
    assert _counter(data, "in_review")["label"] == "Code Review"


def test_area_cards_excluye_qa_y_po(client: TestClient, session: Session):
    _seed(session)
    data = client.get("/api/pulse/now").json()
    areas = [card["area"] for card in data["area_cards"]]
    assert "QA" not in areas
    assert "PO" not in areas


def test_area_card_estructura_y_conteo(client: TestClient, session: Session):
    _seed(session)
    data = client.get("/api/pulse/now").json()
    be = next(c for c in data["area_cards"] if c["area"] == "BE")
    # BE activas: In Progress + In Review + Blocked = 3 (Done/Backlog excluidos)
    assert be["total_active"] == 3
    for group in be["by_status"]:
        assert "status" in group and "zone" in group and "count" in group
        for task in group["tasks"]:
            assert "jira_key" in task
            assert "assignee_name" in task
            assert "zone" in task
            assert "is_aggregate_team" in task


def test_pulse_blocks_detecta_bloqueados(client: TestClient, session: Session):
    _seed(session)
    data = client.get("/api/pulse/now").json()
    keys = [b["jira_key"] for b in data["blocks"]]
    assert "YAP-4" in keys


def test_dev_drilldown_endpoint(client: TestClient, session: Session):
    _seed(session)
    data = client.get("/api/pulse/dev/1").json()
    assert data["display_name"] == "DevBE"
    # p1: In Progress + In Review + Blocked = 3 activas (Done excluido)
    assert data["total"] == 3
    keys = {t["jira_key"] for t in data["tasks"]}
    assert keys == {"YAP-1", "YAP-2", "YAP-4"}
    assert data["is_aggregate_team"] is False


def test_pulse_filtro_area(client: TestClient, session: Session):
    _seed(session)
    data = client.get("/api/pulse/now?area=FE").json()
    assert _counter(data, "ready")["count"] == 1
    assert _counter(data, "in_progress")["count"] == 0
    assert all(c["area"] == "FE" for c in data["area_cards"])


def test_pulse_filtro_project_code(client: TestClient, session: Session):
    _seed(session)
    data_yap = client.get("/api/pulse/now?project_code=YAP").json()
    assert _counter(data_yap, "in_progress")["count"] >= 1

    data_xxx = client.get("/api/pulse/now?project_code=XXX").json()
    assert _counter(data_xxx, "in_progress")["count"] == 0


def test_pulse_filtro_player_id(client: TestClient, session: Session):
    _seed(session)
    data = client.get("/api/pulse/now?player_id=2").json()
    # Player 2 (FE) solo tiene 1 en Ready
    assert _counter(data, "ready")["count"] == 1
    assert _counter(data, "in_progress")["count"] == 0


def test_pulse_done_excluido_de_secciones(client: TestClient, session: Session):
    _seed(session)
    data = client.get("/api/pulse/now").json()
    all_keys = (
        [b["jira_key"] for b in data["blocks"]]
        + [a["jira_key"] for a in data["aging_critical"]]
        + [r["jira_key"] for r in data["ready_queue"]]
    )
    for card in data["area_cards"]:
        for group in card["by_status"]:
            all_keys += [t["jira_key"] for t in group["tasks"]]
    assert "YAP-5" not in all_keys


def test_pulse_no_escribe_en_gamificacion(client: TestClient, session: Session):
    """3 GETs al Pulso no deben modificar sp_adjustments ni leaderboard_snapshots."""
    _seed(session)

    def count(table: str) -> int:
        return session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0

    before_sp = count("sp_adjustments")
    before_lb = count("leaderboard_snapshots")

    for _ in range(3):
        client.get("/api/pulse/now")

    assert count("sp_adjustments") == before_sp
    assert count("leaderboard_snapshots") == before_lb


def test_pulse_performance(client: TestClient, session: Session):
    """El endpoint debe responder en <1s con datos de prueba."""
    _seed(session)
    start = time.perf_counter()
    resp = client.get("/api/pulse/now")
    elapsed = time.perf_counter() - start
    assert resp.status_code == 200
    assert elapsed < 1.0, f"Pulso tardó {elapsed:.2f}s (límite: 1s)"
