"""Schemas Pydantic para UC-04: flujo de aprobación de CP."""

from datetime import datetime

from pydantic import BaseModel, Field


class CpApprovalPendingItem(BaseModel):
    """Item en la cola de aprobación pendiente."""

    jira_key: str
    summary: str
    area: str
    project_code: str | None
    assignee_player_id: int | None
    complexity_size: str | None
    cp: int | None
    cp_proposed_at: datetime | None
    cp_proposed_by: int | None
    waiting_days: int
    is_overdue: bool
    cp_rejection_reason: str | None

    model_config = {"from_attributes": True}


class CpApprovalDetail(CpApprovalPendingItem):
    """Detalle completo de una subtask para aprobación."""

    status: str
    cycle_id: int | None
    cp_approved_at: datetime | None
    cp_approved_by: int | None
    cp_approval_required: bool
    cp_modified_post_approval: bool


class CpAdjustRequest(BaseModel):
    new_size: str = Field(..., description="XS | S | M | L | XL (XXL prohibido)")
    reason: str = Field(..., min_length=10, description="Justificación del ajuste")


class CpRejectRequest(BaseModel):
    reason: str = Field(..., min_length=10, description="Motivo del rechazo")


class XxlItem(BaseModel):
    """Subtask detectada con talla XXL."""

    jira_key: str
    summary: str
    area: str
    project_code: str | None
    assignee_player_id: int | None
    cp: int | None

    model_config = {"from_attributes": True}


class CpApprovalListResponse(BaseModel):
    total: int
    items: list[CpApprovalPendingItem]


class XxlListResponse(BaseModel):
    total: int
    items: list[XxlItem]
