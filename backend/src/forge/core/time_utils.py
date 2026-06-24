"""Utilidades para cálculo de tiempo hábil en CDMX."""

from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from forge.core.config import get_settings

# Constantes de horario hábil (Lun-Vie, 9-14 y 15-18 CDMX)
BUSINESS_DAYS = [0, 1, 2, 3, 4]  # Lunes a Viernes
BUSINESS_HOURS_PER_DAY = 8.0  # 9-14 (5h) + 15-18 (3h)


def get_business_hours_config() -> dict[str, Any]:
    """Obtener configuración de horario hábil desde settings."""
    settings = get_settings()
    return {
        "start": time.fromisoformat(settings.business_hours_start),
        "end": time.fromisoformat(settings.business_hours_end),
        "lunch_start": time.fromisoformat(settings.business_hours_lunch_start),
        "lunch_end": time.fromisoformat(settings.business_hours_lunch_end),
        "timezone": ZoneInfo(settings.business_hours_timezone),
    }


def business_seconds(start_dt: datetime, end_dt: datetime) -> float:
    """
    Calcular segundos hábiles entre dos timestamps.

    Cuenta solo tiempo de Lun-Vie, 9-14 y 15-18 en horario CDMX.
    Excluye fines de semana y hora de comida (14-15).

    Args:
        start_dt: Timestamp inicial (aware o naive)
        end_dt: Timestamp final (aware o naive)

    Returns:
        Segundos hábiles transcurridos (float)
    """
    config = get_business_hours_config()
    tz = config["timezone"]

    # Asegurar que ambos timestamps sean aware
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=tz)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=tz)

    # Convertir a CDMX
    start_dt = start_dt.astimezone(tz)
    end_dt = end_dt.astimezone(tz)

    if end_dt <= start_dt:
        return 0.0

    total_seconds = 0.0
    current = start_dt

    while current.date() <= end_dt.date():
        # Si no es día hábil, saltar
        if current.weekday() not in BUSINESS_DAYS:
            current = (current + timedelta(days=1)).replace(
                hour=config["start"].hour,
                minute=config["start"].minute,
                second=0,
                microsecond=0,
            )
            continue

        # Horario del día actual
        day_start = current.replace(
            hour=config["start"].hour, minute=config["start"].minute, second=0, microsecond=0
        )
        day_end = current.replace(
            hour=config["end"].hour, minute=config["end"].minute, second=0, microsecond=0
        )
        lunch_start = current.replace(
            hour=config["lunch_start"].hour,
            minute=config["lunch_start"].minute,
            second=0,
            microsecond=0,
        )
        lunch_end = current.replace(
            hour=config["lunch_end"].hour,
            minute=config["lunch_end"].minute,
            second=0,
            microsecond=0,
        )

        # Determinar ventanas a contar en este día
        if current.date() == start_dt.date():
            # Primer día: desde current hasta lunch o fin de día
            window_start = max(current, day_start)
        else:
            # Días intermedios: desde inicio de día
            window_start = day_start

        if current.date() == end_dt.date():
            # Último día: hasta end_dt
            window_end = min(end_dt, day_end)
        else:
            # Días intermedios: hasta fin de día
            window_end = day_end

        # Contar antes del almuerzo (9-14)
        morning_start = max(window_start, day_start)
        morning_end = min(window_end, lunch_start)
        if morning_end > morning_start:
            total_seconds += (morning_end - morning_start).total_seconds()

        # Contar después del almuerzo (15-18)
        afternoon_start = max(window_start, lunch_end)
        afternoon_end = min(window_end, day_end)
        if afternoon_end > afternoon_start:
            total_seconds += (afternoon_end - afternoon_start).total_seconds()

        # Avanzar al siguiente día
        current = (current + timedelta(days=1)).replace(
            hour=config["start"].hour,
            minute=config["start"].minute,
            second=0,
            microsecond=0,
        )

    return total_seconds


def business_hours(start_dt: datetime, end_dt: datetime) -> float:
    """
    Calcular horas hábiles entre dos timestamps.

    Args:
        start_dt: Timestamp inicial
        end_dt: Timestamp final

    Returns:
        Horas hábiles transcurridas (float)
    """
    return business_seconds(start_dt, end_dt) / 3600.0


def is_business_time(dt: datetime) -> bool:
    """
    Verificar si un timestamp cae en horario hábil.

    Args:
        dt: Timestamp a verificar

    Returns:
        True si es horario hábil, False si no
    """
    config = get_business_hours_config()
    tz = config["timezone"]

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    dt = dt.astimezone(tz)

    # Verificar día hábil
    if dt.weekday() not in BUSINESS_DAYS:
        return False

    # Verificar hora
    current_time = dt.time()
    lunch_start = config["lunch_start"]
    lunch_end = config["lunch_end"]
    start = config["start"]
    end = config["end"]

    # Mañana: 9-14
    if start <= current_time < lunch_start:
        return True

    # Tarde: 15-18
    if lunch_end <= current_time < end:
        return True

    return False
