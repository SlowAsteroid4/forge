"""PenaltyService — UC-06: penalizaciones manuales + apelaciones.

REGLA DE ORO APPEND-ONLY:
  El campo amount_sp de SpAdjustment NUNCA se hace UPDATE.
  Las reversiones (totales o parciales) se insertan como filas nuevas
  de tipo "reversal", que el motor suma en el bucket de bonus para
  neutralizar la penalización original.

  Los campos de metadatos de apelación (is_appealed, appeal_resolution,
  appeal_resolved_by, appeal_resolved_at, appeal_notes) SÍ se pueden
  actualizar: son estado de flujo, no el valor económico del ajuste.

VALIDACIÓN DE LÍMITE (AC-6.7):
  Una penalización no puede dejar sp_final negativo. El piso es 0.
  Debuffs -100% (D09, D14) llevan sp_final exactamente a 0.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError, RuleViolationError
from forge.db.models.audit_log import AuditLog
from forge.db.models.cycle import Cycle
from forge.db.models.debuff import Debuff
from forge.db.models.player import Player
from forge.db.models.sp_adjustment import SpAdjustment
from forge.db.models.subtask import Subtask
from forge.services.engine.engine_orchestrator import recalculate_subtask

logger = logging.getLogger(__name__)

_REASON_MIN_LEN = 30
_AUTO_DEBUFF_CODES = {"D01", "D03", "D04", "D10", "D11", "D13"}
_FULL_PENALTY_CODES = {"D09", "D14"}  # -100% → piso exacto 0
_DEFAULT_ADMIN_ID = 1  # Hardcoded hasta auth WP-08


# ── Aplicar penalización ──────────────────────────────────────────────────


def apply_penalty(
    session: Session,
    subtask_key: str,
    reason: str,
    admin_id: int = _DEFAULT_ADMIN_ID,
    catalog_code: str | None = None,
    custom_sp: float | None = None,
) -> SpAdjustment:
    """
    Aplicar penalización manual a una subtask.

    Args:
        subtask_key: Jira key de la subtask.
        reason: Justificación (mínimo 30 caracteres).
        admin_id: Player PM/TL que aplica (default 1 hasta auth).
        catalog_code: Código D01-D16; si se provee, el SP viene del catálogo.
        custom_sp: SP custom (positivo); exclusivo con catalog_code.

    Returns:
        SpAdjustment creado.

    Raises:
        RuleViolationError: Si la razón es corta, el ciclo está cerrado,
                           ambos/ninguno de catalog_code/custom_sp provistos,
                           o la subtask ya tiene sp_final=0.
        NotFoundError: Si subtask o debuff no existe.
    """
    if len(reason.strip()) < _REASON_MIN_LEN:
        raise RuleViolationError(
            f"La razón debe tener al menos {_REASON_MIN_LEN} caracteres."
        )

    if catalog_code is not None and custom_sp is not None:
        raise RuleViolationError("Provee catalog_code O custom_sp, no ambos.")

    if catalog_code is None and custom_sp is None:
        raise RuleViolationError("Debes proveer catalog_code o custom_sp.")

    subtask = session.get(Subtask, subtask_key)
    if subtask is None:
        raise NotFoundError(f"Subtask '{subtask_key}' no encontrada.")

    # Verificar que el ciclo asociado no esté cerrado
    if subtask.cycle_id:
        cycle = session.get(Cycle, subtask.cycle_id)
        if cycle and cycle.status in ("closed", "archived"):
            raise RuleViolationError(
                f"No se puede penalizar en un ciclo '{cycle.status}': {cycle.name}"
            )

    current_sp_final = subtask.sp_final or 0.0

    # Calcular el monto a penalizar
    if catalog_code is not None:
        debuff = session.get(Debuff, catalog_code)
        if debuff is None:
            raise NotFoundError(f"Debuff '{catalog_code}' no existe en el catálogo.")
        if not debuff.is_active:
            raise RuleViolationError(f"El debuff '{catalog_code}' está inactivo.")

        if debuff.penalty_type == "percentage":
            # -100% (D09, D14) → piso exacto 0
            penalty_amount = current_sp_final
        else:
            penalty_amount = debuff.value
    else:
        # custom_sp: el PM provee el monto directo
        assert custom_sp is not None  # narrowing: ya validado arriba
        if custom_sp <= 0:
            raise RuleViolationError("custom_sp debe ser positivo.")
        penalty_amount = custom_sp

    # VALIDACIÓN DE LÍMITE: el SP no puede quedar negativo
    if current_sp_final <= 0:
        raise RuleViolationError(
            f"La subtask '{subtask_key}' ya tiene sp_final=0; no se puede penalizar más."
        )
    # Cap: si la penalización supera el SP disponible, la reducimos al máximo posible
    if penalty_amount > current_sp_final:
        logger.warning(
            f"Penalty cap aplicado en {subtask_key}: "
            f"requested={penalty_amount:.2f}, capped={current_sp_final:.2f}"
        )
        penalty_amount = current_sp_final

    adj = SpAdjustment(
        subtask_key=subtask_key,
        adjustment_type="debuff_manual",
        catalog_code=catalog_code or "CUSTOM",
        amount_sp=round(penalty_amount, 2),
        reason=reason.strip(),
        applied_by=admin_id,
        applied_at=datetime.utcnow(),
        cycle_id=subtask.cycle_id,
        is_appealed=False,
    )
    session.add(adj)
    session.flush()

    # Recalcular SP en cascada
    recalculate_subtask(session, subtask_key, admin_id, force=True)

    _log_audit(
        session,
        action="manual_penalty_applied",
        entity_type="sp_adjustment",
        entity_id=adj.id,
        user_id=admin_id,
        details={
            "subtask_key": subtask_key,
            "catalog_code": adj.catalog_code,
            "amount_sp": adj.amount_sp,
            "sp_final_before": round(current_sp_final, 2),
        },
    )

    return adj


# ── Revertir penalización (total o parcial) ───────────────────────────────


def reverse_penalty(
    session: Session,
    adjustment_id: int,
    reason: str,
    admin_id: int = _DEFAULT_ADMIN_ID,
    partial_new_value: float | None = None,
) -> SpAdjustment:
    """
    Revertir una penalización (total o parcialmente) — append-only.

    Un INSERT de tipo "reversal" neutraliza la penalización.
    El campo amount_sp de la fila original NUNCA se modifica.
    Solo los campos de metadatos de apelación se actualizan en la original.

    Args:
        adjustment_id: ID del SpAdjustment original de tipo debuff_manual.
        reason: Justificación del reversal (mínimo 30 caracteres).
        admin_id: PM/TL que aprueba el reversal.
        partial_new_value: Si se provee, deja el neto en ese valor.
                           Ej: original=-10, partial_new_value=3 → reversal=7.
                           Si None: reversal total (reversal_amount = original.amount_sp).

    Returns:
        SpAdjustment de tipo "reversal" creado.

    Raises:
        NotFoundError: Si el adjustment no existe.
        RuleViolationError: Si el ajuste no es debuff_manual, ya fue revertido,
                           partial_new_value inválido, o razón corta.
    """
    if len(reason.strip()) < _REASON_MIN_LEN:
        raise RuleViolationError(
            f"La razón debe tener al menos {_REASON_MIN_LEN} caracteres."
        )

    original = session.get(SpAdjustment, adjustment_id)
    if original is None:
        raise NotFoundError(f"SpAdjustment id={adjustment_id} no encontrado.")

    if original.adjustment_type != "debuff_manual":
        raise RuleViolationError(
            f"Solo se pueden revertir ajustes de tipo 'debuff_manual'; "
            f"este es '{original.adjustment_type}'."
        )

    # Comprobar que no exista ya un reversal total para este adjustment
    existing_reversal = session.scalars(
        select(SpAdjustment).where(
            SpAdjustment.subtask_key == original.subtask_key,
            SpAdjustment.adjustment_type == "reversal",
            SpAdjustment.catalog_code == f"REV:{adjustment_id}",
        )
    ).first()
    if existing_reversal is not None:
        raise RuleViolationError(
            f"El ajuste id={adjustment_id} ya tiene un reversal registrado "
            f"(reversal id={existing_reversal.id})."
        )

    if partial_new_value is not None:
        if partial_new_value < 0:
            raise RuleViolationError("partial_new_value debe ser >= 0.")
        if partial_new_value >= original.amount_sp:
            raise RuleViolationError(
                f"partial_new_value={partial_new_value} debe ser menor que "
                f"la penalización original ({original.amount_sp})."
            )
        reversal_amount = round(original.amount_sp - partial_new_value, 2)
        resolution = "reduced"
    else:
        reversal_amount = original.amount_sp
        resolution = "reversed"

    reversal = SpAdjustment(
        subtask_key=original.subtask_key,
        adjustment_type="reversal",
        # catalog_code codifica el ID original para trazabilidad
        catalog_code=f"REV:{adjustment_id}",
        amount_sp=reversal_amount,
        reason=reason.strip(),
        applied_by=admin_id,
        applied_at=datetime.utcnow(),
        cycle_id=original.cycle_id,
        is_appealed=False,
    )
    session.add(reversal)

    # Actualizar metadatos de apelación en la fila original (UPDATE permitido)
    original.is_appealed = True
    original.appeal_resolution = resolution
    original.appeal_resolved_by = admin_id
    original.appeal_resolved_at = datetime.utcnow()
    original.appeal_notes = reason.strip()

    session.flush()

    # Recalcular SP en cascada
    if original.subtask_key:
        recalculate_subtask(session, original.subtask_key, admin_id, force=True)

    _log_audit(
        session,
        action="penalty_reversed",
        entity_type="sp_adjustment",
        entity_id=reversal.id,
        user_id=admin_id,
        details={
            "original_id": adjustment_id,
            "reversal_amount": reversal_amount,
            "resolution": resolution,
            "partial_new_value": partial_new_value,
        },
    )

    return reversal


# ── Marcar apelado ────────────────────────────────────────────────────────


def mark_appealed(session: Session, adjustment_id: int) -> None:
    """
    Registrar que el player apeló la penalización en la weekly.

    Pone is_appealed=True con appeal_resolution=None (entra a la cola
    de pendientes). El SP NO se modifica — solo metadatos.
    """
    adj = session.get(SpAdjustment, adjustment_id)
    if adj is None:
        raise NotFoundError(f"SpAdjustment id={adjustment_id} no encontrado.")

    if adj.adjustment_type != "debuff_manual":
        raise RuleViolationError("Solo se pueden apelar ajustes de tipo 'debuff_manual'.")

    if adj.is_appealed and adj.appeal_resolution is not None:
        raise RuleViolationError(
            f"Esta penalización ya fue resuelta: appeal_resolution='{adj.appeal_resolution}'."
        )

    adj.is_appealed = True
    adj.appeal_resolution = None  # pendiente de resolución
    session.flush()

    logger.info(f"SpAdjustment id={adjustment_id} marcado como apelado.")


# ── Resolver apelación ────────────────────────────────────────────────────


def resolve_appeal(
    session: Session,
    adjustment_id: int,
    resolution: str,
    notes: str,
    admin_id: int = _DEFAULT_ADMIN_ID,
    reduced_value: float | None = None,
) -> SpAdjustment | None:
    """
    Resolver una apelación pendiente.

    Args:
        adjustment_id: ID del SpAdjustment apelado.
        resolution: "upheld" | "reversed" | "reduced".
        notes: Notas de resolución (mínimo 30 caracteres).
        admin_id: PM/TL que resuelve.
        reduced_value: Solo para "reduced" — el nuevo valor neto de penalización.

    Returns:
        SpAdjustment de reversal si resolution in (reversed, reduced), else None.
    """
    if resolution not in ("upheld", "reversed", "reduced"):
        raise RuleViolationError(
            f"resolution inválido: '{resolution}'. Opciones: upheld | reversed | reduced."
        )

    if len(notes.strip()) < _REASON_MIN_LEN:
        raise RuleViolationError(
            f"Las notas deben tener al menos {_REASON_MIN_LEN} caracteres."
        )

    adj = session.get(SpAdjustment, adjustment_id)
    if adj is None:
        raise NotFoundError(f"SpAdjustment id={adjustment_id} no encontrado.")

    if not adj.is_appealed:
        raise RuleViolationError(
            f"El ajuste id={adjustment_id} no está marcado como apelado."
        )

    if adj.appeal_resolution is not None:
        raise RuleViolationError(
            f"Esta apelación ya fue resuelta: '{adj.appeal_resolution}'."
        )

    reversal: SpAdjustment | None = None

    if resolution == "upheld":
        # Solo actualizar metadatos — el SP no cambia
        adj.appeal_resolution = "upheld"
        adj.appeal_resolved_by = admin_id
        adj.appeal_resolved_at = datetime.utcnow()
        adj.appeal_notes = notes.strip()
        session.flush()

    elif resolution == "reversed":
        # Reversal total: delegar a reverse_penalty
        reversal = reverse_penalty(
            session, adjustment_id, notes, admin_id=admin_id, partial_new_value=None
        )

    elif resolution == "reduced":
        if reduced_value is None:
            raise RuleViolationError(
                "Para resolution='reduced' debes proveer reduced_value."
            )
        reversal = reverse_penalty(
            session, adjustment_id, notes, admin_id=admin_id, partial_new_value=reduced_value
        )

    _log_audit(
        session,
        action="appeal_resolved",
        entity_type="sp_adjustment",
        entity_id=adjustment_id,
        user_id=admin_id,
        details={"resolution": resolution, "reduced_value": reduced_value},
    )

    return reversal


# ── Listados ──────────────────────────────────────────────────────────────


def list_penalties(
    session: Session,
    cycle_id: int | None = None,
    player_id: int | None = None,
    adjustment_type: str | None = None,
    applied_by: int | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """Listar penalizaciones (debuff_manual) con filtros opcionales."""
    stmt = select(SpAdjustment).where(
        SpAdjustment.adjustment_type.in_(["debuff_manual", "penalty"])
    )

    if cycle_id is not None:
        stmt = stmt.where(SpAdjustment.cycle_id == cycle_id)
    if player_id is not None:
        # Buscar por assignee de la subtask
        stmt = stmt.join(
            Subtask, SpAdjustment.subtask_key == Subtask.jira_key
        ).where(Subtask.assignee_player_id == player_id)
    if adjustment_type is not None:
        stmt = stmt.where(SpAdjustment.adjustment_type == adjustment_type)
    if applied_by is not None:
        stmt = stmt.where(SpAdjustment.applied_by == applied_by)

    stmt = stmt.order_by(SpAdjustment.applied_at.desc())

    total = len(session.scalars(stmt).all())

    offset = (page - 1) * page_size
    items_raw = session.scalars(stmt.offset(offset).limit(page_size)).all()
    items = [_serialize_adjustment(session, adj) for adj in items_raw]

    return {"total": total, "page": page, "page_size": page_size, "items": items}


def list_pending_appeals(session: Session) -> dict[str, Any]:
    """Listar penalizaciones apeladas sin resolver (is_appealed=True, appeal_resolution=None)."""
    stmt = (
        select(SpAdjustment)
        .where(
            SpAdjustment.adjustment_type == "debuff_manual",
            SpAdjustment.is_appealed.is_(True),
            SpAdjustment.appeal_resolution.is_(None),
        )
        .order_by(SpAdjustment.applied_at.asc())
    )
    items_raw = session.scalars(stmt).all()
    items = [_serialize_adjustment(session, adj) for adj in items_raw]
    return {"total": len(items), "items": items}


def list_debuff_catalog(session: Session) -> list[dict[str, Any]]:
    """Catálogo de debuffs activos disponibles para aplicar manualmente."""
    debuffs = session.scalars(
        select(Debuff).where(Debuff.is_active.is_(True)).order_by(Debuff.code)
    ).all()
    return [
        {
            "code": d.code,
            "narrative_name": d.narrative_name,
            "trigger_description": d.trigger_description,
            "penalty_type": d.penalty_type,
            "value": d.value,
            "is_appealable": d.is_appealable,
            "icon_code": d.icon_code,
            "is_auto": d.code in _AUTO_DEBUFF_CODES,
        }
        for d in debuffs
    ]


# ── Helpers privados ──────────────────────────────────────────────────────


def _serialize_adjustment(session: Session, adj: SpAdjustment) -> dict[str, Any]:
    """Serializar SpAdjustment a dict con información enriquecida."""
    subtask = session.get(Subtask, adj.subtask_key) if adj.subtask_key else None
    applied_by_player = session.get(Player, adj.applied_by) if adj.applied_by else None
    assignee = (
        session.get(Player, subtask.assignee_player_id)
        if subtask and subtask.assignee_player_id
        else None
    )
    resolved_by = (
        session.get(Player, adj.appeal_resolved_by) if adj.appeal_resolved_by else None
    )

    return {
        "id": adj.id,
        "subtask_key": adj.subtask_key,
        "subtask_summary": subtask.summary if subtask else None,
        "cycle_id": adj.cycle_id,
        "player_id": assignee.id if assignee else None,
        "player_name": assignee.display_name if assignee else None,
        "adjustment_type": adj.adjustment_type,
        "catalog_code": adj.catalog_code,
        "amount_sp": adj.amount_sp,
        "reason": adj.reason,
        "applied_by": adj.applied_by,
        "applied_by_name": applied_by_player.display_name if applied_by_player else None,
        "applied_at": adj.applied_at.isoformat() if adj.applied_at else None,
        "is_appealed": adj.is_appealed,
        "appeal_resolution": adj.appeal_resolution,
        "appeal_resolved_by": adj.appeal_resolved_by,
        "appeal_resolved_by_name": resolved_by.display_name if resolved_by else None,
        "appeal_resolved_at": (
            adj.appeal_resolved_at.isoformat() if adj.appeal_resolved_at else None
        ),
        "appeal_notes": adj.appeal_notes,
        "sp_final_current": subtask.sp_final if subtask else None,
    }


def _log_audit(
    session: Session,
    action: str,
    entity_type: str,
    entity_id: int,
    user_id: int,
    details: dict[str, Any],
) -> None:
    import json

    log = AuditLog(
        event_type=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        actor_player_id=user_id,
        changes=json.dumps(details),
        extra_metadata=None,
        timestamp=datetime.utcnow(),
    )
    session.add(log)
    session.flush()
