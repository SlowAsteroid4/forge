"""Orquestador de sincronización con Jira."""

import json
from datetime import date as date_type
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from forge.core.config import get_settings
from forge.core.logging import get_logger
from forge.db.models.cycle import Cycle
from forge.db.models.epic import Epic
from forge.db.models.player import Player
from forge.db.models.story import Story
from forge.db.models.subtask import Subtask
from forge.etl.jira_client import JiraClient
from forge.etl.project_matcher import match_project
from forge.etl.quality_metrics import extract_quality_metrics
from forge.etl.time_metrics import extract_time_metrics

logger = get_logger(__name__)


class SyncOrchestrator:
    """Orquestador de sincronización completa con Jira."""

    def __init__(self, session: Session) -> None:
        """Inicializar con sesión de DB."""
        self.session = session
        self.client = JiraClient()
        self.settings = get_settings()

    async def sync_all(self, jql: str | None = None) -> dict[str, Any]:
        """
        Sincronizar todos los issues de Jira.

        Args:
            jql: Query JQL personalizada (default: issues actualizados en últimas 2 semanas)

        Returns:
            Estadísticas de la sincronización
        """
        if jql is None:
            jql = "project = YAP AND updated >= -14d ORDER BY updated DESC"

        logger.info(f"Iniciando sync con JQL: {jql}")

        stats = {
            "epics_created": 0,
            "epics_updated": 0,
            "stories_created": 0,
            "stories_updated": 0,
            "subtasks_created": 0,
            "subtasks_updated": 0,
            "errors": [],
        }

        # Paginar resultados con nextPageToken (API /rest/api/3/search/jql)
        next_page_token: str | None = None
        batch_size = self.settings.sync_batch_size

        while True:
            try:
                response = await self.client.search_issues(
                    jql=jql,
                    next_page_token=next_page_token,
                    max_results=batch_size,
                    expand="changelog",
                )
            except Exception as e:
                logger.error(f"Error en search_issues: {e}")
                stats["errors"].append(str(e))
                break

            issues = response.get("issues", [])
            if not issues:
                break

            # Procesar cada issue
            for issue_data in issues:
                try:
                    issue_type = issue_data.get("fields", {}).get("issuetype", {}).get("name")

                    if issue_type == "Epic":
                        self._sync_epic(issue_data, stats)
                    elif issue_type == "Story":
                        self._sync_story(issue_data, stats)
                    elif issue_type in [
                        "Sub-task",
                        "Subtask",
                        "Frontend Sub-Task",
                        "Backend Sub-task",
                        "Design Sub-task",
                        "Database Sub-task",
                        "Task",
                        "Bug",
                        "Coordination",
                    ]:
                        self._sync_subtask(issue_data, stats)
                    else:
                        logger.debug(
                            f"Issue {issue_data.get('key')} ignorado — tipo: '{issue_type}'"
                        )

                except Exception as e:
                    logger.error(f"Error procesando {issue_data.get('key')}: {e}")
                    stats["errors"].append(f"{issue_data.get('key')}: {str(e)}")

            # Commit por batch
            self.session.commit()

            # Siguiente página — la API nueva devuelve nextPageToken en lugar de total
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        logger.info(f"Sync completado: {stats}")
        return stats

    def _sync_epic(self, issue: dict[str, Any], stats: dict[str, int]) -> None:
        """Sincronizar Epic."""
        key = issue["key"]
        fields = issue["fields"]

        # Buscar si existe
        existing = self.session.get(Epic, key)

        epic_data = {
            "jira_key": key,
            "project_code": match_project(key, self.session),
            "summary": fields.get("summary", ""),
            "status": fields.get("status", {}).get("name", "Unknown"),
            "last_synced_at": datetime.utcnow(),
        }

        if existing:
            for k, v in epic_data.items():
                setattr(existing, k, v)
            stats["epics_updated"] += 1
        else:
            self.session.add(Epic(**epic_data))
            stats["epics_created"] += 1

    def _sync_story(self, issue: dict[str, Any], stats: dict[str, int]) -> None:
        """Sincronizar Story."""
        key = issue["key"]
        fields = issue["fields"]

        existing = self.session.get(Story, key)

        story_data = {
            "jira_key": key,
            "parent_epic_key": fields.get("parent", {}).get("key"),
            "summary": fields.get("summary", ""),
            "status": fields.get("status", {}).get("name", "Unknown"),
            "last_synced_at": datetime.utcnow(),
        }

        if existing:
            for k, v in story_data.items():
                setattr(existing, k, v)
            stats["stories_updated"] += 1
        else:
            self.session.add(Story(**story_data))
            stats["stories_created"] += 1

    def _sync_subtask(self, issue: dict[str, Any], stats: dict[str, int]) -> None:
        """Sincronizar Subtask."""
        key = issue["key"]
        fields = issue["fields"]

        existing = self.session.get(Subtask, key)

        # Extraer métricas (time_metrics ya incluye done_at derivado del changelog)
        time_metrics = extract_time_metrics(issue)
        quality_metrics = extract_quality_metrics(issue)

        # Inferir área del assignee
        assignee_id = self._get_player_id(fields.get("assignee"))
        area = self._infer_area(assignee_id) if assignee_id else "BE"  # Default BE

        # done_at viene de time_metrics (resolutiondate o última transición a Done)
        done_at: datetime | None = time_metrics.get("done_at")  # type: ignore[assignment]
        cycle_id = self._get_cycle_id(done_at=done_at)

        subtask_data = {
            "jira_key": key,
            "parent_story_key": fields.get("parent", {}).get("key"),
            "project_code": match_project(key, self.session),
            "issue_type": fields.get("issuetype", {}).get("name", "Sub-task"),
            "area": area,
            "summary": fields.get("summary", ""),
            "status": fields.get("status", {}).get("name", "Unknown"),
            "assignee_player_id": assignee_id,
            "cycle_id": cycle_id,
            "last_synced_at": datetime.utcnow(),
            "raw_changelog": json.dumps(issue.get("changelog", {})),
            **time_metrics,
            **quality_metrics,
        }

        if existing:
            # No sobrescribir CP si ya está aprobado
            if existing.cp_approved_at:
                subtask_data.pop("cp", None)
                subtask_data.pop("complexity_size", None)

            for k, v in subtask_data.items():
                setattr(existing, k, v)
            stats["subtasks_updated"] += 1
        else:
            self.session.add(Subtask(**subtask_data))
            stats["subtasks_created"] += 1

    def _get_player_id(self, assignee: dict | None) -> int | None:
        """Obtener player ID desde assignee de Jira."""
        if not assignee:
            return None

        account_id = assignee.get("accountId")
        if not account_id:
            return None

        stmt = select(Player.id).where(Player.jira_account_id == account_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def _infer_area(self, player_id: int) -> str:
        """Inferir área del player."""
        player = self.session.get(Player, player_id)
        return player.area if player else "BE"

    def _get_cycle_id(self, done_at: datetime | None) -> int | None:
        """
        Obtener cycle_id local que corresponde a este subtask.

        Estrategia: fecha-match — usar done_at (si existe) o hoy para
        encontrar qué ciclo cubre ese día por rango de fechas.
        Si no hay ciclo en rango (subtask muy antigua), retorna None y loguea.
        """
        ref_date = done_at.date() if done_at else date_type.today()
        stmt = (
            select(Cycle.id)
            .where(Cycle.start_date <= ref_date)
            .where(Cycle.end_date >= ref_date)
            .limit(1)
        )
        cycle_id = self.session.execute(stmt).scalar_one_or_none()
        if cycle_id is None:
            logger.debug(f"No cycle found for date {ref_date}; cycle_id will be NULL.")
        return cycle_id

    def _parse_datetime(self, date_str: str | None) -> datetime | None:
        """Parsear fecha de Jira."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return None
