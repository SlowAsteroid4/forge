"""Diagnóstico forense de QA first-pass para Juan Castillo (player_id=7).

Read-only. No modifica la base de datos.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from forge.db.session import SessionLocal
from forge.db.models import Subtask, Cycle

JUAN_ID = 7

# Passive QA states que indican que la tarea pasó por QA
QA_STATES = {"In QA", "Ready for QA", "Testing", "In Testing"}


def parse_changelog(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return []


def detect_qa_info(changelog: list[dict]) -> tuple[bool, bool, int]:
    """Returns (entered_qa, bounced_back, qa_attempts)."""
    entered_qa = False
    bounced = False
    qa_attempts = 0
    prev_in_qa = False

    for entry in changelog:
        to_status = entry.get("to", "")
        from_status = entry.get("from", "")

        if to_status in QA_STATES:
            entered_qa = True
            qa_attempts += 1
            prev_in_qa = True
        elif prev_in_qa and to_status not in QA_STATES and from_status in QA_STATES:
            # Left QA to a non-Done state → bounced
            if to_status not in {"Done", "Cerrado", "Closed"}:
                bounced = True
            prev_in_qa = False

    return entered_qa, bounced, qa_attempts


def main() -> None:
    session = SessionLocal()
    try:
        subtasks = (
            session.query(Subtask)
            .filter(
                Subtask.assignee_player_id == JUAN_ID,
                Subtask.status == "Done",
            )
            .order_by(Subtask.jira_key)
            .all()
        )

        print(f"\n{'='*80}")
        print("QA FIRST-PASS FORENSE — Juan Castillo (player_id=7)")
        print(f"{'='*80}")
        print(
            f"\n{'jira_key':<12} {'cycle':>6} {'qa_fp_db':>10} {'entered':>8} "
            f"{'bounced':>8} {'attempts':>9} {'derived':>8}"
        )
        print("-" * 70)

        tally = {"True": 0, "False": 0, "None": 0}
        rows_with_qa = []

        for st in subtasks:
            changelog = parse_changelog(st.raw_changelog)
            entered, bounced, attempts = detect_qa_info(changelog)
            db_value = st.qa_first_pass  # what's stored in DB

            if db_value is True:
                tally["True"] += 1
            elif db_value is False:
                tally["False"] += 1
            else:
                tally["None"] += 1

            derived = True if entered and not bounced else (False if bounced else None)

            print(
                f"{st.jira_key:<12} {str(st.cycle_id or ''):>6} {str(db_value):>10} "
                f"{str(entered):>8} {str(bounced):>8} {attempts:>9} {str(derived):>8}"
            )

            if entered:
                rows_with_qa.append(st)

        print(f"\nTally (DB value): True={tally['True']} | False={tally['False']} | None={tally['None']}")
        print(f"Subtasks que tocaron QA (entered=True): {len(rows_with_qa)}")

        # --- Reconcilia por scope ---
        window_ids = (
            session.query(Cycle.id)
            .filter(Cycle.status.in_(["closed", "archived"]))
            .order_by(Cycle.start_date.desc())
            .limit(4)
            .all()
        )
        window_ids = [r[0] for r in window_ids]

        active_id = session.query(Cycle.id).filter(Cycle.status == "active").scalar()

        print(f"\n{'='*50}")
        print("RECONCILIACIÓN POR SCOPE (solo subtasks qa_first_pass IS NOT NULL)")
        print(f"  Window cycle_ids: {window_ids}")
        print(f"  Active cycle_id:  {active_id}")
        print(f"{'='*50}")

        for scope_name, cycle_filter in [
            ("historical", None),
            ("window", window_ids),
            ("cycle", [active_id] if active_id else []),
        ]:
            sts = [
                s for s in subtasks if s.qa_first_pass is not None
            ]
            if cycle_filter is not None:
                sts = [s for s in sts if s.cycle_id in cycle_filter]

            passed = sum(1 for s in sts if s.qa_first_pass is True)
            total = len(sts)
            pct = (passed / total * 100) if total else 0
            print(f"  {scope_name:<12}: {passed}/{total}  ({pct:.1f}%)")

        print()

    finally:
        session.close()


if __name__ == "__main__":
    main()
