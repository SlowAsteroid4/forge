"""ProjectRepository — acceso a datos de proyectos (Dungeons)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from forge.db.models.project import Project
from forge.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project, str]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Project)

    def get_by_jira_prefix(self, prefix: str) -> Project | None:
        """Lookup por jira_prefix (usado por ETL ProjectMatcher)."""
        stmt = select(Project).where(Project.jira_prefix == prefix)
        return self._session.scalars(stmt).first()

    def list_active(self) -> list[Project]:
        """Solo proyectos activos."""
        stmt = select(Project).where(Project.is_active.is_(True))
        return list(self._session.scalars(stmt))

    def upsert(self, data: dict[str, Any]) -> Project:
        """Crea o actualiza un proyecto por code (para ETL)."""
        project = self.get(data["code"])
        if project is None:
            project = Project(**data)
            return self.create(project)
        for key, value in data.items():
            if key == "code":
                continue
            setattr(project, key, value)
        return self.update(project)
