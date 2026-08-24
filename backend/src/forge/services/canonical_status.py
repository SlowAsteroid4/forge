"""Mapeo canónico de estados — Manifiesto JPDS (Documento 03.1 Ritmo Operativo).

⚠️ CAPA DE DISPLAY, NO DE ATRIBUCIÓN.
Los 9 estados CANÓNICOS del Manifiesto JPDS se usan SOLO para AGRUPAR y MOSTRAR el flujo
(barras por estado, secciones de Quality/Design). NO cambian la atribución de tiempo
(dev vs Edgar) de WP-07h: esa vive en los buckets `*_biz_hours` del modelo Subtask y
permanece intacta.

Constante ÚNICA y reutilizable: `CANONICAL_STATUS_MAP`. Cualquier consumidor que necesite
agrupar estados crudos de Jira debe usar `canonical_of()`.
"""

from __future__ import annotations

# ──────────────────────────────────────────────────────────────────────
# Los 9 estados canónicos (Manifiesto JPDS — orden de flujo)
# ──────────────────────────────────────────────────────────────────────
CANONICAL_ORDER: tuple[str, ...] = (
    "Backlog",
    "Ready",
    "In Progress",
    "In Review",
    "In QA",
    "Waiting",
    "Blocked",
    "Done",
    "Cancelled",
)

# Paleta canónica del Manifiesto JPDS (hex). 'Cancelled' no la define el doc → neutro tenue.
CANONICAL_COLORS: dict[str, str] = {
    "Backlog": "#60A5FA",      # azul
    "Ready": "#CBD5E1",        # gris claro
    "In Progress": "#FDE68A",  # ámbar tenue
    "In Review": "#DDD6FE",    # violeta tenue
    "In QA": "#99F6E4",        # teal tenue
    "Waiting": "#C7D2FE",      # índigo tenue
    "Blocked": "#FCA5A5",      # rojo
    "Done": "#4ADE80",         # verde
    "Cancelled": "#94A3B8",    # slate (no en doc; neutro para terminal cancelado)
}

# ──────────────────────────────────────────────────────────────────────
# Mapeo crudo → canónico.
# Claves normalizadas en minúsculas (case-insensitive). Cubre los 37 estados
# crudos hallados en raw_changelog + los listados en el Manifiesto que aún no
# aparecen en datos (UI, Validation, Live (Campaign)). Incluye variantes en
# español de la instancia Jira (YAP).
# Cualquier crudo NO listado cae al fallback (ver canonical_of) → "In Progress",
# que es el bucket de trabajo activo, y se considera reportable.
# ──────────────────────────────────────────────────────────────────────
CANONICAL_STATUS_MAP: dict[str, str] = {
    # Backlog (sin iniciar / refinamiento / triage)
    "backlog": "Backlog",
    "to do": "Backlog",
    "open": "Backlog",
    "new": "Backlog",
    "nuevo": "Backlog",
    "nueva": "Backlog",
    "triaged": "Backlog",
    "refinement": "Backlog",
    # Ready (listo para tomar / listo para QA en sentido de cola previa)
    "ready": "Ready",
    "ready for qa": "Ready",
    "ready for dev": "Ready",
    # In Progress (manos del dev / diseño activo)
    "in progress": "In Progress",
    "en progreso": "In Progress",
    "ui": "In Progress",
    "ui implementation": "In Progress",
    "service integration": "In Progress",
    "prototyping": "In Progress",
    "in design": "In Progress",
    "active": "In Progress",
    "implementation": "In Progress",
    "in code": "In Progress",
    "in development": "In Progress",
    "edición": "In Progress",
    "edicion": "In Progress",
    # In Review (revisión de código / validación / testing por pares)
    "in review": "In Review",
    "en revisión": "In Review",
    "en revision": "In Review",
    "in code review": "In Review",
    "validation": "In Review",
    "testing": "In Review",
    "audit": "In Review",
    # In QA (cola de QA dedicada — Edgar)
    "in qa": "In QA",
    # Waiting (en espera / pre-release / staging)
    "waiting": "Waiting",
    "en espera": "Waiting",
    "ready for release": "Waiting",
    "staging": "Waiting",
    # Blocked
    "blocked": "Blocked",
    "bloqueado": "Blocked",
    # Done (entregado / cerrado / campaña en vivo)
    "done": "Done",
    "cerrado": "Done",
    "closed": "Done",
    "live (campaign)": "Done",
    # Cancelled
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
}

# Crudos que indican "en el pipeline de QA ahora" (para 'por probar').
# NOTA: 'Ready for QA' canónicamente cae en 'Ready', pero para la métrica de
# Quality "por probar" cuenta como cola de QA pendiente (igual que 'In QA').
QA_PENDING_RAW: frozenset[str] = frozenset({"in qa", "ready for qa"})

_FALLBACK = "In Progress"


def canonical_of(raw_status: str | None) -> str:
    """Devuelve el estado canónico para un estado crudo de Jira.

    Case-insensitive. Si el crudo no está mapeado, cae a 'In Progress' (trabajo
    activo) — situación reportable que no debería ocurrir con el set actual.
    """
    if not raw_status:
        return _FALLBACK
    return CANONICAL_STATUS_MAP.get(raw_status.strip().lower(), _FALLBACK)


def is_qa_pending(raw_status: str | None) -> bool:
    """True si el estado crudo es cola de QA pendiente ('In QA' / 'Ready for QA')."""
    if not raw_status:
        return False
    return raw_status.strip().lower() in QA_PENDING_RAW


# Mapeo bucket WP-07h → estado canónico (capa de display de las barras).
# Las horas son las de WP-07h sin tocar; solo se RE-ETIQUETAN a canónico.
# ready_for_qa ya está contenido en dev_resp (WP-07h) → no se suma aparte.
BUCKET_TO_CANONICAL: dict[str, str] = {
    "dev_resp_h": "In Progress",
    "review_h": "In Review",
    "qa_h": "In QA",
    "blocked_h": "Blocked",
    "waiting_h": "Waiting",
}
