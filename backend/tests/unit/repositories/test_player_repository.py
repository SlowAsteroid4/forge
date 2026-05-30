"""Tests para PlayerRepository."""

import pytest
from sqlalchemy.orm import Session

from forge.db.models.player import Player
from forge.repositories.player import PlayerRepository


def _make_player(
    jira_id: str,
    email: str,
    area: str = "BE",
    is_active: bool = True,
    is_lead: bool = False,
) -> Player:
    return Player(
        jira_account_id=jira_id,
        display_name=f"Dev {jira_id}",
        email=email,
        area=area,
        employment_type="internal",
        is_active=is_active,
        is_lead=is_lead,
    )


def test_get_by_jira_id_found(test_session: Session) -> None:
    repo = PlayerRepository(test_session)
    test_session.add(_make_player("jira-001", "dev1@yapsi.com"))
    test_session.flush()

    result = repo.get_by_jira_id("jira-001")

    assert result is not None
    assert result.jira_account_id == "jira-001"


def test_get_by_jira_id_not_found(test_session: Session) -> None:
    repo = PlayerRepository(test_session)

    result = repo.get_by_jira_id("nonexistent-id")

    assert result is None


def test_get_by_email_found(test_session: Session) -> None:
    repo = PlayerRepository(test_session)
    test_session.add(_make_player("jira-002", "unique@yapsi.com"))
    test_session.flush()

    result = repo.get_by_email("unique@yapsi.com")

    assert result is not None
    assert result.email == "unique@yapsi.com"


def test_list_active_excludes_inactive_players(test_session: Session) -> None:
    repo = PlayerRepository(test_session)
    test_session.add(_make_player("j-active", "active@yapsi.com", is_active=True))
    test_session.add(_make_player("j-inactive", "inactive@yapsi.com", is_active=False))
    test_session.flush()

    results = repo.list_active()

    jira_ids = {p.jira_account_id for p in results}
    assert "j-active" in jira_ids
    assert "j-inactive" not in jira_ids


def test_list_active_filters_by_area(test_session: Session) -> None:
    repo = PlayerRepository(test_session)
    test_session.add(_make_player("j-be", "be@yapsi.com", area="BE"))
    test_session.add(_make_player("j-fe", "fe@yapsi.com", area="FE"))
    test_session.flush()

    results = repo.list_active(area="BE")

    jira_ids = {p.jira_account_id for p in results}
    assert "j-be" in jira_ids
    assert "j-fe" not in jira_ids


def test_list_active_no_filter_returns_all_areas(test_session: Session) -> None:
    repo = PlayerRepository(test_session)
    test_session.add(_make_player("j-be2", "be2@yapsi.com", area="BE"))
    test_session.add(_make_player("j-fe2", "fe2@yapsi.com", area="FE"))
    test_session.add(_make_player("j-qa2", "qa2@yapsi.com", area="QA"))
    test_session.flush()

    results = repo.list_active()

    jira_ids = {p.jira_account_id for p in results}
    assert {"j-be2", "j-fe2", "j-qa2"}.issubset(jira_ids)


def test_list_leads_returns_only_leads(test_session: Session) -> None:
    repo = PlayerRepository(test_session)
    test_session.add(_make_player("j-lead", "lead@yapsi.com", is_lead=True))
    test_session.add(_make_player("j-nonlead", "nonlead@yapsi.com", is_lead=False))
    test_session.flush()

    results = repo.list_leads()

    jira_ids = {p.jira_account_id for p in results}
    assert "j-lead" in jira_ids
    assert "j-nonlead" not in jira_ids


def test_list_for_leaderboard_excludes_po_and_pm(test_session: Session) -> None:
    repo = PlayerRepository(test_session)
    test_session.add(_make_player("j-dev", "dev@yapsi.com", area="BE"))
    test_session.add(_make_player("j-pm", "pm@yapsi.com", area="PM"))
    test_session.add(_make_player("j-po", "po@yapsi.com", area="PO"))
    test_session.flush()

    results = repo.list_for_leaderboard()

    jira_ids = {p.jira_account_id for p in results}
    assert "j-dev" in jira_ids
    assert "j-pm" not in jira_ids
    assert "j-po" not in jira_ids


def test_upsert_creates_when_not_exists(test_session: Session) -> None:
    repo = PlayerRepository(test_session)

    player = repo.upsert_by_jira_id(
        {
            "jira_account_id": "new-jira-id",
            "display_name": "New Dev",
            "email": "new@yapsi.com",
            "area": "FE",
            "employment_type": "internal",
        }
    )

    assert player.jira_account_id == "new-jira-id"
    assert repo.get_by_jira_id("new-jira-id") is not None


def test_upsert_updates_when_exists(test_session: Session) -> None:
    repo = PlayerRepository(test_session)
    test_session.add(_make_player("j-existing", "existing@yapsi.com", area="BE"))
    test_session.flush()

    updated = repo.upsert_by_jira_id(
        {
            "jira_account_id": "j-existing",
            "display_name": "Updated Name",
            "email": "existing@yapsi.com",
            "area": "FE",
            "employment_type": "internal",
        }
    )

    assert updated.display_name == "Updated Name"
    assert updated.area == "FE"
