"""Router UC-17: cierre mensual y MVP del Mes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError, RuleViolationError
from forge.db.session import get_session
from forge.schemas.monthly_mvp import (
    MonthCloseRequest,
    MonthCloseResponse,
    MonthCloseSummary,
    MonthlyCandidate,
    MonthlyMvpEditRequest,
    MonthlyMvpHistoryItem,
)
from forge.services.monthly_mvp_service import MonthlyMvpService

router = APIRouter(tags=["monthly-mvp"])

# Hardcoded admin_id=1 until auth is built (WP-08)
_DEFAULT_ADMIN_ID = 1


def _service(session: Session = Depends(get_session)) -> MonthlyMvpService:
    return MonthlyMvpService(session)


def _parse_month(month_str: str) -> tuple[int, int]:
    """Parse 'YYYY-MM' string into (year, month). Raises 422 on bad format."""
    try:
        parts = month_str.split("-")
        if len(parts) != 2:
            raise ValueError
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=422,
            detail=f"Formato de mes inválido: '{month_str}'. Usa YYYY-MM (ej: 2026-05).",
        )


@router.get("/months/{month}/candidates", response_model=list[MonthlyCandidate])
def get_candidates(
    month: str,
    svc: MonthlyMvpService = Depends(_service),
) -> list[MonthlyCandidate]:
    year, mon = _parse_month(month)
    try:
        candidates = svc.list_candidates(year, mon)
        return [MonthlyCandidate(**c) for c in candidates]
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/months/{month}/close-summary", response_model=MonthCloseSummary)
def get_close_summary(
    month: str,
    svc: MonthlyMvpService = Depends(_service),
) -> MonthCloseSummary:
    year, mon = _parse_month(month)
    try:
        summary = svc.get_month_close_summary(year, mon)
        return MonthCloseSummary(**summary)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/months/{month}/close", response_model=MonthCloseResponse)
def close_month(
    month: str,
    body: MonthCloseRequest,
    svc: MonthlyMvpService = Depends(_service),
    session: Session = Depends(get_session),
) -> MonthCloseResponse:
    year, mon = _parse_month(month)
    try:
        from forge.db.models.player import Player

        record = svc.close_month(
            year=year,
            month=mon,
            mvp_player_id=body.mvp_player_id,
            reason=body.reason,
            admin_id=_DEFAULT_ADMIN_ID,
        )
        session.commit()

        player = session.get(Player, record.player_id)
        display_name = player.display_name if player else f"Player {record.player_id}"

        from forge.db.models.achievement_unlock import AchievementUnlock
        from sqlalchemy import select

        ach_unlocked = session.scalar(
            select(AchievementUnlock).where(
                AchievementUnlock.player_id == record.player_id,
                AchievementUnlock.achievement_code == "ACH04",
            )
        ) is not None

        return MonthCloseResponse(
            period_label=record.period_label,
            player_id=record.player_id,
            display_name=display_name,
            sp_awarded=float(record.sp_reward),
            ach04_unlocked=ach_unlocked,
            message=(
                f"MVP del Mes {record.period_label}: {display_name} "
                f"+{record.sp_reward} SP (B17M)"
            ),
        )
    except (NotFoundError, RuleViolationError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/months/{month}/edit-mvp", response_model=MonthCloseResponse)
def edit_monthly_mvp(
    month: str,
    body: MonthlyMvpEditRequest,
    svc: MonthlyMvpService = Depends(_service),
    session: Session = Depends(get_session),
) -> MonthCloseResponse:
    year, mon = _parse_month(month)
    try:
        record = svc.edit_monthly_mvp(
            year=year,
            month=mon,
            new_player_id=body.new_player_id,
            reason=body.reason,
            admin_id=_DEFAULT_ADMIN_ID,
        )
        session.commit()

        from forge.db.models.player import Player

        player = session.get(Player, record.player_id)
        display_name = player.display_name if player else f"Player {record.player_id}"

        return MonthCloseResponse(
            period_label=record.period_label,
            player_id=record.player_id,
            display_name=display_name,
            sp_awarded=float(record.sp_reward),
            ach04_unlocked=False,
            message=(
                f"MVP del Mes {record.period_label} actualizado: {display_name} "
                f"+{record.sp_reward} SP (B17M)"
            ),
        )
    except (NotFoundError, RuleViolationError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/months/mvp-history", response_model=list[MonthlyMvpHistoryItem])
def get_mvp_history(
    year: int | None = Query(None, description="Filtrar por año"),
    player_id: int | None = Query(None, description="Filtrar por player"),
    svc: MonthlyMvpService = Depends(_service),
) -> list[MonthlyMvpHistoryItem]:
    history = svc.get_history(year=year, player_id=player_id)
    return [MonthlyMvpHistoryItem(**item) for item in history]
