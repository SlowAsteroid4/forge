"""Tests para ProjectRepository."""

from sqlalchemy.orm import Session

from forge.db.models.project import Project
from forge.repositories.project import ProjectRepository


def _make_project(
    code: str, prefix: str, internal: str = "Test", arena: str = "Arena", active: bool = True
) -> Project:
    return Project(
        code=code,
        jira_prefix=prefix,
        internal_name=internal,
        arena_name=arena,
        is_active=active,
    )


def test_get_by_jira_prefix_found(test_session: Session) -> None:
    repo = ProjectRepository(test_session)
    test_session.add(_make_project("P01", "[YAPAPP]"))
    test_session.flush()

    result = repo.get_by_jira_prefix("[YAPAPP]")

    assert result is not None
    assert result.code == "P01"


def test_get_by_jira_prefix_not_found(test_session: Session) -> None:
    repo = ProjectRepository(test_session)

    result = repo.get_by_jira_prefix("[NONEXISTENT]")

    assert result is None


def test_list_active_excludes_inactive(test_session: Session) -> None:
    repo = ProjectRepository(test_session)
    test_session.add(_make_project("P02", "[ACT]", active=True))
    test_session.add(_make_project("P03", "[INA]", active=False))
    test_session.flush()

    results = repo.list_active()

    codes = {p.code for p in results}
    assert "P02" in codes
    assert "P03" not in codes


def test_upsert_creates_when_not_exists(test_session: Session) -> None:
    repo = ProjectRepository(test_session)

    project = repo.upsert(
        {
            "code": "P04",
            "jira_prefix": "[NEW]",
            "internal_name": "New Project",
            "arena_name": "New Dungeon",
        }
    )

    assert project.code == "P04"
    assert repo.get("P04") is not None


def test_upsert_updates_when_exists(test_session: Session) -> None:
    repo = ProjectRepository(test_session)
    test_session.add(_make_project("P05", "[UPD]", internal="Old Name"))
    test_session.flush()

    updated = repo.upsert(
        {
            "code": "P05",
            "jira_prefix": "[UPD]",
            "internal_name": "New Name",
            "arena_name": "Arena",
        }
    )

    assert updated.internal_name == "New Name"
