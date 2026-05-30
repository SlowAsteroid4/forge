"""
Calculadoras de multiplicadores SP (JPDS v2.0).

Fórmula:
  SP = CP × M_calidad × M_eficiencia × M_dificultad × M_lider × M_cooperacion
       + bonos_flat − penalizaciones_flat

Todos los multiplicadores default a 1.0.
Todos los multiplicadores están acotados a los rangos máximos del engine YAML:
  M_calidad    [0.85, 1.20]
  M_eficiencia [0.75, 1.20]
  M_dificultad [1.00, 1.30]
  M_lider      [1.00, 1.20]  (MVP: siempre 1.0, sin integración GitHub)
  M_cooperacion[1.00, 1.15]
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from forge.core.time_utils import business_hours
from forge.db.models.subtask import Subtask

# ── M_calidad ─────────────────────────────────────────────────────────────
_M_CALIDAD_FIRST_PASS: float = 1.20   # Pasó QA en primer intento
_M_CALIDAD_DEFAULT: float = 1.00      # 1 o 2 intentos
_M_CALIDAD_MULTIPLE: float = 0.85     # ≥ 3 intentos (inestabilidad)
_QA_ATTEMPTS_THRESHOLD: int = 3


def calc_m_calidad(subtask: Subtask) -> float:
    """
    Multiplicador de calidad basado en resultados de QA.

    Reglas:
      qa_first_pass = True               → 1.20 (bonus calidad)
      qa_attempts >= 3                   → 0.85 (penalización)
      cualquier otro caso (1-2 intentos) → 1.00
    """
    if subtask.qa_first_pass is True:
        return _M_CALIDAD_FIRST_PASS
    if (subtask.qa_attempts or 0) >= _QA_ATTEMPTS_THRESHOLD:
        return _M_CALIDAD_MULTIPLE
    return _M_CALIDAD_DEFAULT


# ── M_eficiencia ──────────────────────────────────────────────────────────
# Horas hábiles esperadas por talla JPDS v2.0.
# Derivadas empíricamente: ~4h base × escala Fibonacci truncada.
_EXPECTED_HOURS_BY_SIZE: dict[str, float] = {
    "XS": 4.0,
    "S": 8.0,
    "M": 16.0,
    "L": 32.0,
    "XL": 56.0,
    "XXL": 80.0,  # Rechazada, pero por si PM la aprueba igualmente
}

# Tabla de ratio → multiplicador de eficiencia
# ratio = adj_ct_biz_hours / expected_hours
_EFICIENCIA_BRACKETS: list[tuple[float, float]] = [
    # (ratio_max_exclusivo, multiplicador)
    (0.60, 1.20),   # Terminó >40% más rápido → bonus eficiencia
    (0.85, 1.10),   # Terminó algo más rápido de lo esperado
    (1.20, 1.00),   # Dentro del rango esperado
    (2.00, 0.90),   # Tardó hasta el doble
    (float("inf"), 0.75),  # Tardó más del doble
]


def calc_m_eficiencia(subtask: Subtask) -> float:
    """
    Multiplicador de eficiencia basado en tiempo real vs. esperado por talla.

    Fórmula:
      ratio = adj_ct_biz_hours / horas_esperadas_para_talla

    Si no hay talla asignada o no se conoce el cycle time → 1.0 (neutral).
    """
    if not subtask.complexity_size or subtask.adj_ct_biz_hours is None:
        return 1.0

    size = subtask.complexity_size.strip().upper()
    expected = _EXPECTED_HOURS_BY_SIZE.get(size)
    if expected is None or expected <= 0:
        return 1.0

    ratio = subtask.adj_ct_biz_hours / expected
    for max_ratio, multiplier in _EFICIENCIA_BRACKETS:
        if ratio < max_ratio:
            return multiplier
    return 0.75  # fallback (ya cubierto por el último bracket)


# ── M_dificultad ──────────────────────────────────────────────────────────
# Catálogo B06-B10 (campo difficulty_modifier_raw en Subtask).
# Valores raw del custom field de Jira (string exacto que devuelve la API).
# El catálogo forge_catalogos_v1 define estos códigos; aquí mapeamos a float.
_DIFFICULTY_MAP: dict[str, float] = {
    # Código catálogo → (raw Jira string, multiplicador)
    # B06: Sin dificultad adicional / Normal
    "B06": 1.00,
    "Normal": 1.00,
    "Sin modificador": 1.00,
    # B07: Complejidad técnica leve (nueva librería, deuda técnica menor)
    "B07": 1.05,
    "Leve": 1.05,
    # B08: Complejidad media (integración externa, refactoring parcial)
    "B08": 1.10,
    "Media": 1.10,
    # B09: Alta complejidad (múltiples sistemas, seguridad crítica)
    "B09": 1.20,
    "Alta": 1.20,
    # B10: Máxima complejidad (arquitectura crítica, migración completa)
    "B10": 1.30,
    "Muy alta": 1.30,
    "Máxima": 1.30,
}
_M_DIFICULTAD_DEFAULT: float = 1.00


def calc_m_dificultad(subtask: Subtask) -> float:
    """
    Multiplicador de dificultad desde el campo de Jira difficulty_modifier_raw.

    Acepta tanto el código del catálogo (B06-B10) como la etiqueta en español.
    Si el campo es None o no reconocido → 1.0.
    """
    raw = subtask.difficulty_modifier_raw
    if not raw:
        return _M_DIFICULTAD_DEFAULT
    return _DIFFICULTY_MAP.get(raw.strip(), _M_DIFICULTAD_DEFAULT)


# ── M_lider ───────────────────────────────────────────────────────────────


def calc_m_lider(subtask: Subtask) -> float:
    """
    Multiplicador de liderazgo técnico.

    MVP: siempre 1.0.
    En versiones futuras se calculará a partir de métricas de GitHub (PRs
    revisados, mentoring detectado en comentarios, etc.).
    """
    return 1.0


# ── M_cooperacion ─────────────────────────────────────────────────────────
_M_COOPERACION_BONUS: float = 1.15  # Desbloqueó a compañero en <24h hábiles
_M_COOPERACION_DEFAULT: float = 1.00
_UNBLOCK_WINDOW_BIZ_HOURS: float = 24.0  # Umbral para bonus de cooperación

# Estados que indican que alguien estaba bloqueado
_BLOCKED_STATES: frozenset[str] = frozenset({"Blocked", "Bloqueado", "Waiting", "Esperando"})


def calc_m_cooperacion(subtask: Subtask) -> float:
    """
    Multiplicador de cooperación.

    Detecta si la subtask estuvo bloqueada y fue desbloqueada en menos de
    24 horas hábiles. Esto indica que alguien del equipo ayudó a resolverlo.

    Requiere raw_changelog almacenado. Si no hay changelog → 1.0.
    """
    if not subtask.raw_changelog:
        return _M_COOPERACION_DEFAULT

    try:
        payload = json.loads(subtask.raw_changelog)
    except (json.JSONDecodeError, TypeError):
        return _M_COOPERACION_DEFAULT

    histories: list[dict[str, Any]] = payload.get("histories", [])
    blocking_periods = _collect_blocking_periods(histories)

    for entered_at, exited_at in blocking_periods:
        if entered_at and exited_at:
            biz_time = business_hours(entered_at, exited_at)
            if 0 < biz_time <= _UNBLOCK_WINDOW_BIZ_HOURS:
                return _M_COOPERACION_BONUS

    return _M_COOPERACION_DEFAULT


def _collect_blocking_periods(
    histories: list[dict[str, Any]],
) -> list[tuple[datetime | None, datetime | None]]:
    """Pares (entrada_bloqueado, salida_bloqueado) desde el changelog."""
    sorted_h = sorted(histories, key=lambda h: h.get("created", ""))
    periods: list[tuple[datetime | None, datetime | None]] = []
    entered_at: datetime | None = None

    for history in sorted_h:
        ts_str: str | None = history.get("created")
        ts = _parse_ts(ts_str)
        for item in history.get("items", []):
            if item.get("field") != "status":
                continue
            to_status: str = item.get("toString") or ""
            from_status: str = item.get("fromString") or ""

            if to_status in _BLOCKED_STATES and entered_at is None:
                entered_at = ts
            elif from_status in _BLOCKED_STATES and entered_at is not None:
                periods.append((entered_at, ts))
                entered_at = None

    return periods


def _parse_ts(ts_str: str | None) -> datetime | None:
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


# ── Helper: calcular todos de una vez ─────────────────────────────────────


def calc_all_multipliers(subtask: Subtask) -> dict[str, float]:
    """
    Calcula los 5 multiplicadores en un solo paso.

    Returns:
        Dict con claves que mapean directamente a columnas del modelo Subtask.
    """
    return {
        "m_calidad": calc_m_calidad(subtask),
        "m_eficiencia": calc_m_eficiencia(subtask),
        "m_dificultad": calc_m_dificultad(subtask),
        "m_lider": calc_m_lider(subtask),
        "m_cooperacion": calc_m_cooperacion(subtask),
    }
