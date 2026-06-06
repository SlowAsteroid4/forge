"""ForecastService — UC-07: P30/P50/P85 forecast por épica (on-the-fly, read-only)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from forge.services.engine.forecast import EpicForecast, ForecastCalculator


class ForecastService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_epic_forecasts(
        self,
        project_code: str | None = None,
        epic_status: str | None = None,
    ) -> dict[str, Any]:
        """Lista de épicas activas con escenarios opt/real/cons (on-the-fly).

        El cálculo es siempre fresco (no usa forecast_snapshots para el MVP).
        """
        calc = ForecastCalculator(self._session)
        epics = calc.compute_all(project_code=project_code, epic_status=epic_status)
        return {
            "epics": epics,
            "n_closed_cycles": calc._n_closed,
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_epic_detail(self, epic_key: str) -> EpicForecast | None:
        """Detalle de una épica específica con desglose por área."""
        calc = ForecastCalculator(self._session)
        return calc.compute_one(epic_key)

    def recalculate_open_epics(self, cycle_id: int) -> None:
        """Hook disparado al cerrar un ciclo.

        En el MVP el forecast es on-the-fly; este método es un no-op intencional.
        La tabla forecast_snapshots queda para cuando se quiera histórico de proyecciones.
        """
        pass
