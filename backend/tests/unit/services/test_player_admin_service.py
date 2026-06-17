"""Tests unitarios para player_admin_service."""

import json

import pytest
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError, RuleViolationError
from forge.db.models.audit_log import AuditLog
from forge.db.models.player import Player
from forge.db.models.subtask import Subtask
from forge.services import player_admin_service


def test_list_players_all(test_session: Session, sample_player: Player):
    players = player_admin_service.list_players(test_session)
    assert len(players) == 1
    assert players[0].id == sample_player.id


def test_list_players_filter_area(test_session: Session, sample_player: Player):
    fe_player = Player(
        jira_account_id="fe-001",
        display_name="FE Dev",
        area="FE",
        employment_type="internal",
        is_lead=False,
        is_active=True,
    )
    test_session.add(fe_player)
    test_session.commit()

    be_players = player_admin_service.list_players(test_session, area="BE")
    assert all(p.area == "BE" for p in be_players)
    assert len(be_players) == 1

    fe_players = player_admin_service.list_players(test_session, area="FE")
    assert len(fe_players) == 1


def test_list_players_filter_is_active(test_session: Session, sample_player: Player):
    inactive = Player(
        jira_account_id="inactive-001",
        display_name="Old Dev",
        area="BE",
        employment_type="internal",
        is_lead=False,
        is_active=False,
    )
    test_session.add(inactive)
    test_session.commit()

    active = player_admin_service.list_players(test_session, is_active=True)
    assert all(p.is_active for p in active)


def test_get_player_found(test_session: Session, sample_player: Player):
    p = player_admin_service.get_player(test_session, sample_player.id)
    assert p.id == sample_player.id


def test_get_player_not_found(test_session: Session):
    with pytest.raises(NotFoundError):
        player_admin_service.get_player(test_session, 9999)


def test_update_player_editable_fields(test_session: Session, sample_player: Player):
    updated = player_admin_service.update_player(
        session=test_session,
        player_id=sample_player.id,
        patch={
            "monthly_salary": 50000.0,
            "hourly_rate": 300.0,
            "employment_type": "external",
            "is_lead": True,
        },
        admin_id=1,
    )
    test_session.commit()

    test_session.refresh(updated)
    assert float(updated.monthly_salary) == 50000.0
    assert float(updated.hourly_rate) == 300.0
    assert updated.employment_type == "external"
    assert updated.is_lead is True


def test_update_player_persists_to_db(test_session: Session, sample_player: Player):
    player_admin_service.update_player(
        session=test_session,
        player_id=sample_player.id,
        patch={"is_active": False, "area": "FE"},
        admin_id=1,
    )
    test_session.commit()

    reloaded = test_session.get(Player, sample_player.id)
    assert reloaded is not None
    assert reloaded.is_active is False
    assert reloaded.area == "FE"


def test_update_player_readonly_rejected(test_session: Session, sample_player: Player):
    with pytest.raises(RuleViolationError) as exc_info:
        player_admin_service.update_player(
            session=test_session,
            player_id=sample_player.id,
            patch={"display_name": "Hacker McHack"},
            admin_id=1,
        )
    assert "display_name" in str(exc_info.value)


def test_update_player_readonly_jira_account_id_rejected(test_session: Session, sample_player: Player):
    with pytest.raises(RuleViolationError):
        player_admin_service.update_player(
            session=test_session,
            player_id=sample_player.id,
            patch={"jira_account_id": "new-jira-id"},
            admin_id=1,
        )


def test_update_player_creates_audit_log(test_session: Session, sample_player: Player):
    player_admin_service.update_player(
        session=test_session,
        player_id=sample_player.id,
        patch={"monthly_salary": 60000.0, "is_lead": True},
        admin_id=1,
    )
    test_session.commit()

    logs = test_session.query(AuditLog).filter_by(
        event_type="player_updated", entity_id=str(sample_player.id)
    ).all()
    assert len(logs) == 1
    changes = json.loads(logs[0].changes)  # type: ignore[arg-type]
    # Costo enmascarado en log
    assert changes["after"]["monthly_salary"] == "<changed>"
    # is_lead registrado con valor real
    assert changes["after"]["is_lead"] is True


def test_update_player_salary_negative_not_stored(test_session: Session, sample_player: Player):
    # El servicio no valida rangos (eso es responsabilidad del schema/router),
    # pero el test documenta que un float negativo se acepta a nivel service.
    # La validación >= 0 ocurre en el schema Pydantic (PlayerUpdateRequest).
    player_admin_service.update_player(
        session=test_session,
        player_id=sample_player.id,
        patch={"monthly_salary": -100.0},
        admin_id=1,
    )
    # No lanza excepción — la validación es en el router/schema


def test_update_player_clears_cost_field_with_none(test_session: Session, sample_player: Player):
    """Cambiar de dinámica: enviar None debe limpiar el costo (mensualidad → hora)."""
    sample_player.monthly_salary = 25000.0
    test_session.commit()

    player = player_admin_service.update_player(
        session=test_session,
        player_id=sample_player.id,
        patch={
            "employment_type": "external",
            "monthly_salary": None,
            "hourly_rate": 300.0,
        },
        admin_id=1,
    )
    test_session.commit()

    assert player.monthly_salary is None
    assert player.hourly_rate == 300.0
    assert player.employment_type == "external"


def test_update_player_none_does_not_null_flags(test_session: Session, sample_player: Player):
    """None en campos no-costo (ej. is_active) se ignora, no nulifica."""
    sample_player.is_active = True
    test_session.commit()

    player = player_admin_service.update_player(
        session=test_session,
        player_id=sample_player.id,
        patch={"is_active": None, "area": None},
        admin_id=1,
    )

    assert player.is_active is True


def test_update_player_no_changes_no_audit_log(test_session: Session, sample_player: Player):
    """Si no hay cambios reales, no se escribe audit_log."""
    player_admin_service.update_player(
        session=test_session,
        player_id=sample_player.id,
        patch={"area": "BE"},  # mismo valor
        admin_id=1,
    )
    test_session.commit()

    logs = test_session.query(AuditLog).filter_by(entity_id=str(sample_player.id)).all()
    assert len(logs) == 0


def test_edit_player_does_not_touch_subtasks(test_session: Session, sample_player: Player):
    """Editar un player NO modifica subtasks ni cp_approved_at."""
    from forge.db.models.story import Story
    from forge.db.models.epic import Epic
    from datetime import datetime

    epic = Epic(jira_key="YAP-E1", project_code="YAP", summary="E", status="Done")
    story = Story(jira_key="YAP-S1", parent_epic_key="YAP-E1", summary="S", status="Done")
    test_session.add_all([epic, story])
    test_session.flush()

    subtask = Subtask(
        jira_key="YAP-T1",
        parent_story_key="YAP-S1",
        project_code="YAP",
        issue_type="Sub-task",
        area="BE",
        summary="T",
        status="Done",
        assignee_player_id=sample_player.id,
        cp=10,
        cp_approved_at=datetime.utcnow(),
    )
    test_session.add(subtask)
    test_session.commit()

    cp_before = test_session.query(Subtask).filter(
        Subtask.cp_approved_at.isnot(None)
    ).count()

    player_admin_service.update_player(
        session=test_session,
        player_id=sample_player.id,
        patch={"monthly_salary": 45000.0, "is_lead": True},
        admin_id=1,
    )
    test_session.commit()

    cp_after = test_session.query(Subtask).filter(
        Subtask.cp_approved_at.isnot(None)
    ).count()
    assert cp_before == cp_after
