"""Modelo de AuditLog."""

from datetime import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class AuditLog(Base):
    """Log de auditoría de operaciones críticas."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    actor_player_id: Mapped[int | None]
    changes: Mapped[str | None] = mapped_column(Text, comment="JSON con antes/después")
    extra_metadata: Mapped[str | None] = mapped_column(Text, comment="JSON con contexto adicional")
    timestamp: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, index=True)
