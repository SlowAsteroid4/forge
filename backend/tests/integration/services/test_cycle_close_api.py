"""Tests de integración: endpoints cycle_admin (UC-05)."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from forge.db.base import Base
from forge.db.models.achievement import Achievement
from forge.db.models.audit_log import AuditLog
from forge.db.models.cycle import Cycle
from forge.db.models.leaderboard_snapshot import LeaderboardSnapshot
from forge.db.models.player import Player
from forge.db.models.sp_adjustment import SpAdjustment
from forge.db.models.subtask import Subtask
from forge.db.session import get_session
from forge.main import app


def _add_done_subtask(
    session: Session,
    *,
    jira_key: str,
    player_id: int,
    cycle_id: int,
    sp_final: float | None,
    cp: int | None = None,
    complexity_size: str | None = None,
) -> Subtask:
    st = Subtask(
        jira_key=jira_key,
        issue_type="Sub-task",
        area="BE",
        summary=f"Subtask {jira_key}",
        status="Done",
        assignee_player_id=player_id,
        cycle_id=cycle_id,
        sp_final=sp_final,
        cp=cp,
        complexity_size=complexity_size,
    )
    session.add(st)
    return st


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


# ── WP-23: errores estructurados con claves ────────────────────────────────


def test_blocking_errors_structured_with_issue_keys(
    client: TestClient, int_session: Session
) -> None:
    """La validación devuelve {type, message, issue_keys} con EXACTAMENTE las N claves."""
    player, cycle, _ = _seed_base(int_session)
    # 3 Done sin sp_final → bloqueo con sus 3 claves
    for k in ("YAP-NO-1", "YAP-NO-2", "YAP-NO-3"):
        _add_done_subtask(
            int_session, jira_key=k, player_id=player.id, cycle_id=cycle.id, sp_final=None
        )
    int_session.commit()

    resp = client.get(f"/api/admin/cycles/{cycle.id}/close-summary")
    assert resp.status_code == 200
    data = resp.json()

    assert data["can_close"] is False
    assert len(data["blocking_errors"]) == 1
    err = data["blocking_errors"][0]
    assert err["type"] == "done_without_sp_final"
    assert set(err["issue_keys"]) == {"YAP-NO-1", "YAP-NO-2", "YAP-NO-3"}
    assert data["jira_base_url"]  # configurado en .env de test/dev


def test_close_summary_is_read_only(client: TestClient, int_session: Session) -> None:
    """El endpoint de resumen (errores + top players) no escribe nada."""
    player, cycle, _ = _seed_base(int_session)
    _add_done_subtask(
        int_session, jira_key="YAP-RO-1", player_id=player.id, cycle_id=cycle.id, sp_final=None
    )
    int_session.commit()

    before_adj = int_session.query(SpAdjustment).count()
    before_null = (
        int_session.query(Subtask)
        .filter(Subtask.sp_final.is_(None))
        .count()
    )

    client.get(f"/api/admin/cycles/{cycle.id}/close-summary")
    client.get(f"/api/admin/cycles/{cycle.id}/close-summary")

    assert int_session.query(SpAdjustment).count() == before_adj
    assert (
        int_session.query(Subtask).filter(Subtask.sp_final.is_(None)).count()
        == before_null
    )


# ── WP-23: recalc del ciclo (frontera de seguridad) ────────────────────────


def test_recalc_populates_sp_final_and_respects_frontier(
    client: TestClient, int_session: Session
) -> None:
    """recalc escribe sp_final; NO toca sp_adjustments, cp, complexity_size; idempotente."""
    player, cycle, _ = _seed_base(int_session)
    # 2 Done sin sp_final (cp inmutable que NO debe cambiar)
    _add_done_subtask(
        int_session, jira_key="YAP-RC-1", player_id=player.id, cycle_id=cycle.id,
        sp_final=None, cp=None, complexity_size=None,
    )
    _add_done_subtask(
        int_session, jira_key="YAP-RC-2", player_id=player.id, cycle_id=cycle.id,
        sp_final=None, cp=2, complexity_size="S",
    )
    # Ledger preexistente que debe quedar intacto
    int_session.add(
        SpAdjustment(
            subtask_key="YAP-API-1",
            adjustment_type="penalty",
            catalog_code="D01",
            amount_sp=0.5,
            reason="seed penalty",
            applied_by=player.id,
            applied_at=datetime.utcnow(),
            cycle_id=cycle.id,
        )
    )
    int_session.commit()

    adj_before = int_session.query(SpAdjustment).count()
    cp_before = {
        s.jira_key: (s.cp, s.complexity_size)
        for s in int_session.query(Subtask).all()
    }

    resp = client.post(f"/api/admin/cycles/{cycle.id}/recalc", json={})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["recalculated"] == 2
    assert body["summary"]["can_close"] is True
    assert body["summary"]["blocking_errors"] == []

    int_session.expire_all()
    # sp_final poblado (no NULL) para las 2
    for k in ("YAP-RC-1", "YAP-RC-2"):
        st = int_session.get(Subtask, k)
        assert st.sp_final is not None

    # FRONTERA: ledger intacto
    assert int_session.query(SpAdjustment).count() == adj_before
    # FRONTERA: cp / complexity_size intactos
    cp_after = {
        s.jira_key: (s.cp, s.complexity_size)
        for s in int_session.query(Subtask).all()
    }
    assert cp_after == cp_before

    # audit_log registrado
    assert (
        int_session.query(AuditLog).filter_by(event_type="cycle_recalc").count() == 1
    )

    # Idempotente: segundo recalc no toca nada
    resp2 = client.post(f"/api/admin/cycles/{cycle.id}/recalc", json={})
    assert resp2.status_code == 200
    assert resp2.json()["recalculated"] == 0
    assert int_session.query(SpAdjustment).count() == adj_before


# ── WP-23: drill-down con reconciliación obligatoria ───────────────────────


def test_top_players_drilldown_reconciles_with_mvp_bonus(
    client: TestClient, int_session: Session
) -> None:
    """El desglose (issues + ajustes no-issue) suma EXACTO el SP de la fila."""
    player, cycle, _ = _seed_base(int_session)  # ya tiene YAP-API-1 sp_final=10, cp=3
    # Bono MVP player-level (subtask_key=None) → línea no-issue +10
    int_session.add(
        SpAdjustment(
            subtask_key=None,
            player_id=player.id,
            adjustment_type="mvp_bonus",
            catalog_code="B17",
            amount_sp=10.0,
            reason="MVP del ciclo de prueba con razón suficientemente larga",
            applied_by=player.id,
            applied_at=datetime.utcnow(),
            cycle_id=cycle.id,
        )
    )
    # Penalización LIGADA a issue → NO debe aparecer como línea no-issue
    int_session.add(
        SpAdjustment(
            subtask_key="YAP-API-1",
            adjustment_type="penalty",
            catalog_code="D01",
            amount_sp=2.0,
            reason="penalty atada a subtask",
            applied_by=player.id,
            applied_at=datetime.utcnow(),
            cycle_id=cycle.id,
        )
    )
    int_session.commit()

    resp = client.get(f"/api/admin/cycles/{cycle.id}/close-summary")
    assert resp.status_code == 200
    tp = next(p for p in resp.json()["top_players"] if p["player_id"] == player.id)

    # por_issue trae la subtask con su sp_final; ajustes_no_issue solo el bono MVP
    assert any(i["jira_key"] == "YAP-API-1" for i in tp["por_issue"])
    assert len(tp["ajustes_no_issue"]) == 1
    assert tp["ajustes_no_issue"][0]["label"] == "Bono MVP"
    assert tp["ajustes_no_issue"][0]["amount_sp"] == 10.0

    # RECONCILIACIÓN: Σ sp_final + Σ ajustes == sp de la fila
    issue_sum = sum(i["sp_final"] or 0.0 for i in tp["por_issue"])
    adj_sum = sum(a["amount_sp"] for a in tp["ajustes_no_issue"])
    assert round(issue_sum + adj_sum, 2) == tp["sp"]
    assert tp["sp"] == 20.0  # 10 (sp_final) + 10 (mvp bonus)
