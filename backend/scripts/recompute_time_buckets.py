"""Recomputa los buckets de tiempo desde raw_changelog guardado en BD.

No llama a Jira. Idempotente: se puede correr múltiples veces.
Lee el raw_changelog de cada subtask Done, extrae los periodos de estado
con extract_time_metrics, y actualiza los buckets en la BD.

Uso:
    uv run python scripts/recompute_time_buckets.py
    uv run python scripts/recompute_time_buckets.py --dry-run   # solo imprime, no escribe
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forge.db.models.subtask import Subtask
from forge.db.session import SessionLocal
from forge.etl.time_metrics import extract_time_metrics

BUCKET_FIELDS = [
    "done_at",
    "lt_biz_hours",
    "ct_biz_hours",
    "adj_ct_biz_hours",
    "dev_resp_biz_hours",
    "ready_for_qa_biz_hours",
    "qa_biz_hours",
    "blocked_biz_hours",
    "waiting_biz_hours",
    "review_biz_hours",
]


def fake_issue_from_raw_changelog(subtask: Subtask) -> dict:
    """Reconstruye un issue mínimo para extract_time_metrics desde raw_changelog."""
    raw = subtask.raw_changelog
    if not raw:
        return {}
    try:
        changelog_data = json.loads(raw)
    except Exception:
        return {}

    # raw_changelog almacena el payload completo de Jira: {"histories": [...]}
    # extract_time_metrics espera issue["changelog"]["histories"]
    return {
        "changelog": changelog_data,
        "fields": {
            # resolutiondate: usamos done_at ya guardado como fallback si existe
            "resolutiondate": subtask.done_at.isoformat() if subtask.done_at else None,
            "created": None,  # no disponible en raw_changelog — se inferirá del changelog
        },
    }


def main(dry_run: bool = False) -> None:
    session = SessionLocal()
    try:
        subtasks = (
            session.query(Subtask)
            .filter(Subtask.raw_changelog.is_not(None))
            .all()
        )

        print(f"Subtasks con raw_changelog: {len(subtasks)}")
        updated = 0
        skipped_no_created = 0

        for st in subtasks:
            issue = fake_issue_from_raw_changelog(st)
            if not issue:
                continue

            # Necesitamos `created` para lead time y cycle time.
            # Lo extraemos del raw_changelog: buscamos el primer timestamp.
            try:
                histories = issue["changelog"].get("histories", [])
                all_ts = [h.get("created", "") for h in histories if h.get("created")]
                if all_ts:
                    earliest = min(all_ts)
                    issue["fields"]["created"] = earliest
            except Exception:
                pass

            if not issue["fields"].get("created"):
                skipped_no_created += 1
                continue

            metrics = extract_time_metrics(issue)

            if not any(metrics.get(f) is not None for f in BUCKET_FIELDS):
                continue

            changed = False
            for field in BUCKET_FIELDS:
                new_val = metrics.get(field)
                old_val = getattr(st, field, None)
                if new_val != old_val:
                    if not dry_run:
                        setattr(st, field, new_val)
                    changed = True

            if changed:
                updated += 1

        if not dry_run:
            session.commit()

        print(f"{'[DRY RUN] ' if dry_run else ''}Actualizadas: {updated}")
        print(f"Omitidas (sin 'created' en changelog): {skipped_no_created}")

    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
