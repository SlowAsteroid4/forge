"""PlayerRepository — acceso a datos de players."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from forge.db.models.player import Player
from forge.repositories.base import BaseRepository

LEADERBOARD_AREAS = {"BE", "FE", "DESIGN", "DB", "QA"}


class PlayerRepository(BaseRepository[Player, int]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Player)

    def get_by_jira_id(self, jira_account_id: str) -> Player | None:
        """Lookup por jira_account_id (usado por ETL sync)."""
        stmt = select(Player).where(Player.jira_account_id == jira_account_id)
        return self._session.scalars(stmt).first()

    def get_by_email(self, email: str) -> Player | None:
        stmt = select(Player).where(Player.email == email)
        return self._session.scalars(stmt).first()

    def list_active(self, area: str | None = None) -> list[Player]:
        """Players activos. Filtra por área si se especifica."""
        stmt = select(Player).where(Player.is_active.is_(True))
        if area is not None:
            stmt = stmt.where(Player.area == area)
        return list(self._session.scalars(stmt))

    def list_leads(self) -> list[Player]:
        """Solo players con is_lead=True."""
        stmt = select(Player).where(Player.is_lead.is_(True), Player.is_active.is_(True))
        return list(self._session.scalars(stmt))

    def list_for_leaderboard(self) -> list[Player]:
        """Players activos en áreas que participan en leaderboard (excluye PO/PM)."""
        stmt = select(Player).where(
            Player.is_active.is_(True),
            Player.area.in_(LEADERBOARD_AREAS),
        )
        return list(self._session.scalars(stmt))

    def upsert_by_jira_id(self, data: dict[str, Any]) -> Player:
        """Crea o actualiza un player por jira_account_id (para ETL)."""
        player = self.get_by_jira_id(data["jira_account_id"])
        if player is None:
            player = Player(**data)
            return self.create(player)
        for key, value in data.items():
            setattr(player, key, value)
        return self.update(player)
