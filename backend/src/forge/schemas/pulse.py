"""Schemas Pydantic para UC-16 Pulso Operativo (rediseño WP-16)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ── CAMBIO 1: Franja de contadores por estado (orden de flujo) ─────────────────


class FlowCounter(BaseModel):
    """Un contador de la franja de flujo (Backlog → Done)."""

    key: str = Field(description="Clave estable del paso de flujo, ej. 'in_progress'")
    label: str = Field(description="Etiqueta visible, ej. 'In Progress'")
    count: int = Field(description="Subtasks en este paso AHORA")
    raw_statuses: list[str] = Field(
        description="Statuses reales de Jira plegados en este contador (auditable)"
    )
    zone: str = Field(description="Zona de color JPDS: neutral/dev/review/qa/done")


# ── CAMBIO 2: Cards por área (reemplaza WIP/semáforo) ──────────────────────────


class AreaTask(BaseModel):
    """Fila de tarea dentro de un grupo-por-estado de una card de área."""

    jira_key: str
    summary: str
    status: str
    zone: str = Field(description="Zona de color JPDS del estado")
    assignee_name: str | None
    assignee_player_id: int | None
    is_aggregate_team: bool = Field(
        default=False,
        description="True si el dueño es una cuenta-grupo agregada (ej. 'Equipo de Producto')",
    )


class AreaStatusGroup(BaseModel):
    """Agrupación de tareas de un área por estado."""

    status: str
    zone: str
    count: int
    tasks: list[AreaTask]


class AreaCard(BaseModel):
    """Card de un área: tareas activas asignadas → expand por estado → código+dueño.

    Sin 'WIP', sin semáforo de límite. Cuenta estados activos (Ready→In QA, Blocked);
    excluye Backlog y Done.
    """

    area: str
    total_active: int = Field(description="Total de tareas activas en el área (excl. Backlog/Done)")
    by_status: list[AreaStatusGroup] = Field(description="Grupos por estado en orden de flujo")


# ── CAMBIO 3: Drill-down de dev ────────────────────────────────────────────────


class DevTask(BaseModel):
    jira_key: str
    summary: str
    status: str
    zone: str
    area: str
    dias_en_estado: float = Field(description="Días hábiles en el estado actual")


class DevDrilldown(BaseModel):
    player_id: int
    display_name: str
    is_aggregate_team: bool = Field(
        default=False, description="True si es cuenta-grupo agregada"
    )
    area: str | None
    total: int
    tasks: list[DevTask] = Field(description="Tareas en progreso del dev, con estatus")


# ── Secciones conservadas (sin cambios funcionales) ────────────────────────────


class BlockItem(BaseModel):
    jira_key: str
    summary: str
    area: str
    assignee_name: str | None
    assignee_player_id: int | None
    horas_bloqueado: float
    es_critico: bool = Field(description="True si horas_bloqueado >= 8h habiles")
    block_reason: str | None = Field(
        default=None,
        description="Razon del bloqueo. HUECO: Jira no expone este campo en changelog.",
    )


class DayMovementItem(BaseModel):
    jira_key: str
    summary: str
    area: str
    assignee_name: str | None
    from_status: str
    to_status: str
    moved_at: datetime


class AgingItem(BaseModel):
    jira_key: str
    summary: str
    area: str
    status: str
    assignee_name: str | None
    assignee_player_id: int | None
    dias_en_estado: float = Field(description="Dias habiles en el estado actual")
    edad_total_dias: float = Field(description="Dias habiles desde created_at")


class ReadyQueueItem(BaseModel):
    jira_key: str
    summary: str
    area: str
    cp: int | None
    assignee_name: str | None
    tiempo_en_ready_horas: float
    priority: str | None = Field(default=None, description="Prioridad Jira (Highest/High/Medium/Low/Lowest)")


class FlagForReviewRequest(BaseModel):
    note: str | None = Field(default=None, description="Nota opcional del PM/TL")


class FlagForReviewResponse(BaseModel):
    jira_key: str
    audit_log_id: int
    message: str


class PulseSnapshot(BaseModel):
    generated_at: datetime
    filters_applied: dict[str, Any]
    flow_counters: list[FlowCounter] = Field(description="CAMBIO 1: franja por estado")
    area_cards: list[AreaCard] = Field(description="CAMBIO 2: cards por área")
    blocks: list[BlockItem]
    day_movements: list[DayMovementItem]
    aging_critical: list[AgingItem]
    ready_queue: list[ReadyQueueItem]
