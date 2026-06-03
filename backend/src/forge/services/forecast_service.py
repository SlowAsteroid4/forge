"""ForecastService — stub hasta WP-05 (P30/P50/P85 forecast por épica)."""

import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ForecastService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def recalculate_open_epics(self, cycle_id: int) -> None:
        """
        TODO (WP-05): Recalcular predicciones P30/P50/P85 para épicas abiertas.

        Al cierre de ciclo se dispara este hook para actualizar el pronóstico
        usando los datos del ciclo recién cerrado como entrada al modelo.
        Por ahora es un stub vacío que loguea la intención.
        """
        logger.info(
            f"forecast_service.recalculate_open_epics(cycle_id={cycle_id}) — "
            "STUB: implementar en WP-05."
        )
