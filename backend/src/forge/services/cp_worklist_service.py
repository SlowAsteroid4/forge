"""
CpWorklistService — WP-24: subtasks sin CP agrupadas por apartado (read-only).

Reemplaza el flujo de aprobación manual de UC-04 (retirado por ADR-016: el CP
se auto-lockea en el sync). La pantalla asociada muestra el trabajo pendiente
de tallar (cp IS NULL) agrupado por apartado, más las XXL detectadas (talla
rechazada, requieren ruptura — no se auto-lockean).

Reutiliza la derivación de apartado de WP-21/ADR-012 (prefijo [XXX] del summary
de la épica, vía story → epic) con 'Sin apartado' como categoría de primera clase.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from forge.core.config import get_settings
from forge.db.models.player import Player
from forge.db.models.subtask import Subtask
from forge.repositories.subtask import SubtaskRepository
from forge.services.analytics_service import (
    KNOWN_APARTADOS,
    SIN_APARTADO,
    AnalyticsService,
)


class CpWorklistService:
    """Listados read-only del worklist de CP. Cero escrituras."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = SubtaskRepository(session)
        self._analytics = AnalyticsService(session)

    def get_worklist(self) -> dict[str, Any]:
        """Subtasks sin CP agrupadas por apartado + sección XXL."""
        now = datetime.utcnow()

        # 'Sin CP' canónico = cp IS NULL (en datos reales cp y complexity_size
        # son NULL juntos; el sync siempre calcula cp cuando hay talla).
        rows = self._session.execute(
            select(Subtask, Player.display_name)
            .join(Player, Subtask.assignee_player_id == Player.id, isouter=True)
            .where(Subtask.cp.is_(None), Subtask.pruned_at.is_(None))
        ).all()

        smap = self._analytics._story_apartado_map()
        grouped: dict[str, list[dict[str, Any]]] = {}
        for st, assignee_name in rows:
            apartado = (
                smap.get(st.parent_story_key, SIN_APARTADO) if st.parent_story_key else SIN_APARTADO
            )
            grouped.setdefault(apartado, []).append(
                {
                    "jira_key": st.jira_key,
                    "summary": st.summary,
                    "area": st.area,
                    "status": st.status,
                    "assignee_player_id": st.assignee_player_id,
                    "assignee_name": assignee_name,
                    "age_days": (now - st.created_at).days if st.created_at else 0,
                }
            )

        # Orden ADR-012: conocidos primero (en su orden), otros alfabético,
        # 'Sin apartado' al final.
        known = [a for a in KNOWN_APARTADOS if a in grouped]
        others = sorted(set(grouped) - set(KNOWN_APARTADOS) - {SIN_APARTADO})
        ordered = known + others + ([SIN_APARTADO] if SIN_APARTADO in grouped else [])

        groups = [
            {
                "apartado": a,
                "known": a in KNOWN_APARTADOS or a == SIN_APARTADO,
                "count": len(grouped[a]),
                "items": sorted(grouped[a], key=lambda i: -i["age_days"]),
            }
            for a in ordered
        ]

        xxl_items = self._list_xxl()
        return {
            "total": sum(g["count"] for g in groups),
            "groups": groups,
            "xxl_total": len(xxl_items),
            "xxl_items": xxl_items,
            "jira_base_url": (get_settings().jira_instance_url or "").rstrip("/") or None,
        }

    def _list_xxl(self) -> list[dict[str, Any]]:
        """XXL detectadas (talla rechazada — el auto-lock nunca las toca)."""
        results = []
        for st in self._repo.list_xxl_detected():
            assignee = (
                self._session.get(Player, st.assignee_player_id) if st.assignee_player_id else None
            )
            results.append(
                {
                    "jira_key": st.jira_key,
                    "summary": st.summary,
                    "area": st.area,
                    "status": st.status,
                    "assignee_player_id": st.assignee_player_id,
                    "assignee_name": assignee.display_name if assignee else None,
                    "cp": st.cp,
                }
            )
        return results
