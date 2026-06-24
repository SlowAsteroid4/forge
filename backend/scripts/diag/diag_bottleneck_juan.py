"""Diagnóstico de cuello de botella promedio por estado para Juan Castillo.

Calcula promedio de horas por estado Jira sobre sus subtasks Done,
reusando la lógica de raw_changelog del servicio de time-in-status-detail.

Read-only. No modifica la base de datos.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from forge.db.models import Subtask
from forge.db.session import SessionLocal

JUAN_ID = 7


def parse_time_by_status(raw_changelog: str | None) -> dict[str, float]:
    """Extrae horas por estado Jira desde raw_changelog.

    raw_changelog es una lista de entries con fields:
      from, to, from_ts (ISO), to_ts (ISO)  (o similar según ETL)
    """
    if not raw_changelog:
        return {}
    try:
        entries = json.loads(raw_changelog)
    except Exception:
        return {}

    hours_by_status: dict[str, float] = defaultdict(float)

    for entry in entries:
        status = entry.get("from") or entry.get("status") or entry.get("to", "")
        duration_h = entry.get("duration_h") or entry.get("hours") or 0.0

        # Some changelogs store minutes instead of hours
        duration_min = entry.get("duration_minutes") or entry.get("minutes") or 0.0
        if duration_h == 0.0 and duration_min > 0:
            duration_h = duration_min / 60.0

        if status and duration_h > 0:
            hours_by_status[status] += float(duration_h)

    return dict(hours_by_status)


def main() -> None:
    session = SessionLocal()
    try:
        subtasks = (
            session.query(Subtask)
            .filter(
                Subtask.assignee_player_id == JUAN_ID,
                Subtask.status == "Done",
            )
            .all()
        )

        print(f"\n{'='*70}")
        print("CUELLO DE BOTELLA PROMEDIO — Juan Castillo (player_id=7)")
        print(f"Total subtasks Done analizadas: {len(subtasks)}")
        print(f"{'='*70}")

        # Check raw_changelog structure of first subtask with data
        sample = next((s for s in subtasks if s.raw_changelog), None)
        if sample:
            try:
                sample_data = json.loads(sample.raw_changelog or "[]")
                print(f"\nEstructura de raw_changelog (keys de primer entry de {sample.jira_key}):")
                if sample_data:
                    print(f"  {list(sample_data[0].keys())}")
                else:
                    print("  (vacío)")
            except Exception as e:
                print(f"  Error parseando: {e}")

        # Use DB columns (pre-computed bucket hours) if raw_changelog doesn't have duration
        print("\n--- Usando columnas pre-computadas (dev_resp_biz_hours, qa_biz_hours, etc.) ---")
        bucket_totals = {
            "Dev (dev_resp)": 0.0,
            "QA (qa)": 0.0,
            "Review (review)": 0.0,
            "Blocked (blocked)": 0.0,
            "Waiting (waiting)": 0.0,
        }
        with_hours = 0
        for s in subtasks:
            dh = float(s.dev_resp_biz_hours or 0)
            qh = float(s.qa_biz_hours or 0)
            rh = float(s.review_biz_hours or 0)
            bh = float(s.blocked_biz_hours or 0)
            wh = float(s.waiting_biz_hours or 0)
            if dh + qh + rh + bh + wh > 0:
                with_hours += 1
            bucket_totals["Dev (dev_resp)"] += dh
            bucket_totals["QA (qa)"] += qh
            bucket_totals["Review (review)"] += rh
            bucket_totals["Blocked (blocked)"] += bh
            bucket_totals["Waiting (waiting)"] += wh

        n = len(subtasks)
        print(f"\n{'Bucket':<25} {'Total h':>10} {'Promedio h':>12} {'(sobre {n} Done)'}")
        print("-" * 60)
        ranked = sorted(bucket_totals.items(), key=lambda x: -x[1])
        for bucket, total in ranked:
            avg = total / n if n else 0
            print(f"{bucket:<25} {total:>10.1f} {avg:>12.2f}")

        print(f"\nSubtasks con al menos 1h en algún bucket: {with_hours}/{n}")

        # Also try raw_changelog parsing
        print("\n--- Intentando parsear raw_changelog para estados Jira específicos ---")
        all_status_hours: dict[str, float] = defaultdict(float)
        count_with_parsed = 0
        for s in subtasks:
            parsed = parse_time_by_status(s.raw_changelog)
            if parsed:
                count_with_parsed += 1
                for st, h in parsed.items():
                    all_status_hours[st] += h

        if all_status_hours:
            print(f"Subtasks con raw_changelog parseable: {count_with_parsed}/{n}")
            print("\nTop-10 estados por horas totales (Juan, todas sus Done):")
            top = sorted(all_status_hours.items(), key=lambda x: -x[1])[:10]
            for status, total in top:
                avg = total / n
                print(f"  {status:<30} total={total:>8.1f}h  prom={avg:>6.2f}h/tarea")
        else:
            print("No se pudo extraer duración desde raw_changelog (formato no tiene 'duration_h').")
            print("Los datos de tiempo por estado Jira específico requieren el parseo del ETL.")

        print()

    finally:
        session.close()


if __name__ == "__main__":
    main()
