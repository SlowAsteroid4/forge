"""Tests del mapeo canónico de estados (WP-17a) — Manifiesto JPDS."""

from forge.services.canonical_status import (
    BUCKET_TO_CANONICAL,
    CANONICAL_COLORS,
    CANONICAL_ORDER,
    CANONICAL_STATUS_MAP,
    canonical_of,
    is_qa_pending,
)

# Los 37 estados crudos hallados en raw_changelog real (instancia YAP) + los
# listados en el Manifiesto que aún no aparecen en datos. La auditoría WP-17a
# exige que el mapeo cubra TODOS.
REAL_RAW_STATUSES = [
    "In Review", "In Progress", "Ready", "Ready for QA", "In QA", "Done",
    "Backlog", "Prototyping", "In Design", "Service Integration",
    "UI Implementation", "Testing", "In Code Review", "To Do", "Waiting",
    "In Code", "Refinement", "Cerrado", "Blocked", "En progreso", "En revisión",
    "Ready for Release", "Closed", "Ready for dev", "Nuevo", "STAGING", "Active",
    "Staging", "In Development", "Open", "Triaged", "Implementation", "New",
    "Audit", "En espera", "Bloqueado", "Edición", "Cancelled",
    # Manifiesto, aún no en datos
    "UI", "Validation", "Live (Campaign)",
]


def test_every_real_status_maps_to_a_canonical() -> None:
    for raw in REAL_RAW_STATUSES:
        canon = canonical_of(raw)
        assert canon in CANONICAL_ORDER, f"{raw!r} → {canon!r} no es canónico válido"


def test_no_real_status_hits_the_silent_fallback() -> None:
    """Ningún crudo conocido debe caer al fallback (todos explícitos en el mapa)."""
    for raw in REAL_RAW_STATUSES:
        assert raw.strip().lower() in CANONICAL_STATUS_MAP, f"{raw!r} no está en el mapa explícito"


def test_canonical_is_case_insensitive() -> None:
    assert canonical_of("DONE") == "Done"
    assert canonical_of("in qa") == "In QA"
    assert canonical_of("  Blocked  ") == "Blocked"


def test_unmapped_status_falls_back_to_in_progress() -> None:
    assert canonical_of("Quantum Limbo") == "In Progress"
    assert canonical_of(None) == "In Progress"


def test_spanish_variants() -> None:
    assert canonical_of("Bloqueado") == "Blocked"
    assert canonical_of("En espera") == "Waiting"
    assert canonical_of("Cerrado") == "Done"
    assert canonical_of("En revisión") == "In Review"


def test_qa_pending_detection() -> None:
    assert is_qa_pending("In QA")
    assert is_qa_pending("Ready for QA")
    assert not is_qa_pending("In Progress")
    assert not is_qa_pending(None)


def test_all_canonical_have_a_color() -> None:
    for canon in CANONICAL_ORDER:
        assert canon in CANONICAL_COLORS


def test_bucket_to_canonical_targets_are_canonical() -> None:
    for canon in BUCKET_TO_CANONICAL.values():
        assert canon in CANONICAL_ORDER
