"""Modelo de Redemption."""

from datetime import datetime

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class Redemption(Base):
    """Canjes de SP por items."""

    __tablename__ = "redemptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shop_item_code: Mapped[str] = mapped_column(
        String(10), ForeignKey("shop_items.code", ondelete="RESTRICT"), nullable=False
    )
    cost_sp: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("pending", "approved", "rejected", "fulfilled", name="redemption_status_enum"),
        nullable=False,
        default="pending",
        index=True,
    )
    requested_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    approved_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None]
    fulfilled_at: Mapped[datetime | None]
    notes: Mapped[str | None] = mapped_column(Text)
