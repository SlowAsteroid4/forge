"""
Auto-lock de CP (WP-24 / ADR-016) — reemplaza la aprobación manual de UC-04.

Toda subtask con CP válido (talla y cp poblados) y no-XXL queda lockeada
automáticamente: cp_approved_at = now(), cp_approved_by = NULL (sentinela de
sistema: distingue el lock automático de las aprobaciones manuales históricas,
que llevan el id del PM). A partir del lock aplica la misma inmutabilidad de
siempre: un cambio de cp en Jira se ignora (guard del sync + CPImmutableError).

Reglas:
  - XXL nunca se lockea: es talla rechazada (is_rejected_size), debe partirse.
  - Sin talla/cp (NULL) no hay nada que lockear.
  - Idempotente: una subtask ya lockeada (cp_approved_at NOT NULL) no se toca,
    incluidas las filas históricas aprobadas manualmente.
  - Subtasks podadas (pruned_at NOT NULL) se excluyen: están fuera del flujo.
  - Cada lock se registra en audit_log con event_type='cp_auto_locked' y
    actor_player_id=NULL (acción de sistema, igual que los eventos del sync).

Se invoca al final de SyncOrchestrator.sync_all(), después de que los upserts
materializaron el valor legítimo de Jira — el CP aterriza primero y luego se
lockea, nunca antes.
"""

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from forge.core.logging import get_logger
from forge.db.models.audit_log import AuditLog
from forge.db.models.subtask import Subtask
from forge.services.engine.cp_calculator import REJECTED_SIZES

logger = get_logger(__name__)


def auto_lock_cp(session: Session, *, now: datetime | None = None) -> int:
    """
    Lockea el CP de toda subtask con CP válido no-XXL aún sin lock.

    Args:
        session: Sesión activa de SQLAlchemy (el caller hace commit).
        now: Timestamp del lock (inyectable para tests). Default: utcnow().

    Returns:
        Número de subtasks lockeadas en esta corrida (0 si no había pendientes).
    """
    ts = now or datetime.utcnow()
    stmt = select(Subtask).where(
        Subtask.cp.is_not(None),
        Subtask.complexity_size.is_not(None),
        Subtask.complexity_size.not_in(list(REJECTED_SIZES)),
        Subtask.cp_approved_at.is_(None),
        Subtask.pruned_at.is_(None),
    )
    pending = list(session.scalars(stmt))

    for st in pending:
        st.cp_approved_at = ts
        st.cp_approved_by = None  # sentinela de sistema (ADR-016)
        st.cp_approval_required = False
        session.add(
            AuditLog(
                event_type="cp_auto_locked",
                entity_type="subtask",
                entity_id=st.jira_key,
                actor_player_id=None,
                changes=json.dumps({"complexity_size": st.complexity_size, "cp": st.cp}),
                timestamp=ts,
            )
        )

    if pending:
        logger.info(f"Auto-lock CP: {len(pending)} subtask(s) lockeadas")
    return len(pending)
