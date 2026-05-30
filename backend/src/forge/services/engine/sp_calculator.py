"""
Calculadora de Score Points (SP) — fórmula completa JPDS v2.0.

Fórmula:
  sp_base  = CP × M_calidad × M_eficiencia × M_dificultad × M_lider × M_cooperacion
  sp_final = sp_base + Σ(bonos_flat) − Σ(penalizaciones_flat)

sp_final siempre ≥ 0 (no hay SP negativo).

Este módulo es PURO: no lee ni escribe DB. Recibe una subtask con todos los
campos calculados y retorna un dict de componentes listo para persistir.
La suma de SpAdjustments se pasa externamente (el orquestador los lee de DB).
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.db.models.subtask import Subtask
from forge.services.engine.multiplier_calculator import calc_all_multipliers

# ── Tipos de retorno ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class SpComponents:
    """
    Componentes desglosados del cálculo SP.

    Todos los campos mapean 1:1 a columnas del modelo Subtask.
    """

    # Multiplicadores
    m_calidad: float
    m_eficiencia: float
    m_dificultad: float
    m_lider: float
    m_cooperacion: float

    # Puntos base (CP × multiplicadores)
    sp_base: float

    # Ajustes planos externos (suma de SpAdjustments del orquestador)
    sp_flat_bonus: float    # Suma de ajustes tipo "bonus"
    sp_penalty: float       # Suma de ajustes tipo "penalty" (valor positivo)

    # Resultado final
    sp_final: float         # = sp_base + sp_flat_bonus − sp_penalty  (≥ 0)

    def as_dict(self) -> dict[str, float]:
        """Retornar como dict con claves = columnas del modelo Subtask."""
        return {
            "m_calidad": self.m_calidad,
            "m_eficiencia": self.m_eficiencia,
            "m_dificultad": self.m_dificultad,
            "m_lider": self.m_lider,
            "m_cooperacion": self.m_cooperacion,
            "sp_base": self.sp_base,
            "sp_flat_bonus": self.sp_flat_bonus,
            "sp_penalty": self.sp_penalty,
            "sp_final": self.sp_final,
        }


# ── Función principal ─────────────────────────────────────────────────────


def calculate_sp(
    subtask: Subtask,
    *,
    sp_flat_bonus: float = 0.0,
    sp_penalty: float = 0.0,
) -> SpComponents:
    """
    Calcular SP completo para una Subtask.

    La función asume que los campos de tiempo y qa ya están actualizados
    en el objeto subtask (el orquestador corre recompute_time_metrics antes).

    Args:
        subtask: Instancia del modelo Subtask con datos actualizados.
        sp_flat_bonus: Suma de todos los SpAdjustments tipo "bonus" en DB.
        sp_penalty: Suma de todos los SpAdjustments tipo "penalty" en DB
                    (valor positivo; se restará del total).

    Returns:
        SpComponents con todos los valores desglosados.
    """
    cp: float = float(subtask.cp or 0)

    # Si la tarea no tiene CP asignado, SP = 0 (no hay nada que premiar)
    if cp <= 0:
        return SpComponents(
            m_calidad=1.0,
            m_eficiencia=1.0,
            m_dificultad=1.0,
            m_lider=1.0,
            m_cooperacion=1.0,
            sp_base=0.0,
            sp_flat_bonus=sp_flat_bonus,
            sp_penalty=sp_penalty,
            sp_final=0.0,
        )

    mults = calc_all_multipliers(subtask)

    sp_base = (
        cp
        * mults["m_calidad"]
        * mults["m_eficiencia"]
        * mults["m_dificultad"]
        * mults["m_lider"]
        * mults["m_cooperacion"]
    )

    # Redondear sp_base a 2 decimales para evitar ruido floating-point
    sp_base = round(sp_base, 2)

    raw_final = sp_base + sp_flat_bonus - sp_penalty
    sp_final = round(max(0.0, raw_final), 2)

    return SpComponents(
        m_calidad=mults["m_calidad"],
        m_eficiencia=mults["m_eficiencia"],
        m_dificultad=mults["m_dificultad"],
        m_lider=mults["m_lider"],
        m_cooperacion=mults["m_cooperacion"],
        sp_base=sp_base,
        sp_flat_bonus=round(sp_flat_bonus, 2),
        sp_penalty=round(sp_penalty, 2),
        sp_final=sp_final,
    )


# ── Helpers de verificación ───────────────────────────────────────────────


def needs_recalculation(subtask: Subtask, current_version_id: int) -> bool:
    """
    Indica si la subtask debe recalcularse.

    Una subtask necesita recálculo si:
      a) Nunca ha sido calculada (sp_last_calculated_at IS NULL)
      b) La versión del engine cambió desde el último cálculo

    Args:
        subtask: Modelo Subtask cargado de DB.
        current_version_id: ID del EngineVersion activo en DB.

    Returns:
        True si se requiere recálculo.
    """
    if subtask.sp_last_calculated_at is None:
        return True
    if subtask.engine_version_id != current_version_id:
        return True
    return False
