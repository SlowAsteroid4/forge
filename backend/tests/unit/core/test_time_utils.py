"""Tests de time_utils (cálculo de horas hábiles)."""

from datetime import datetime

from forge.core.time_utils import business_hours, is_business_time


def test_business_hours_same_day():
    """Test: horas hábiles en el mismo día."""
    # Lunes 9:00 a 14:00 (5 horas)
    start = datetime(2026, 5, 18, 9, 0)  # Lunes
    end = datetime(2026, 5, 18, 14, 0)

    result = business_hours(start, end)
    assert result == 5.0


def test_business_hours_skip_lunch():
    """Test: horas hábiles saltando comida."""
    # Lunes 9:00 a 16:00 = 5h (9-14) + 1h (15-16) = 6h
    start = datetime(2026, 5, 18, 9, 0)
    end = datetime(2026, 5, 18, 16, 0)

    result = business_hours(start, end)
    assert result == 6.0


def test_business_hours_skip_weekend():
    """Test: horas hábiles saltando fin de semana."""
    # Viernes 9:00 a Lunes 10:00
    # Viernes: 8h completo
    # Lunes: 1h (9-10)
    # Total: 9h
    start = datetime(2026, 5, 22, 9, 0)  # Viernes
    end = datetime(2026, 5, 25, 10, 0)  # Lunes

    result = business_hours(start, end)
    assert result == 9.0


def test_is_business_time():
    """Test: verificar si es horario hábil."""
    # Lunes 10:00 = hábil
    assert is_business_time(datetime(2026, 5, 18, 10, 0)) is True

    # Lunes 14:30 (hora de comida) = no hábil
    assert is_business_time(datetime(2026, 5, 18, 14, 30)) is False

    # Sábado 10:00 = no hábil
    assert is_business_time(datetime(2026, 5, 23, 10, 0)) is False

    # Lunes 19:00 (después de horario) = no hábil
    assert is_business_time(datetime(2026, 5, 18, 19, 0)) is False
