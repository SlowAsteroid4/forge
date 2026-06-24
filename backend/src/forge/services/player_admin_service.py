"""Servicio de administración de players (WP-13)."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError, RuleViolationError
from forge.db.models.audit_log import AuditLog
from forge.db.models.player import Player

# Campos que el PM puede editar. El sync NUNCA escribe sobre players,
# pero por claridad y seguridad usamos una whitelist explícita.
_EDITABLE_FIELDS = frozenset(
    {"area", "employment_type", "is_active", "is_lead", "monthly_salary", "hourly_rate", "monthly_hours_cap"}
)

# Campos de costo que SÍ admiten None (borrar el valor). Necesario para
# cambiar de dinámica: al pasar de mensualidad fija a costo por hora se debe
# poder limpiar el salario (y viceversa). El resto de campos nunca se nulifican.
_NULLABLE_FIELDS = frozenset({"monthly_salary", "hourly_rate", "monthly_hours_cap"})

# Campos que vienen de Jira/seed y NO se deben editar desde la UI admin.
_READONLY_FIELDS = frozenset({"jira_account_id", "display_name", "email"})


def list_players(
    session: Session,
    area: str | None = None,
    employment_type: str | None = None,
    is_active: bool | None = None,
) -> list[Player]:
    """Listar players con filtros opcionales."""
    stmt = select(Player).order_by(Player.area, Player.display_name)
    if area is not None:
        stmt = stmt.where(Player.area == area)
    if employment_type is not None:
        stmt = stmt.where(Player.employment_type == employment_type)
    if is_active is not None:
        stmt = stmt.where(Player.is_active == is_active)
    return list(session.execute(stmt).scalars().all())


def get_player(session: Session, player_id: int) -> Player:
    """Obtener player por ID."""
    player = session.get(Player, player_id)
    if player is None:
        raise NotFoundError(f"Player {player_id} no encontrado")
    return player


def update_player(
    session: Session,
    player_id: int,
    patch: dict[str, object],
    admin_id: int,
) -> Player:
    """
    Actualizar campos editables de un player.

    Rechaza cualquier intento de modificar campos read-only (jira_account_id,
    display_name, email). Registra cambio en audit_log.
    """
    player = get_player(session, player_id)

    # Detectar intentos de modificar campos read-only
    readonly_attempted = _READONLY_FIELDS & set(patch.keys())
    if readonly_attempted:
        raise RuleViolationError(
            f"Campos sincronizados desde Jira no son editables: {sorted(readonly_attempted)}"
        )

    # Filtrar solo campos permitidos con valor no-None
    changes_before: dict[str, object] = {}
    changes_after: dict[str, object] = {}

    for field, value in patch.items():
        if field not in _EDITABLE_FIELDS:
            continue
        # None solo es válido para limpiar los campos de costo; para el resto
        # (area, employment_type, flags) lo ignoramos para no nulificar por error.
        if value is None and field not in _NULLABLE_FIELDS:
            continue
        old = getattr(player, field)
        if old != value:
            changes_before[field] = old
            changes_after[field] = value
            setattr(player, field, value)

    if not changes_before:
        return player  # sin cambios reales

    # Audit log — los campos de costo se registran solo como "changed" (no el valor)
    # para evitar exponer datos sensibles en texto plano en el log.
    safe_before = _mask_sensitive(changes_before)
    safe_after = _mask_sensitive(changes_after)

    session.add(
        AuditLog(
            event_type="player_updated",
            entity_type="player",
            entity_id=str(player_id),
            actor_player_id=admin_id,
            changes=json.dumps({"before": safe_before, "after": safe_after}),
            timestamp=datetime.utcnow(),
        )
    )

    return player


def _mask_sensitive(d: dict[str, object]) -> dict[str, object]:
    """Reemplaza valores de costos con "<changed>" para el audit log."""
    sensitive = {"monthly_salary", "hourly_rate", "monthly_hours_cap"}
    return {k: ("<changed>" if k in sensitive else v) for k, v in d.items()}
