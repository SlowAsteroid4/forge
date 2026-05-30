"""
Detector automático de debuffs (penalizaciones).

Implementa los debuffs DETECTABLES AUTOMÁTICAMENTE del catálogo JPDS v2.0:
  D01 — QA Primera Pasada Fallida       (qa_first_pass=False, 1 intento)
  D03 — Inestabilidad QA                (qa_attempts >= 3)
  D04 — Code Review Rechazado Múltiple  (review_rejections >= 2)
  D10 — Bloqueo Sin Resolución Oportuna (blocked_biz_hours > umbral)
  D11 — Tarea Fantasma / Abandonada     (no terminada, > N días hábiles sin avance)
  D13 — Cycle Overflow                  (ciclo cerrado, tarea no entregada)

Debuffs que NO se implementan aquí (requieren fuente externa / input manual):
  D02 Bug crítico en producción     → webhook de GitHub
  D05 Incumplimiento de SLA         → integración externa
  D06-D09, D12, D14-D16             → aprobación/rechazo manual PM

CONTRATO:
  - Ninguna función persiste nada en DB.
  - Cada detector devuelve `DetectedDebuff | None`.
  - `detect_all()` agrega los resultados y filtra None.
  - El orquestador persiste los debuffs usando SpAdjustmentRepository.
  - Para idempotencia: el orquestador NO crea un SpAdjustment si ya existe
    uno con el mismo (subtask_key, catalog_code).
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.db.models.cycle import Cycle
from forge.db.models.subtask import Subtask

# ── Tipo de retorno ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DetectedDebuff:
    """Datos de un debuff detectado, listos para persistir como SpAdjustment."""

    catalog_code: str       # Código catálogo: D01, D03, ...
    amount_sp: float        # Penalización en SP (positivo = se resta)
    reason: str             # Descripción legible del motivo


# ── Umbrales configurables ─────────────────────────────────────────────────
_D01_PENALTY: float = 0.5       # SP penalización por fallar primera pasada QA
_D03_PENALTY_PER_EXTRA: float = 1.0   # SP por cada intento extra de QA (> 2)
_D04_PENALTY_PER_EXTRA: float = 0.5   # SP por cada rechazo extra de review (> 1)
_D10_BLOCKED_THRESHOLD_HOURS: float = 8.0  # > 1 día hábil bloqueado → debuff
_D10_PENALTY: float = 1.0
_D11_INACTIVE_BIZ_HOURS: float = 40.0  # > 5 días hábiles sin entrega → fantasma
_D11_PENALTY: float = 2.0
_D13_PENALTY: float = 1.5       # No entregada cuando sprint cerró


# ── D01: QA Primera Pasada Fallida ─────────────────────────────────────────
def detect_d01(subtask: Subtask) -> DetectedDebuff | None:
    """
    D01 — QA Primera Pasada Fallida.

    Trigger: qa_first_pass IS FALSE Y qa_attempts == 1
    (Falló el único intento; si repitió más veces, D03 ya cubre el caso).

    Penalización: 0.5 SP
    """
    if subtask.qa_first_pass is False and (subtask.qa_attempts or 0) == 1:
        return DetectedDebuff(
            catalog_code="D01",
            amount_sp=_D01_PENALTY,
            reason="QA no pasó en primera revisión (intento único fallido).",
        )
    return None


# ── D03: Inestabilidad QA ─────────────────────────────────────────────────
def detect_d03(subtask: Subtask) -> DetectedDebuff | None:
    """
    D03 — Inestabilidad QA.

    Trigger: qa_attempts >= 3
    Penalización: (qa_attempts - 2) × 1.0 SP (acumulativa por intento).
    """
    attempts = subtask.qa_attempts or 0
    if attempts >= 3:
        extra = attempts - 2
        return DetectedDebuff(
            catalog_code="D03",
            amount_sp=extra * _D03_PENALTY_PER_EXTRA,
            reason=(
                f"Inestabilidad QA: {attempts} intentos "
                f"(+{extra} sobre el máximo de 2). "
                f"Penalización: {extra * _D03_PENALTY_PER_EXTRA:.1f} SP."
            ),
        )
    return None


# ── D04: Code Review Rechazado Múltiple ───────────────────────────────────
def detect_d04(subtask: Subtask) -> DetectedDebuff | None:
    """
    D04 — Code Review Rechazado Múltiple.

    Trigger: review_rejections >= 2
    Penalización: (review_rejections - 1) × 0.5 SP por rechazo extra.
    """
    rejections = subtask.review_rejections or 0
    if rejections >= 2:
        extra = rejections - 1
        return DetectedDebuff(
            catalog_code="D04",
            amount_sp=extra * _D04_PENALTY_PER_EXTRA,
            reason=(
                f"Code Review rechazado {rejections} veces "
                f"(+{extra} sobre el máximo de 1). "
                f"Penalización: {extra * _D04_PENALTY_PER_EXTRA:.1f} SP."
            ),
        )
    return None


# ── D10: Bloqueo Sin Resolución Oportuna ──────────────────────────────────
def detect_d10(subtask: Subtask) -> DetectedDebuff | None:
    """
    D10 — Bloqueo Sin Resolución Oportuna.

    Trigger: blocked_biz_hours > 8.0 (más de un día hábil en estado Blocked).
    Penalización: 1.0 SP fija.

    Nota: Este debuff se aplica aunque la tarea ya esté terminada, porque
    el bloqueo prolongado afecta al equipo.
    """
    blocked = subtask.blocked_biz_hours or 0.0
    if blocked > _D10_BLOCKED_THRESHOLD_HOURS:
        return DetectedDebuff(
            catalog_code="D10",
            amount_sp=_D10_PENALTY,
            reason=(
                f"Bloqueo excesivo: {blocked:.1f}h hábiles en estado Blocked "
                f"(umbral: {_D10_BLOCKED_THRESHOLD_HOURS}h). "
                f"Penalización: {_D10_PENALTY} SP."
            ),
        )
    return None


# ── D11: Tarea Fantasma / Abandonada ─────────────────────────────────────
def detect_d11(subtask: Subtask) -> DetectedDebuff | None:
    """
    D11 — Tarea Fantasma (Abandonada).

    Trigger:
      - status NO está en {Done, Cancelled}
      - done_at IS NULL
      - lt_biz_hours > 40h (>5 días hábiles sin completar)

    Penalización: 2.0 SP.

    Nota: lt_biz_hours se mide desde created_at, por lo que una tarea que
    lleva más de una semana de trabajo sin cerrarse se considera fantasma.
    """
    _terminal = {"Done", "Cancelled", "Cerrado", "Cancelado"}
    if subtask.status in _terminal:
        return None
    if subtask.done_at is not None:
        return None
    if (subtask.lt_biz_hours or 0.0) > _D11_INACTIVE_BIZ_HOURS:
        return DetectedDebuff(
            catalog_code="D11",
            amount_sp=_D11_PENALTY,
            reason=(
                f"Tarea fantasma: {subtask.lt_biz_hours:.1f}h hábiles sin completar "
                f"(umbral: {_D11_INACTIVE_BIZ_HOURS}h / ~5 días hábiles). "
                f"Penalización: {_D11_PENALTY} SP."
            ),
        )
    return None


# ── D13: Cycle Overflow ───────────────────────────────────────────────────
def detect_d13(
    subtask: Subtask,
    cycle: Cycle | None = None,
) -> DetectedDebuff | None:
    """
    D13 — Cycle Overflow (Tarea No Entregada Al Cierre Del Ciclo).

    Trigger:
      - El ciclo asociado está cerrado (cycle.status in {'closed', 'archived'})
      - La tarea NO está en estado Done/Cancelled

    Penalización: 1.5 SP.

    Args:
        subtask: Modelo Subtask cargado.
        cycle: Modelo Cycle correspondiente (debe pasarse desde el orquestador).
               Si es None, se omite la detección.
    """
    if cycle is None:
        return None
    if cycle.status not in ("closed", "archived"):
        return None

    _terminal = {"Done", "Cancelled", "Cerrado", "Cancelado"}
    if subtask.status in _terminal:
        return None

    return DetectedDebuff(
        catalog_code="D13",
        amount_sp=_D13_PENALTY,
        reason=(
            f"Cycle Overflow: el ciclo '{cycle.name}' cerró con la tarea "
            f"en estado '{subtask.status}' (sin completar). "
            f"Penalización: {_D13_PENALTY} SP."
        ),
    )


# ── Punto de entrada unificado ─────────────────────────────────────────────


def detect_all(
    subtask: Subtask,
    cycle: Cycle | None = None,
    # sprint kept for backwards-compat but ignored (WP-01b migration)
    sprint: object | None = None,
) -> list[DetectedDebuff]:
    """
    Ejecutar todos los detectores automáticos y retornar la lista de debuffs.

    Args:
        subtask: Modelo Subtask con todos sus campos calculados y al día.
        cycle: Modelo Cycle (necesario para D13). Puede ser None.

    Returns:
        Lista de DetectedDebuff (vacía si ninguno aplica).
        Nunca lanza excepciones; un detector que falla por dato ausente
        simplemente retorna None (ignorado).
    """
    results: list[DetectedDebuff] = []

    detectors = [
        lambda: detect_d01(subtask),
        lambda: detect_d03(subtask),
        lambda: detect_d04(subtask),
        lambda: detect_d10(subtask),
        lambda: detect_d11(subtask),
        lambda: detect_d13(subtask, cycle),
    ]

    for detector in detectors:
        try:
            result = detector()
            if result is not None:
                results.append(result)
        except Exception:
            # Nunca propagar errores del detector; el engine debe ser robusto
            pass

    return results
