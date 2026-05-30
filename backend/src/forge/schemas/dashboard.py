"""Schemas de respuesta para el dashboard de Forge Ops."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Cycle blocks
# ──────────────────────────────────────────────


class CycleSummary(BaseModel):
    """Ciclo reducido para el selector de ciclos."""

    id: int
    name: str
    start_date: date
    end_date: date
    status: str


class CycleHeader(BaseModel):
    """Header del ciclo con progreso temporal."""

    id: int
    name: str
    start_date: date
    end_date: date
    days_elapsed: int
    days_total: int
    progress_pct: float = Field(ge=0, le=100, description="% de días transcurridos")


class KPIValue(BaseModel):
    """Valor de un KPI con comparativa vs ciclo anterior."""

    value: float
    previous_value: float | None = None
    delta_pct: float | None = Field(
        default=None,
        description="Variación porcentual vs ciclo anterior (+positivo = mejora)",
    )


class KPICards(BaseModel):
    """4 KPI cards principales del dashboard."""

    cp_done: KPIValue
    cp_pending: float = Field(description="CP de subtasks aún no terminadas")
    sp_total: float = Field(description="SP acumulado en subtasks Done del ciclo")
    bugs_derived: int = Field(description="Cantidad de Bug Sub-tasks en el ciclo")


class AreaProgress(BaseModel):
    """Progreso de un área técnica en el ciclo."""

    area: str
    cp_done: float
    cp_total: float
    progress_pct: float = Field(ge=0, le=100)
    active_devs: int = Field(description="Devs con al menos 1 subtask activa")
    has_wip_bottleneck: bool = Field(description="Algún dev del área excede el WIP máximo")


PlayerStatusEnum = Literal["productive", "wip_high", "blocked", "inactive"]


class PlayerStatus(BaseModel):
    """Estado de un developer en el ciclo actual."""

    player_id: int
    display_name: str
    area: str
    avatar_code: str | None = None
    active_subtasks: int = Field(description="Subtasks no terminadas (no Done/Cancelled)")
    done_subtasks: int = Field(description="Subtasks Done en el ciclo")
    sp_sprint: float = Field(description="SP acumulado en el ciclo")
    status: PlayerStatusEnum


AlertTypeEnum = Literal[
    "abandoned_subtask",
    "waiting_long",
    "wip_exceeded",
    "cp_pending_approval",
    "bug_unattributed",
]


class AlertItem(BaseModel):
    """Alerta accionable del dashboard."""

    alert_type: AlertTypeEnum
    severity: Literal["warning", "critical"]
    message: str
    subtask_key: str | None = None
    player_id: int | None = None


class ProjectSummary(BaseModel):
    """Proyecto resumido para el filtro global."""

    code: str
    internal_name: str
    jira_prefix: str


# ──────────────────────────────────────────────
# Respuesta principal
# ──────────────────────────────────────────────


class DashboardResponse(BaseModel):
    """Respuesta completa del dashboard Forge Ops.

    Cuando no hay ciclo activo, `cycle` es None y `no_cycle_message`
    indica el motivo. El frontend renderiza el empty state.
    """

    cycle: CycleHeader | None = None
    no_cycle_message: str | None = None

    kpis: KPICards | None = None
    area_progress: list[AreaProgress] = []
    player_status: list[PlayerStatus] = []
    alerts: list[AlertItem] = []

    available_projects: list[ProjectSummary] = []
    available_cycles: list[CycleSummary] = []
    last_synced_at: datetime | None = Field(
        default=None,
        description="Timestamp del último sync contra Jira",
    )
