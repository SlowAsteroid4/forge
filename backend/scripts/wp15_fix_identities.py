"""WP-15 — Fix de identidades y áreas (idempotente, auditado).

Decisiones del chat maestro (PASO 0 confirmado):
- Jesús (id 12): rol PO de gobierno PERO area=DESIGN (cuenta en producción).
- Único diseñador real en los datos: Jesús (Sasha/Fran no existen; Diego es BE).
- "Equipo de Producto" (id 14): cuenta-grupo de Jira, 84 Design Sub-tasks.
  Mecanismo durable = player.area PO->DESIGN (el sync NO pisa player.area; y
  subtasks.area se re-infiere desde player.area). NO se toca assignee (lo
  revertiría el sync).

Cada cambio queda en audit_logs con before/after. Ejecutar con:
    uv run python scripts/wp15_fix_identities.py
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select

from forge.db.models.audit_log import AuditLog
from forge.db.models.player import Player
from forge.db.models.subtask import Subtask
from forge.db.session import SessionLocal

JESUS_ID = 12
EDP_ID = 14  # "Equipo de Producto" (cuenta-grupo)


def _audit(session, event_type: str, entity_type: str, entity_id: str, changes: dict) -> None:
    session.add(
        AuditLog(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_player_id=None,  # cambio administrativo de sistema (WP-15)
            changes=json.dumps(changes, ensure_ascii=False),
            extra_metadata=json.dumps({"wp": "WP-15"}, ensure_ascii=False),
            timestamp=datetime.utcnow(),
        )
    )


def apply_wp15(session) -> dict[str, int]:
    """Aplica los cambios de identidad WP-15 sobre la sesión dada (idempotente).

    Devuelve un resumen {area_corrected, role_set, subtasks_remapped}.
    """
    summary = {"area_corrected": 0, "role_set": 0, "subtasks_remapped": 0}
    # --- PASO 1: 4 diseñadores -> DESIGN (solo Jesús existe en datos) ---
    jesus = session.get(Player, JESUS_ID)
    if jesus is None:
        raise SystemExit("ERROR: player Jesús (id 12) no encontrado")
    if jesus.area != "DESIGN":
        before = jesus.area
        jesus.area = "DESIGN"
        _audit(
            session, "player_area_corrected", "player", str(JESUS_ID),
            {"field": "area", "before": before, "after": "DESIGN"},
        )
        summary["area_corrected"] += 1

    # --- PASO 2: Jesús = PO (gobierno) SIN salir de DESIGN ---
    if jesus.role != "PO":
        before = jesus.role
        jesus.role = "PO"
        _audit(
            session, "player_role_set", "player", str(JESUS_ID),
            {"field": "role", "before": before, "after": "PO",
             "note": "gobierno; area sigue DESIGN, cuenta en produccion"},
        )
        summary["role_set"] += 1

    # --- PASO 3: "Equipo de Producto" PO -> DESIGN (atribución durable) ---
    edp = session.get(Player, EDP_ID)
    if edp is None:
        raise SystemExit("ERROR: player 'Equipo de Producto' (id 14) no encontrado")
    if edp.area != "DESIGN":
        before = edp.area
        edp.area = "DESIGN"
        _audit(
            session, "player_area_corrected", "player", str(EDP_ID),
            {"field": "area", "before": before, "after": "DESIGN",
             "note": "cuenta-grupo de diseno; trabajo real de DESIGN (Jesus en 73/84)"},
        )
        summary["area_corrected"] += 1

    # Corregir filas subtasks.area ya almacenadas del grupo (84 Design Sub-tasks)
    stale = session.execute(
        select(Subtask).where(
            Subtask.assignee_player_id == EDP_ID, Subtask.area != "DESIGN"
        )
    ).scalars().all()
    for st in stale:
        before = st.area
        st.area = "DESIGN"
        _audit(
            session, "subtask_area_remapped_from_group", "subtask", st.jira_key,
            {"field": "area", "before": before, "after": "DESIGN",
             "assignee_player_id": EDP_ID},
        )
    summary["subtasks_remapped"] += len(stale)
    return summary


def main() -> None:
    session = SessionLocal()
    try:
        summary = apply_wp15(session)
        session.commit()
        print(f"WP-15 commit OK: {summary}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
