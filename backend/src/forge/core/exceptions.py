"""Excepciones personalizadas de Forge."""


class ForgeError(Exception):
    """Excepción base para todos los errores de Forge."""

    def __init__(self, message: str, details: dict[str, any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(ForgeError):
    """Recurso no encontrado."""

    pass


class RuleViolationError(ForgeError):
    """Violación de regla de negocio."""

    pass


class CPImmutableError(RuleViolationError):
    """Intento de modificar CP después de aprobación."""

    def __init__(self, subtask_key: str) -> None:
        super().__init__(
            f"CP inmutable: la sub-task {subtask_key} ya tiene CP aprobado y no puede modificarse",
            details={"subtask_key": subtask_key},
        )


class AppendOnlyViolationError(RuleViolationError):
    """Intento de modificar registro append-only."""

    def __init__(self, table: str, record_id: int) -> None:
        super().__init__(
            f"Violación append-only: no se puede modificar {table} id={record_id}",
            details={"table": table, "record_id": record_id},
        )


class MonthlySpendingLimitError(RuleViolationError):
    """Excede el techo de gasto mensual."""

    def __init__(self, player_id: int, current: float, limit: float) -> None:
        super().__init__(
            f"El player {player_id} excedería el techo mensual: ${current:.2f} + nuevo canje > ${limit:.2f}",
            details={"player_id": player_id, "current": current, "limit": limit},
        )


class ClassChangeRestrictedError(RuleViolationError):
    """Intento de cambiar clase antes del trimestre."""

    def __init__(self, player_id: int, days_remaining: int) -> None:
        super().__init__(
            f"Player {player_id} debe esperar {days_remaining} días para cambiar de clase",
            details={"player_id": player_id, "days_remaining": days_remaining},
        )


class IntegrationError(ForgeError):
    """Error en integración externa (Jira, GitHub, etc.)."""

    pass


class JiraAPIError(IntegrationError):
    """Error específico de API de Jira."""

    def __init__(self, status_code: int, message: str, endpoint: str | None = None) -> None:
        super().__init__(
            f"Jira API error (status {status_code}): {message}",
            details={"status_code": status_code, "endpoint": endpoint},
        )
