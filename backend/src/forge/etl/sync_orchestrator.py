"""Orquestador de sincronización con Jira."""

import json
from datetime import date as date_type
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from forge.core.config import get_settings
from forge.core.logging import get_logger
from forge.db.models.audit_log import AuditLog
from forge.db.models.cycle import Cycle
from forge.db.models.epic import Epic
from forge.db.models.player import Player
from forge.db.models.sp_adjustment import SpAdjustment
from forge.db.models.story import Story
from forge.db.models.subtask import Subtask
from forge.etl.jira_client import JiraClient
from forge.etl.project_matcher import match_project
from forge.etl.quality_metrics import extract_quality_metrics
from forge.etl.time_metrics import extract_time_metrics
from forge.services.engine.cp_calculator import calculate_cp, needs_approval

logger = get_logger(__name__)

_DEFAULT_PRUNE_THRESHOLD_PCT = 0.05  # 5 %


class PruneGuardAError(Exception):
    """Poda abortada: supera el umbral de % de subtasks activas."""


class PruneGuardBError(Exception):
    """Poda abortada: subtask(s) a podar tiene CP aprobado."""


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
                        # Tipos de entrega estándar
                        "Sub-task",
                        "Subtask",
                        "Frontend Sub-Task",
                        "Backend Sub-task",
                        "Design Sub-task",
                        "Database Sub-task",
                        # Tipos de entrega adicionales (WP-07j — antes ignorados)
                        # Portan talla (customfield_10851) igual que los anteriores;
                        # Bug Sub-task y Test Sub-Task pueden no llevar talla → cp queda NULL (legítimo)
                        "Bug Sub-task",
                        "Discovery Sub-task",
                        "Infrastructure Sub-task",
                        "Test Sub-Task",
                        # Tipos de gestión / coordinación
                        "Task",
                        "Bug",
                        "Coordination",
                        # Tipo custom DB — hijo directo de Epic (WP-20 ajuste: sin parent Story)
                        "Database",
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

    # ──────────────────────────────────────────────────────────────
    # Reconciliación de borrados (prune)
    #
    # El sync es solo upsert: nunca elimina. Cuando un issue se borra en
    # Jira queda huérfano en la BD local. Estos métodos detectan esos
    # registros (keys locales que ya no existen en Jira) y los eliminan.
    # ──────────────────────────────────────────────────────────────

    async def fetch_live_keys(self, project_code: str) -> set[str]:
        """Traer TODOS los keys vivos del proyecto en Jira (sin filtro de fecha).

        Se piden 0 campos extra (expand vacío) para que sea rápido: solo
        necesitamos los keys para comparar contra la BD local.
        """
        jql = f"project = {project_code} ORDER BY created ASC"
        live: set[str] = set()
        next_page_token: str | None = None

        while True:
            response = await self.client.search_issues(
                jql=jql,
                next_page_token=next_page_token,
                max_results=self.settings.sync_batch_size,
                expand="",
            )
            issues = response.get("issues", [])
            for issue in issues:
                key = issue.get("key")
                if key:
                    live.add(key)

            next_page_token = response.get("nextPageToken")
            if not next_page_token or not issues:
                break

        return live

    def find_stale_keys(self, live_keys: set[str], project_code: str) -> dict[str, list[str]]:
        """Keys locales del proyecto que ya no existen en Jira.

        Subtasks ya podadas (pruned_at IS NOT NULL) se excluyen: ya fueron
        procesadas y re-correr el prune no debe duplicar reversiones.
        """
        prefix = f"{project_code}-"

        def _local(model: type[Epic] | type[Story]) -> list[str]:
            rows = self.session.execute(
                select(model.jira_key).where(model.jira_key.like(f"{prefix}%"))
            ).scalars().all()
            return [k for k in rows if k not in live_keys]

        # Subtasks: excluir las ya podadas para idempotencia
        subtask_rows = self.session.execute(
            select(Subtask.jira_key).where(
                Subtask.jira_key.like(f"{prefix}%"),
                Subtask.pruned_at.is_(None),
            )
        ).scalars().all()
        stale_subtasks = [k for k in subtask_rows if k not in live_keys]

        return {
            "epics": _local(Epic),
            "stories": _local(Story),
            "subtasks": stale_subtasks,
        }

    def prune_stale(
        self,
        stale: dict[str, list[str]],
        *,
        threshold_pct: float = _DEFAULT_PRUNE_THRESHOLD_PCT,
        allow_large_prune: bool = False,
        actor_player_id: int = 1,
    ) -> dict[str, int]:
        """Reconciliar obsoletos: soft-delete de subtasks + reversión append-only de SP.

        Para subtasks:
          - GUARDA A: aborta si se excede el umbral de % de subtasks activas.
          - GUARDA B: aborta si alguna subtask a podar tiene CP aprobado.
          - Por cada subtask: inserta prune_reversal por cada SpAdjustment original
            (amount_sp = -original.amount_sp, ledger-only) y marca pruned_at.
          - Las filas originales de SpAdjustment y Subtask quedan INTACTAS.

        Para stories y epics: borrado físico (no tienen sp_adjustments).
        """
        subtask_keys = stale.get("subtasks", [])
        story_keys = stale.get("stories", [])
        epic_keys = stale.get("epics", [])

        counts: dict[str, int] = {
            "subtasks_pruned": 0,
            "prune_reversals_inserted": 0,
            "stories": 0,
            "epics": 0,
        }

        # ── GUARDAS (solo para subtasks) ─────────────────────────────────────
        if subtask_keys:
            total_active: int = self.session.execute(
                select(func.count()).select_from(Subtask).where(Subtask.pruned_at.is_(None))
            ).scalar_one()

            # GUARDA A — umbral de volumen
            if not allow_large_prune and len(subtask_keys) > threshold_pct * max(total_active, 1):
                raise PruneGuardAError(
                    f"GUARDA A: la poda afectaría {len(subtask_keys)} subtask(s) "
                    f"({len(subtask_keys)/max(total_active,1)*100:.1f}% de {total_active} activas, "
                    f"umbral={threshold_pct*100:.0f}%). "
                    "Usa --allow-large-prune para forzar."
                )

            # GUARDA B — CP aprobado
            approved_stale = self.session.execute(
                select(Subtask.jira_key).where(
                    Subtask.jira_key.in_(subtask_keys),
                    Subtask.cp_approved_at.is_not(None),
                )
            ).scalars().all()
            if approved_stale:
                raise PruneGuardBError(
                    f"GUARDA B: {len(approved_stale)} subtask(s) a podar tienen CP aprobado. "
                    f"Revisión manual requerida: {list(approved_stale)}"
                )

            # ── Soft-delete + reversiones append-only ────────────────────────
            now = datetime.utcnow()
            for key in subtask_keys:
                subtask = self.session.get(Subtask, key)
                if subtask is None:
                    continue

                # Por cada SpAdjustment existente, insertar reversión ledger
                originals = self.session.execute(
                    select(SpAdjustment).where(SpAdjustment.subtask_key == key)
                ).scalars().all()

                for orig in originals:
                    reversal = SpAdjustment(
                        subtask_key=key,
                        adjustment_type="prune_reversal",
                        catalog_code=f"PRUNE:{orig.id}",
                        amount_sp=round(-orig.amount_sp, 2),  # signo opuesto (vault: append-only)
                        reason=(
                            f"prune: subtask eliminada/fusionada en Jira "
                            f"(revierte adj #{orig.id}, tipo={orig.adjustment_type})"
                        ),
                        applied_by=actor_player_id,
                        applied_at=now,
                        cycle_id=orig.cycle_id,
                        is_appealed=False,
                    )
                    self.session.add(reversal)
                    counts["prune_reversals_inserted"] += 1

                # Soft-delete: marcar como podada (NO borrar la fila)
                subtask.pruned_at = now
                subtask.prune_reason = "jira_prune: issue eliminado o fusionado en Jira"
                counts["subtasks_pruned"] += 1

        # ── Stories y epics: borrado físico (sin sp_adjustments asociados) ──
        if story_keys:
            self.session.execute(
                update(Subtask)
                .where(Subtask.parent_story_key.in_(story_keys))
                .values(parent_story_key=None)
            )
            counts["stories"] = self.session.execute(
                delete(Story).where(Story.jira_key.in_(story_keys))
            ).rowcount

        if epic_keys:
            self.session.execute(
                update(Story)
                .where(Story.parent_epic_key.in_(epic_keys))
                .values(parent_epic_key=None)
            )
            counts["epics"] = self.session.execute(
                delete(Epic).where(Epic.jira_key.in_(epic_keys))
            ).rowcount

        if any(counts[k] for k in ("subtasks_pruned", "stories", "epics")):
            self.session.add(
                AuditLog(
                    event_type="jira_prune",
                    entity_type="sync",
                    entity_id="prune",
                    actor_player_id=actor_player_id,
                    changes=json.dumps({"pruned_keys": stale, "counts": counts}),
                    timestamp=datetime.utcnow(),
                )
            )

        return counts

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

        # Inferir área del assignee; si no hay, inferir del issue_type (evita default ciego a BE)
        assignee_id = self._get_player_id(fields.get("assignee"))
        issue_type_str = fields.get("issuetype", {}).get("name", "Sub-task")
        area = (
            self._infer_area(assignee_id)
            if assignee_id
            else self._area_from_issue_type(issue_type_str)
        )

        # done_at viene de time_metrics (resolutiondate o última transición a Done)
        done_at: datetime | None = time_metrics.get("done_at")  # type: ignore[assignment]
        cycle_id = self._get_cycle_id(done_at=done_at)

        # Talla (complexity_size) desde customfield_10851 ("Complexity")
        complexity_option = fields.get("customfield_10851")
        complexity_size: str | None = None
        if isinstance(complexity_option, dict):
            raw_value = complexity_option.get("value")
            if raw_value:
                complexity_size = raw_value.strip().upper()

        cp = calculate_cp(complexity_size) if complexity_size else None
        cp_approval_required = needs_approval(complexity_size) if complexity_size else False

        # priority: campo estándar de Jira (no customfield) → fields.priority.name
        priority_field = fields.get("priority")
        priority: str | None = None
        if isinstance(priority_field, dict):
            priority = priority_field.get("name")

        # parent_story_key solo si el padre es una Story (no Epic).
        # "Database" issues son hijos directos de Epics → parent_story_key = None.
        _parent = fields.get("parent") or {}
        _parent_type = (_parent.get("fields") or {}).get("issuetype", {}).get("name", "")
        _parent_story_key: str | None = _parent.get("key") if _parent_type not in ("Epic",) else None

        subtask_data = {
            "jira_key": key,
            "parent_story_key": _parent_story_key,
            "project_code": match_project(key, self.session),
            "issue_type": fields.get("issuetype", {}).get("name", "Sub-task"),
            "area": area,
            "summary": fields.get("summary", ""),
            "status": fields.get("status", {}).get("name", "Unknown"),
            "assignee_player_id": assignee_id,
            "cycle_id": cycle_id,
            "complexity_size": complexity_size,
            "cp": cp,
            "cp_approval_required": cp_approval_required,
            "priority": priority,
            "last_synced_at": datetime.utcnow(),
            "raw_changelog": json.dumps(issue.get("changelog", {})),
            **time_metrics,
            **quality_metrics,
        }

        if existing:
            # AC-4.7/4.10: no sobrescribir CP si ya está aprobado
            if existing.cp_approved_at is not None:
                incoming_cp = subtask_data.pop("cp", None)
                incoming_size = subtask_data.pop("complexity_size", None)
                subtask_data.pop("cp_approval_required", None)
                cp_changed = (incoming_cp is not None and incoming_cp != existing.cp) or (
                    incoming_size is not None and incoming_size != existing.complexity_size
                )
                if cp_changed:
                    existing.cp_modified_post_approval = True
                    self.session.add(
                        AuditLog(
                            event_type="cp_change_attempted_post_approval",
                            entity_type="subtask",
                            entity_id=existing.jira_key,
                            actor_player_id=None,
                            changes=json.dumps(
                                {
                                    "approved_cp": existing.cp,
                                    "approved_size": existing.complexity_size,
                                    "jira_cp": incoming_cp,
                                    "jira_size": incoming_size,
                                }
                            ),
                            timestamp=datetime.utcnow(),
                        )
                    )

            for k, v in subtask_data.items():
                setattr(existing, k, v)

            # Sellar cp_proposed_at solo si es la primera vez que llega con aprobación requerida
            if cp_approval_required and existing.cp_proposed_at is None and existing.cp_approved_at is None:
                existing.cp_proposed_at = datetime.utcnow()

            stats["subtasks_updated"] += 1
        else:
            new_subtask = Subtask(**subtask_data)
            if cp_approval_required:
                new_subtask.cp_proposed_at = datetime.utcnow()
            self.session.add(new_subtask)
            stats["subtasks_created"] += 1

    def _get_player_id(self, assignee: dict[str, Any] | None) -> int | None:
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

    @staticmethod
    def _area_from_issue_type(issue_type: str) -> str:
        """Área canónica para tareas sin assignee, inferida del issue type.
        Evita el default ciego a 'BE' que contaminaba los conteos de área."""
        t = issue_type.lower()
        if "frontend" in t or "ui" in t:
            return "FE"
        if "design" in t:
            return "DESIGN"
        if "database" in t or "db" in t:
            return "DB"
        return "BE"

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
