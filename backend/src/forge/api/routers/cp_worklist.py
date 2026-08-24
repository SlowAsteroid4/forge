"""Router WP-24: worklist de CP — subtasks sin CP por apartado + XXL (read-only)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from forge.db.session import get_session
from forge.schemas.cp_worklist import CpWorklistResponse
from forge.services.cp_worklist_service import CpWorklistService

router = APIRouter(tags=["cp-worklist"])


@router.get("", response_model=CpWorklistResponse)
def get_worklist(session: Session = Depends(get_session)) -> CpWorklistResponse:
    data = CpWorklistService(session).get_worklist()
    return CpWorklistResponse(**data)
