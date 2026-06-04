"""Recomputa qa_first_pass sobre raw_changelog existente sin re-fetch de Jira."""

import json
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from forge.db.models import Subtask
from forge.db.session import SessionLocal
from forge.etl.quality_metrics import compute_qa_first_pass_from_raw


def recompute(session: Session, *, dry_run: bool = False) -> Counter[str]:
    """
    Recorre todas las subtasks con raw_changelog y recalcula qa_first_pass.

    Args:
        session: SQLAlchemy session
        dry_run: Si True, muestra cambios sin persistirlos

    Returns:
        Counter con distribución resultante {True/False/None → count}
    """
    rows = session.scalars(
        select(Subtask).where(
            Subtask.raw_changelog.is_not(None),
        )
    ).all()

    dist: Counter[str] = Counter()
    updated = 0

    for subtask in rows:
        if not subtask.raw_changelog:
            continue

        raw: dict[str, object] = (
            subtask.raw_changelog
            if isinstance(subtask.raw_changelog, dict)
            else json.loads(subtask.raw_changelog)
        )

        new_qa_first_pass, new_qa_attempts = compute_qa_first_pass_from_raw(raw)
        key = str(new_qa_first_pass)
        dist[key] += 1

        if (
            subtask.qa_first_pass != new_qa_first_pass
            or subtask.qa_attempts != new_qa_attempts
        ):
            if not dry_run:
                subtask.qa_first_pass = new_qa_first_pass
                subtask.qa_attempts = new_qa_attempts
            updated += 1

    if not dry_run:
        session.commit()

    print(f"\nRecompute {'(DRY RUN) ' if dry_run else ''}completado:")
    print(f"  Subtasks procesadas: {len(rows)}")
    print(f"  Actualizadas: {updated}")
    print("\nDistribución qa_first_pass:")
    for val in ("True", "False", "None"):
        print(f"  {val:5s}: {dist[val]}")
    return dist


def main() -> None:
    with SessionLocal() as session:
        recompute(session)


if __name__ == "__main__":
    main()
