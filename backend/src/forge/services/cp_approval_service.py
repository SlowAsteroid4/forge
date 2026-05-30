"""CpApprovalService — UC-04: flujo de aprobación de CP para subtasks L/XL/XXL."""

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from forge.core.exceptions import CPImmutableError, NotFoundError, RuleViolationError
from forge.db.models.audit_log import AuditLog
from forge.db.models.subtask import Subtask
from forge.repositories.subtask import SubtaskRepository
from forge.services.engine.cp_calculator import assign_cp

_VALID_SIZES = frozenset({"XS", "S", "M", "L", "XL"})
_OVERDUE_DAYS = 3


class CpApprovalService:
    """Gestiona el flujo de aprobación de CP: listar, aprobar, ajustar, rechazar."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = SubtaskRepository(session)

    # ── Listados ──────────────────────────────────────────────────────────

    def list_pending(
        self,
        area: str | None = None,
        player_id: int | None = None,
        project_code: str | None = None,
        min_waiting_days: int | None = None,
    ) -> list[dict[str, Any]]:
        """Lista subtasks L/XL pendientes con dias_esperando calculado."""
        now = datetime.utcnow()
        subtasks = self._repo.list_pending_cp_approval(
            area=area,
            player_id=player_id,
            project_code=project_code,
            min_waiting_days=min_waiting_days,
        )
        results = []
        for st in subtasks:
            proposed_at = st.cp_proposed_at or st.last_synced_at
            waiting_days = (now - proposed_at).days if proposed_at else 0
            results.append(
                {
                    "jira_key": st.jira_key,
                    "summary": st.summary,
                    "area": st.area,
                    "project_code": st.project_code,
                    "assignee_player_id": st.assignee_player_id,
                    "complexity_size": st.complexity_size,
                    "cp": st.cp,
                    "cp_proposed_at": st.cp_proposed_at,
                    "cp_proposed_by": st.cp_proposed_by,
                    "waiting_days": waiting_days,
                    "is_overdue": waiting_days > _OVERDUE_DAYS,
                    "cp_rejection_reason": st.cp_rejection_reason,
                }
            )
        return results

    def list_xxl(self) -> list[dict[str, Any]]:
        """Lista subtasks XXL detectadas (deben dividirse)."""
        subtasks = self._repo.list_xxl_detected()
        return [
            {
                "jira_key": st.jira_key,
                "summary": st.summary,
                "area": st.area,
                "project_code": st.project_code,
                "assignee_player_id": st.assignee_player_id,
                "cp": st.cp,
            }
            for st in subtasks
        ]

    def get_detail(self, jira_key: str) -> Subtask:
        """Obtener subtask para aprobación; lanza NotFoundError si no existe."""
        st = self._repo.get_for_approval(jira_key)
        if st is None:
            raise NotFoundError(f"Subtask {jira_key} no encontrada")
        return st

    # ── Acciones ──────────────────────────────────────────────────────────

    def approve(self, jira_key: str, admin_id: int) -> Subtask:
        """Sella CP de la subtask. Lanza CPImmutableError si ya fue aprobada."""
        st = self._get_pending(jira_key)
        now = datetime.utcnow()
        st.cp_approved_by = admin_id
        st.cp_approved_at = now
        st.cp_approval_required = False
        self._session.flush()
        self._audit(
            event_type="cp_approved",
            entity_id=jira_key,
            actor_id=admin_id,
            changes={"complexity_size": st.complexity_size, "cp": st.cp},
        )
        return st

    def adjust_and_approve(
        self, jira_key: str, new_size: str, reason: str, admin_id: int
    ) -> Subtask:
        """Ajusta la talla, recalcula CP y aprueba. XXL está prohibido como destino."""
        size = new_size.strip().upper()
        if size not in _VALID_SIZES:
            raise RuleViolationError(
                f"Talla destino '{size}' no válida para adjust. "
                f"Valores permitidos: {', '.join(sorted(_VALID_SIZES))}",
                details={"received": size},
            )
        st = self._get_pending(jira_key)
        old_size = st.complexity_size
        old_cp = st.cp

        # assign_cp respeta inmutabilidad internamente
        assign_cp(st, size)
        now = datetime.utcnow()
        st.cp_approved_by = admin_id
        st.cp_approved_at = now
        st.cp_approval_required = False
        self._session.flush()
        self._audit(
            event_type="cp_adjusted_and_approved",
            entity_id=jira_key,
            actor_id=admin_id,
            changes={
                "before": {"complexity_size": old_size, "cp": old_cp},
                "after": {"complexity_size": st.complexity_size, "cp": st.cp},
                "reason": reason,
            },
        )
        return st

    def reject(self, jira_key: str, reason: str, admin_id: int) -> Subtask:
        """Marca la subtask como rechazada; permanece en la cola."""
        st = self._get_subtask(jira_key)
        if st.cp_approved_at is not None:
            raise CPImmutableError(jira_key)
        st.cp_rejection_reason = reason
        # Mantiene cp_approval_required=1 y cp_approved_at NULL → sigue en la cola
        self._session.flush()
        self._audit(
            event_type="cp_rejected",
            entity_id=jira_key,
            actor_id=admin_id,
            changes={"reason": reason},
        )
        return st

    def mark_xxl_notified(self, jira_key: str, admin_id: int) -> Subtask:
        """Registra en audit_log que se notificó sobre una subtask XXL."""
        st = self._get_subtask(jira_key)
        if st.complexity_size != "XXL":
            raise RuleViolationError(
                f"Subtask {jira_key} no es XXL (es '{st.complexity_size}')",
                details={"jira_key": jira_key},
            )
        self._audit(
            event_type="xxl_notified",
            entity_id=jira_key,
            actor_id=admin_id,
            changes={"complexity_size": "XXL", "cp": st.cp},
        )
        return st

    # ── Helpers ───────────────────────────────────────────────────────────

    def _get_subtask(self, jira_key: str) -> Subtask:
        st = self._repo.get_for_approval(jira_key)
        if st is None:
            raise NotFoundError(f"Subtask {jira_key} no encontrada")
        return st

    def _get_pending(self, jira_key: str) -> Subtask:
        """Subtask que existe y no está aprobada aún."""
        st = self._get_subtask(jira_key)
        if st.cp_approved_at is not None:
            raise CPImmutableError(jira_key)
        return st

    def _audit(
        self,
        event_type: str,
        entity_id: str,
        actor_id: int,
        changes: dict[str, Any],
    ) -> None:
        log = AuditLog(
            event_type=event_type,
            entity_type="subtask",
            entity_id=entity_id,
            actor_player_id=actor_id,
            changes=json.dumps(changes),
            timestamp=datetime.utcnow(),
        )
        self._session.add(log)
