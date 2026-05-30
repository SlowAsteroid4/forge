"""Modelo de ShopItem."""

from sqlalchemy import Boolean, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class ShopItem(Base):
    """Items canjeables en la tienda."""

    __tablename__ = "shop_items"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(
        Enum(
            "perk_time",
            "perk_communal",
            "perk_consumption",
            "perk_physical",
            "perk_large",
            name="shop_category_enum",
        ),
        nullable=False,
    )
    price_sp: Mapped[int] = mapped_column(Integer, nullable=False)
    operational_notes: Mapped[str | None] = mapped_column(Text)
    stock_limit: Mapped[int | None] = mapped_column(Integer)
    min_rank_required: Mapped[str | None] = mapped_column(String(20))
    icon_code: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
