"""Router UC-04: aprobación de CP para subtasks L/XL."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from forge.core.exceptions import CPImmutableError, NotFoundError, RuleViolationError
from forge.db.session import get_session
from forge.schemas.cp_approval import (
    CpAdjustRequest,
    CpApprovalDetail,
    CpApprovalListResponse,
    CpApprovalPendingItem,
    CpRejectRequest,
    XxlItem,
    XxlListResponse,
)
from forge.services.cp_approval_service import CpApprovalService

router = APIRouter(tags=["cp-approvals"])

# Hardcoded admin_id=1 until auth is built (UC-08)
_DEFAULT_ADMIN_ID = 1


def _service(session: Session = Depends(get_session)) -> CpApprovalService:
    return CpApprovalService(session)


@router.get("/pending", response_model=CpApprovalListResponse)
def list_pending(
    area: str | None = Query(None),
    player_id: int | None = Query(None),
    project_code: str | None = Query(None),
    min_waiting_days: int | None = Query(None, ge=0),
    svc: CpApprovalService = Depends(_service),
) -> CpApprovalListResponse:
    items = svc.list_pending(
        area=area,
        player_id=player_id,
        project_code=project_code,
        min_waiting_days=min_waiting_days,
    )
    return CpApprovalListResponse(
        total=len(items),
        items=[CpApprovalPendingItem(**i) for i in items],
    )


@router.get("/xxl-detected", response_model=XxlListResponse)
def list_xxl(svc: CpApprovalService = Depends(_service)) -> XxlListResponse:
    items = svc.list_xxl()
    return XxlListResponse(total=len(items), items=[XxlItem(**i) for i in items])


@router.get("/{jira_key}", response_model=CpApprovalDetail)
def get_detail(
    jira_key: str,
    svc: CpApprovalService = Depends(_service),
) -> CpApprovalDetail:
    try:
        st = svc.get_detail(jira_key)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    now = __import__("datetime").datetime.utcnow()
    proposed_at = st.cp_proposed_at or st.last_synced_at
    waiting_days = (now - proposed_at).days if proposed_at else 0
    return CpApprovalDetail(
        jira_key=st.jira_key,
        summary=st.summary,
        area=st.area,
        project_code=st.project_code,
        assignee_player_id=st.assignee_player_id,
        complexity_size=st.complexity_size,
        cp=st.cp,
        cp_proposed_at=st.cp_proposed_at,
        cp_proposed_by=st.cp_proposed_by,
        waiting_days=waiting_days,
        is_overdue=waiting_days > 3,
        cp_rejection_reason=st.cp_rejection_reason,
        status=st.status,
        cycle_id=st.cycle_id,
        cp_approved_at=st.cp_approved_at,
        cp_approved_by=st.cp_approved_by,
        cp_approval_required=st.cp_approval_required,
        cp_modified_post_approval=st.cp_modified_post_approval,
    )


@router.post("/{jira_key}/approve", response_model=CpApprovalDetail)
def approve(
    jira_key: str,
    svc: CpApprovalService = Depends(_service),
) -> CpApprovalDetail:
    try:
        st = svc.approve(jira_key, admin_id=_DEFAULT_ADMIN_ID)
        svc._session.commit()
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except CPImmutableError as e:
        raise HTTPException(status_code=409, detail=e.message)
    return _to_detail(st)


@router.post("/{jira_key}/adjust", response_model=CpApprovalDetail)
def adjust(
    jira_key: str,
    body: CpAdjustRequest,
    svc: CpApprovalService = Depends(_service),
) -> CpApprovalDetail:
    try:
        st = svc.adjust_and_approve(
            jira_key, new_size=body.new_size, reason=body.reason, admin_id=_DEFAULT_ADMIN_ID
        )
        svc._session.commit()
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except CPImmutableError as e:
        raise HTTPException(status_code=409, detail=e.message)
    except (RuleViolationError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _to_detail(st)


@router.post("/{jira_key}/reject", response_model=CpApprovalDetail)
def reject(
    jira_key: str,
    body: CpRejectRequest,
    svc: CpApprovalService = Depends(_service),
) -> CpApprovalDetail:
    try:
        st = svc.reject(jira_key, reason=body.reason, admin_id=_DEFAULT_ADMIN_ID)
        svc._session.commit()
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except CPImmutableError as e:
        raise HTTPException(status_code=409, detail=e.message)
    return _to_detail(st)


@router.post("/{jira_key}/mark-xxl-notified", response_model=CpApprovalDetail)
def mark_xxl_notified(
    jira_key: str,
    svc: CpApprovalService = Depends(_service),
) -> CpApprovalDetail:
    try:
        st = svc.mark_xxl_notified(jira_key, admin_id=_DEFAULT_ADMIN_ID)
        svc._session.commit()
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except RuleViolationError as e:
        raise HTTPException(status_code=422, detail=e.message)
    return _to_detail(st)


def _to_detail(st) -> CpApprovalDetail:  # type: ignore[no-untyped-def]
    now = __import__("datetime").datetime.utcnow()
    proposed_at = st.cp_proposed_at or st.last_synced_at
    waiting_days = (now - proposed_at).days if proposed_at else 0
    return CpApprovalDetail(
        jira_key=st.jira_key,
        summary=st.summary,
        area=st.area,
        project_code=st.project_code,
        assignee_player_id=st.assignee_player_id,
        complexity_size=st.complexity_size,
        cp=st.cp,
        cp_proposed_at=st.cp_proposed_at,
        cp_proposed_by=st.cp_proposed_by,
        waiting_days=waiting_days,
        is_overdue=waiting_days > 3,
        cp_rejection_reason=st.cp_rejection_reason,
        status=st.status,
        cycle_id=st.cycle_id,
        cp_approved_at=st.cp_approved_at,
        cp_approved_by=st.cp_approved_by,
        cp_approval_required=st.cp_approval_required,
        cp_modified_post_approval=st.cp_modified_post_approval,
    )
