"""Tests de integración: endpoints cycle_admin (UC-05)."""

from __future__ import annotations

import pytest
from datetime import date, datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from forge.db.base import Base
from forge.db.models.achievement import Achievement
from forge.db.models.cycle import Cycle
from forge.db.models.leaderboard_snapshot import LeaderboardSnapshot
from forge.db.models.player import Player
from forge.db.models.sp_adjustment import SpAdjustment
from forge.db.models.subtask import Subtask
from forge.db.session import get_session
from forge.main import app


@pytest.fixture
def int_db_engine():
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
def int_session(int_db_engine):
    Sess = sessionmaker(bind=int_db_engine)
    s = Sess()
    yield s
    s.close()


@pytest.fixture
def client(int_session: Session):
    app.dependency_overrides[get_session] = lambda: int_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _seed_base(session: Session):
    """Crea player, cycle activo, subtask Done con sp_final, achievement ACH04 y ciclo planned."""
    player = Player(
        jira_account_id="jira-api-1",
        display_name="API Dev",
        email="apidev@yapsi.com",
        area="BE",
        employment_type="internal",
        is_lead=False,
        is_active=True,
    )
    session.add(player)
    session.flush()

    cycle = Cycle(
        name="Ciclo 2026-W22",
        iso_year=2026,
        iso_week=22,
        start_date=date(2026, 5, 25),
        end_date=date(2026, 5, 29),
        status="active",
    )
    session.add(cycle)
    session.flush()

    st = Subtask(
        jira_key="YAP-API-1",
        issue_type="Sub-task",
        area="BE",
        summary="Test API subtask",
        status="Done",
        assignee_player_id=player.id,
        cycle_id=cycle.id,
        sp_final=10.0,
        cp=3,
    )
    session.add(st)

    ach = Achievement(
        code="ACH04",
        name="Primer MVP",
        description="Obtuviste el reconocimiento de MVP por primera vez.",
        rarity="rare",
        sp_bonus=0,
        unlock_condition_code="mvp_weekly_first",
        is_active=True,
    )
    session.add(ach)

    next_cycle = Cycle(
        name="Ciclo 2026-W23",
        iso_year=2026,
        iso_week=23,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 5),
        status="planned",
    )
    session.add(next_cycle)
    session.commit()

    return player, cycle, next_cycle


def test_get_mvp_candidates_200(client: TestClient, int_session: Session) -> None:
    player, cycle, _ = _seed_base(int_session)
    resp = client.get(f"/api/admin/cycles/{cycle.id}/mvp-candidates")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["player_id"] == player.id


def test_get_close_summary_200(client: TestClient, int_session: Session) -> None:
    _, cycle, _ = _seed_base(int_session)
    resp = client.get(f"/api/admin/cycles/{cycle.id}/close-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_close"] is True
    assert data["kpis"]["subtasks_done"] == 1


def test_close_cycle_end_to_end(client: TestClient, int_session: Session) -> None:
    """Cierre completo en BD de test: +5 SP, ACH04, snapshot, siguiente activo."""
    player, cycle, next_cycle = _seed_base(int_session)

    resp = client.post(
        f"/api/admin/cycles/{cycle.id}/close",
        json={
            "mvp_player_id": player.id,
            "mvp_reason": "Excelente semana con entregas a tiempo y calidad demostrada",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "closed"
    assert data["mvp_player_id"] == player.id

    # +5 SP aplicado
    adj = int_session.query(SpAdjustment).filter_by(
        player_id=player.id, adjustment_type="mvp_bonus"
    ).first()
    assert adj is not None
    assert adj.amount_sp == 5.0

    # ACH04 desbloqueado
    from forge.db.models.achievement_unlock import AchievementUnlock
    unlock = int_session.query(AchievementUnlock).filter_by(
        player_id=player.id, achievement_code="ACH04"
    ).first()
    assert unlock is not None

    # LeaderboardSnapshot weekly generado
    snap = int_session.query(LeaderboardSnapshot).filter_by(
        cycle_id=cycle.id, period_type="weekly"
    ).first()
    assert snap is not None

    # Siguiente ciclo activo
    int_session.refresh(next_cycle)
    assert next_cycle.status == "active"


def test_close_cycle_invalid_reason(client: TestClient, int_session: Session) -> None:
    """mvp_reason corta retorna 422."""
    player, cycle, _ = _seed_base(int_session)
    resp = client.post(
        f"/api/admin/cycles/{cycle.id}/close",
        json={"mvp_player_id": player.id, "mvp_reason": "Corto"},
    )
    assert resp.status_code == 422


def test_get_mvp_history_200(client: TestClient, int_session: Session) -> None:
    """mvp-history retorna 200 vacío cuando no hay ciclos cerrados."""
    _seed_base(int_session)
    resp = client.get("/api/admin/cycles/mvp-history")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
