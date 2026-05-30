"""Cliente HTTP para Jira Cloud API."""

import base64
from typing import Any

import httpx

from forge.core.config import get_settings
from forge.core.exceptions import JiraAPIError
from forge.core.logging import get_logger

logger = get_logger(__name__)


class JiraClient:
    """Cliente para interactuar con Jira Cloud API."""

    def __init__(self) -> None:
        """Inicializar cliente con credenciales desde config."""
        settings = get_settings()
        self.instance_url = settings.jira_instance_url.rstrip("/")
        self.user_email = settings.jira_user_email
        self.api_token = settings.jira_api_token

        # Basic Auth para Jira Cloud
        credentials = f"{self.user_email}:{self.api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()

        self.headers = {
            "Authorization": f"Basic {encoded}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        self.timeout = settings.sync_timeout_seconds

    async def test_connection(self) -> dict[str, Any]:
        """
        Probar conexión a Jira.

        Returns:
            Info del servidor y usuario actual

        Raises:
            JiraAPIError: Si falla la conexión
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Test: obtener info del usuario actual
                response = await client.get(
                    f"{self.instance_url}/rest/api/3/myself",
                    headers=self.headers,
                )
                response.raise_for_status()
                user_info = response.json()

                logger.info(f"Conexión exitosa a Jira: {user_info.get('displayName')}")
                return {
                    "status": "connected",
                    "user": user_info.get("displayName"),
                    "account_id": user_info.get("accountId"),
                    "instance": self.instance_url,
                }
            except httpx.HTTPStatusError as e:
                raise JiraAPIError(
                    status_code=e.response.status_code,
                    message=str(e),
                    endpoint="/rest/api/3/myself",
                ) from e
            except httpx.RequestError as e:
                raise JiraAPIError(
                    status_code=0,
                    message=f"Error de conexión: {str(e)}",
                    endpoint="/rest/api/3/myself",
                ) from e

    async def search_issues(
        self,
        jql: str,
        max_results: int = 50,
        next_page_token: str | None = None,
        expand: str = "changelog",
    ) -> dict[str, Any]:

        payload = {
            "jql": jql,
            "maxResults": max_results,
            "expand": expand,
            "fields": [
                "summary",
                "status",
                "issuetype",
                "parent",
                "assignee",
                "created",
                "updated",
                "resolutiondate",
                "customfield_10016",
                "customfield_10020",
                "customfield_10851",  # Complexity (talla: XS/S/M/L/XL/XXL)
            ],
        }

        if next_page_token:
            payload["nextPageToken"] = next_page_token

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.instance_url}/rest/api/3/search/jql",
                    headers=self.headers,
                    json=payload,
                )

                response.raise_for_status()

                data = response.json()

                logger.info(f"JQL search: {len(data.get('issues', []))} resultados")

                return data

            except httpx.HTTPStatusError as e:
                error_text = e.response.text

                logger.error(f"Jira API error: {error_text}")

                raise JiraAPIError(
                    status_code=e.response.status_code,
                    message=error_text,
                    endpoint="/rest/api/3/search/jql",
                ) from e

    async def get_issue(self, issue_key: str, expand: str = "changelog") -> dict[str, Any]:
        """
        Obtener issue individual.

        Args:
            issue_key: Key del issue (ej: PROJ-123)
            expand: Campos adicionales a expandir

        Returns:
            Payload completo del issue

        Raises:
            JiraAPIError: Si falla la obtención
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.instance_url}/rest/api/3/issue/{issue_key}",
                    headers=self.headers,
                    params={"expand": expand},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise JiraAPIError(
                    status_code=e.response.status_code,
                    message=str(e),
                    endpoint=f"/rest/api/3/issue/{issue_key}",
                ) from e

    async def get_projects(self) -> list[dict[str, Any]]:
        """
        Obtener lista de proyectos.

        Returns:
            Lista de proyectos

        Raises:
            JiraAPIError: Si falla la obtención
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.instance_url}/rest/api/3/project",
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise JiraAPIError(
                    status_code=e.response.status_code,
                    message=str(e),
                    endpoint="/rest/api/3/project",
                ) from e
