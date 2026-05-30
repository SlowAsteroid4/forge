"""Motor de cálculo CP/SP — JPDS v2.0."""

from forge.services.engine.cp_calculator import (
    CP_TABLE,
    APPROVAL_REQUIRED,
    REJECTED_SIZES,
    assign_cp,
    calculate_cp,
    is_rejected_size,
    needs_approval,
    validate_immutability,
)
from forge.services.engine.debuff_detector import DetectedDebuff, detect_all
from forge.services.engine.engine_orchestrator import (
    recalculate_cycle,
    recalculate_sprint,  # DEPRECATED: usar recalculate_cycle
    recalculate_subtask,
)
from forge.services.engine.multiplier_calculator import (
    calc_all_multipliers,
    calc_m_calidad,
    calc_m_cooperacion,
    calc_m_dificultad,
    calc_m_eficiencia,
    calc_m_lider,
)
from forge.services.engine.sp_calculator import SpComponents, calculate_sp, needs_recalculation
from forge.services.engine.time_calculator import recompute_time_metrics

__all__ = [
    # CP
    "CP_TABLE",
    "APPROVAL_REQUIRED",
    "REJECTED_SIZES",
    "calculate_cp",
    "needs_approval",
    "is_rejected_size",
    "validate_immutability",
    "assign_cp",
    # Time
    "recompute_time_metrics",
    # Multipliers
    "calc_m_calidad",
    "calc_m_eficiencia",
    "calc_m_dificultad",
    "calc_m_lider",
    "calc_m_cooperacion",
    "calc_all_multipliers",
    # Debuffs
    "DetectedDebuff",
    "detect_all",
    # SP
    "SpComponents",
    "calculate_sp",
    "needs_recalculation",
    # Orchestrator
    "recalculate_subtask",
    "recalculate_cycle",
    "recalculate_sprint",  # DEPRECATED
]
