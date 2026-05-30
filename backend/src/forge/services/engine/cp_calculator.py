"""
Motor de cálculo de Complexity Points (CP).

Reglas JPDS v2.0:
  XS=1  S=2  M=3  L=5  XL=8  XXL=13(rechazada)

CP es INMUTABLE una vez que cp_approved_at es NOT NULL.
L y XL requieren aprobación explícita de PM/TL antes de que cp_approved_at se asigne.
XXL es rechazada: debe dividirse; si PM la aprueba de todas formas, lleva 13 CP y requiere
aprobación igual que L/XL.
"""

from forge.core.exceptions import CPImmutableError
from forge.db.models.subtask import Subtask

# ── Tabla de tallas ────────────────────────────────────────────────────────
# Fuente: especificación JPDS v2.0.
# Nota: engine_versions.yaml usa una escala {XXS→XXL} diferente (desplazada
# una posición). Esta tabla toma la especificación del documento de diseño.
CP_TABLE: dict[str, int] = {
    "XS": 1,
    "S": 2,
    "M": 3,
    "L": 5,
    "XL": 8,
    "XXL": 13,
}

# Tallas que requieren aprobación explícita de PM/TL
APPROVAL_REQUIRED: frozenset[str] = frozenset({"L", "XL", "XXL"})

# Tallas consideradas "rechazadas" (deben dividirse en sub-tareas menores)
REJECTED_SIZES: frozenset[str] = frozenset({"XXL"})

# CP mínimo cuando no hay talla definida (safe default)
_CP_DEFAULT: int = 0


def calculate_cp(complexity_size: str | None) -> int:
    """
    Obtener el valor CP para una talla dada.

    Args:
        complexity_size: Talla de la sub-task (XS, S, M, L, XL, XXL).
                         None → devuelve 0 (tarea sin talla asignada).

    Returns:
        Entero CP según la tabla JPDS v2.0.

    Raises:
        ValueError: Si la talla no pertenece al catálogo.
    """
    if complexity_size is None:
        return _CP_DEFAULT

    size = complexity_size.strip().upper()
    if size not in CP_TABLE:
        valid = ", ".join(sorted(CP_TABLE))
        raise ValueError(
            f"Talla '{complexity_size}' no reconocida. Valores válidos: {valid}"
        )
    return CP_TABLE[size]


def needs_approval(complexity_size: str | None) -> bool:
    """
    Indica si esta talla requiere aprobación explícita de PM/TL.

    L, XL y XXL requieren que el PM/TL llame al endpoint de aprobación
    antes de que el CP se selle (cp_approved_at IS NOT NULL).

    Args:
        complexity_size: Talla de la sub-task. None → False.

    Returns:
        True si se requiere aprobación, False en caso contrario.
    """
    if complexity_size is None:
        return False
    return complexity_size.strip().upper() in APPROVAL_REQUIRED


def is_rejected_size(complexity_size: str | None) -> bool:
    """
    Indica si la talla está en la lista de rechazadas (debe dividirse).

    Args:
        complexity_size: Talla de la sub-task. None → False.

    Returns:
        True si la talla es XXL (rechazada).
    """
    if complexity_size is None:
        return False
    return complexity_size.strip().upper() in REJECTED_SIZES


def validate_immutability(subtask: Subtask) -> None:
    """
    Garantiza que el CP de la subtask NO se modifique si ya fue aprobado.

    Debe llamarse ANTES de cualquier write a subtask.cp o subtask.complexity_size.

    Args:
        subtask: Instancia del modelo Subtask cargada desde DB.

    Raises:
        CPImmutableError: Si cp_approved_at IS NOT NULL (CP ya sellado).
    """
    if subtask.cp_approved_at is not None:
        raise CPImmutableError(subtask.jira_key)


def assign_cp(subtask: Subtask, complexity_size: str) -> None:
    """
    Asigna complexity_size y cp a una subtask, respetando la inmutabilidad.

    Args:
        subtask: Instancia del modelo (debe estar en una sesión activa).
        complexity_size: Nueva talla a asignar.

    Raises:
        CPImmutableError: Si la subtask ya tiene CP aprobado.
        ValueError: Si la talla no es reconocida.
    """
    validate_immutability(subtask)
    subtask.complexity_size = complexity_size.strip().upper()
    subtask.cp = calculate_cp(subtask.complexity_size)
    subtask.cp_approval_required = needs_approval(subtask.complexity_size)
