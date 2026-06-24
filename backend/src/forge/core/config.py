"""Configuración de la aplicación usando Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración global de Forge."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Aplicación
    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "Forge"
    app_version: str = "0.1.0"
    debug: bool = True
    log_level: str = "INFO"

    # Base de Datos
    database_url: str = "sqlite:///./forge.db"

    # Jira Integration
    jira_instance_url: str = Field(..., description="URL de la instancia de Jira")
    jira_user_email: str = Field(..., description="Email del usuario de API")
    jira_api_token: str = Field(..., description="API token de Jira")

    # Security
    encryption_key: str = Field(..., description="Clave para cifrar datos sensibles")

    # API Settings
    api_v1_prefix: str = "/api"
    cors_origins: str = "http://localhost:3000,http://localhost:8000"
    max_upload_size_mb: int = 50

    # Business Rules
    business_hours_start: str = "09:00"
    business_hours_end: str = "18:00"
    business_hours_lunch_start: str = "14:00"
    business_hours_lunch_end: str = "15:00"
    business_hours_timezone: str = "America/Mexico_City"

    # Engine Config
    default_engine_version: str = "v2.0"
    enable_auto_recalc: bool = True

    # Jira Sync Settings
    sync_batch_size: int = 50
    sync_timeout_seconds: int = 300
    sync_retry_max: int = 3

    # Feature Flags
    enable_arena: bool = True
    enable_achievements: bool = True
    enable_shop: bool = True
    enable_forecast: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins como lista."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """
    Obtener configuración (cacheada).

    Use esta función en lugar de instanciar Settings() directamente
    para aprovechar el cache y evitar leer .env múltiples veces.
    """
    return Settings()
