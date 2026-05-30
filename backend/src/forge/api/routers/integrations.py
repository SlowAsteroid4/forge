"""API Router para integraciones externas (UC-01: Jira)."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from forge.core.exceptions import JiraAPIError
from forge.db.session import get_session
from forge.etl.jira_client import JiraClient
from forge.etl.sync_orchestrator import SyncOrchestrator

router = APIRouter(tags=["integrations"])


@router.post("/jira/test-connection")
async def test_jira_connection() -> dict[str, Any]:
    """
    UC-01: Probar conexión a Jira.

    Verifica credenciales y acceso a la API de Jira.

    Returns:
        Estado de la conexión e info del usuario
    """
    client = JiraClient()
    try:
        result = await client.test_connection()
        return result
    except JiraAPIError as e:
        raise HTTPException(
            status_code=e.details.get("status_code", 500),
            detail={
                "error": "jira_connection_failed",
                "message": e.message,
                "details": e.details,
            },
        )


@router.post("/jira/sync")
async def sync_jira(
    jql: str | None = None,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """
    UC-01: Sincronizar issues de Jira.

    Args:
        jql: Query JQL personalizada (default: updated >= -14d)

    Returns:
        Estadísticas de la sincronización
    """
    orchestrator = SyncOrchestrator(session)
    try:
        stats = await orchestrator.sync_all(jql=jql)
        return {
            "status": "success",
            "stats": stats,
        }
    except JiraAPIError as e:
        raise HTTPException(
            status_code=e.details.get("status_code", 500),
            detail={
                "error": "jira_sync_failed",
                "message": e.message,
                "details": e.details,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "sync_failed",
                "message": str(e),
            },
        )


@router.get("/jira/status")
async def get_jira_status(session: Session = Depends(get_session)) -> dict[str, Any]:
    """
    UC-01: Obtener estado de la integración con Jira.

    Returns:
        Estado actual de la sincronización
    """
    # TODO: Implementar tracking de último sync
    return {
        "status": "configured",
        "last_sync": None,
        "next_sync": None,
    }
