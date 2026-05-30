"""Tests para BaseRepository usando Project como modelo concreto."""

import pytest
from sqlalchemy.orm import Session

from forge.db.models.project import Project
from forge.repositories.base import BaseRepository


class ProjectRepo(BaseRepository[Project, str]):
    """Instancia concreta del base para tests."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Project)


def _make_project(code: str, prefix: str = "[TEST]") -> Project:
    return Project(
        code=code,
        jira_prefix=prefix,
        internal_name=f"Project {code}",
        arena_name=f"Arena {code}",
        is_active=True,
    )


def test_get_returns_entity(test_session: Session) -> None:
    repo = ProjectRepo(test_session)
    project = _make_project("P01", "[YAPAPP]")
    test_session.add(project)
    test_session.flush()

    result = repo.get("P01")

    assert result is not None
    assert result.code == "P01"


def test_get_returns_none_when_missing(test_session: Session) -> None:
    repo = ProjectRepo(test_session)

    result = repo.get("NONEXISTENT")

    assert result is None


def test_create_persists_to_db(test_session: Session) -> None:
    repo = ProjectRepo(test_session)
    project = _make_project("P02", "[YAPCRM]")

    created = repo.create(project)

    assert created.code == "P02"
    assert repo.get("P02") is not None


def test_update_reflects_changes(test_session: Session) -> None:
    repo = ProjectRepo(test_session)
    project = _make_project("P03", "[YAPWEB]")
    repo.create(project)

    project.arena_name = "Updated Arena"
    repo.update(project)

    fetched = repo.get("P03")
    assert fetched is not None
    assert fetched.arena_name == "Updated Arena"


def test_delete_removes_entity(test_session: Session) -> None:
    repo = ProjectRepo(test_session)
    project = _make_project("P04", "[YAPMOB]")
    repo.create(project)

    repo.delete(project)

    assert repo.get("P04") is None


def test_list_all_returns_all(test_session: Session) -> None:
    repo = ProjectRepo(test_session)
    repo.create(_make_project("P05", "[A]"))
    repo.create(_make_project("P06", "[B]"))
    repo.create(_make_project("P07", "[C]"))

    results = repo.list_all()

    codes = {p.code for p in results}
    assert {"P05", "P06", "P07"}.issubset(codes)


def test_list_all_pagination(test_session: Session) -> None:
    repo = ProjectRepo(test_session)
    for i in range(5):
        repo.create(_make_project(f"PX{i}", f"[X{i}]"))

    page1 = repo.list_all(limit=2, offset=0)
    page2 = repo.list_all(limit=2, offset=2)

    assert len(page1) == 2
    assert len(page2) == 2
    assert {p.code for p in page1}.isdisjoint({p.code for p in page2})


def test_count_returns_correct_number(test_session: Session) -> None:
    repo = ProjectRepo(test_session)
    initial = repo.count()
    repo.create(_make_project("PC1", "[C1]"))
    repo.create(_make_project("PC2", "[C2]"))

    assert repo.count() == initial + 2
