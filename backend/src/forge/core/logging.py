"""Configuración de logging estructurado."""

import logging
import sys
from typing import Any

from forge.core.config import get_settings


def setup_logging() -> None:
    """
    Configurar logging de la aplicación.

    Usa formato estructurado con nivel configurable desde settings.
    """
    settings = get_settings()

    # Formato
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Handler a stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

    # Logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())
    root_logger.addHandler(handler)

    # Silenciar loggers ruidosos en development
    if settings.app_env == "development":
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Obtener logger con nombre específico.

    Args:
        name: Nombre del logger (usualmente __name__)

    Returns:
        Logger configurado
    """
    return logging.getLogger(name)


class StructuredLogger:
    """
    Logger con soporte para campos estructurados.

    Útil para agregar contexto adicional a los logs.
    """

    def __init__(self, name: str) -> None:
        self.logger = logging.getLogger(name)
        self.context: dict[str, Any] = {}

    def with_context(self, **kwargs: Any) -> "StructuredLogger":
        """
        Crear un nuevo logger con contexto adicional.

        Args:
            **kwargs: Campos de contexto

        Returns:
            Nuevo logger con contexto
        """
        new_logger = StructuredLogger(self.logger.name)
        new_logger.context = {**self.context, **kwargs}
        return new_logger

    def _format_message(self, message: str) -> str:
        """Formatear mensaje con contexto."""
        if not self.context:
            return message

        context_str = " | ".join(f"{k}={v}" for k, v in self.context.items())
        return f"{message} | {context_str}"

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug con contexto."""
        self.logger.debug(self._format_message(message), extra=kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info con contexto."""
        self.logger.info(self._format_message(message), extra=kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning con contexto."""
        self.logger.warning(self._format_message(message), extra=kwargs)

    def error(self, message: str, exc_info: bool = False, **kwargs: Any) -> None:
        """Log error con contexto."""
        self.logger.error(self._format_message(message), exc_info=exc_info, extra=kwargs)
