"""Modelos de SQLAlchemy para Forge.

Importar todos los modelos aquí para que Alembic autogenerate los vea.
"""

from forge.db.models.achievement import Achievement
from forge.db.models.achievement_unlock import AchievementUnlock
from forge.db.models.audit_log import AuditLog
from forge.db.models.avatar import Avatar
from forge.db.models.buff import Buff
from forge.db.models.class_ import Class
from forge.db.models.debuff import Debuff
from forge.db.models.engine_version import EngineVersion
from forge.db.models.epic import Epic
from forge.db.models.leaderboard_snapshot import LeaderboardSnapshot
from forge.db.models.player import Player
from forge.db.models.project import Project
from forge.db.models.redemption import Redemption
from forge.db.models.shop_item import ShopItem
from forge.db.models.sp_adjustment import SpAdjustment
from forge.db.models.sprint import Sprint
from forge.db.models.story import Story
from forge.db.models.subtask import Subtask

__all__ = [
    "Achievement",
    "AchievementUnlock",
    "AuditLog",
    "Avatar",
    "Buff",
    "Class",
    "Debuff",
    "EngineVersion",
    "Epic",
    "LeaderboardSnapshot",
    "Player",
    "Project",
    "Redemption",
    "ShopItem",
    "SpAdjustment",
    "Sprint",
    "Story",
    "Subtask",
]
