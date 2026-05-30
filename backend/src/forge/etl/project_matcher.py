"""Matcher de proyectos por prefix de Jira."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from forge.db.models.project import Project


def match_project(issue_key: str, session: Session) -> str | None:
    """
    Matchear issue a proyecto por prefix.

    Args:
        issue_key: Key del issue (ej: SIMPL-123)
        session: Sesión de DB

    Returns:
        Project code o None si no match
    """
    # Extraer prefix (ej: SIMPL-123 → SIMPL)
    prefix = issue_key.split("-")[0] if "-" in issue_key else issue_key

    # Buscar proyecto con ese prefix
    stmt = select(Project).where(Project.jira_prefix == prefix)
    project = session.execute(stmt).scalar_one_or_none()

    return project.code if project else None
