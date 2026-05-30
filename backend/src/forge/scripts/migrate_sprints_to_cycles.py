"""Script de migración: sprints → cycles (WP-01a, idempotente)."""

import sys
from datetime import date, datetime, timedelta

from sqlalchemy import select, update

sys.path.insert(0, "src")

from forge.db.session import SessionLocal
from forge.db.models.sprint import Sprint
from forge.db.models.cycle import Cycle
from forge.db.models.subtask import Subtask
from forge.db.models.leaderboard_snapshot import LeaderboardSnapshot

TODAY = date.today()
ARCHIVED_THRESHOLD_DAYS = 7


def sprint_to_cycle_status(start_date: date, end_date: date, is_closed: bool) -> str:
    if start_date > TODAY:
        return "planned"
    if start_date <= TODAY <= end_date:
        return "active"
    # Past sprint
    if is_closed:
        days_since_end = (TODAY - end_date).days
        return "archived" if days_since_end > ARCHIVED_THRESHOLD_DAYS else "closed"
    # Not explicitly closed but past — treat as archived
    return "archived"


def main() -> None:
    session = SessionLocal()
    try:
        sprints = session.execute(select(Sprint).order_by(Sprint.start_date)).scalars().all()
        print(f"Sprints encontrados: {len(sprints)}")

        created_by_status: dict[str, int] = {}
        skipped = 0
        sprint_to_cycle: dict[int, int] = {}

        for sprint in sprints:
            iso = sprint.start_date.isocalendar()
            iso_year, iso_week = iso[0], iso[1]

            # Idempotent: skip if cycle for this iso_year+iso_week already exists
            existing = session.execute(
                select(Cycle).where(Cycle.iso_year == iso_year, Cycle.iso_week == iso_week)
            ).scalar_one_or_none()

            if existing:
                sprint_to_cycle[sprint.id] = existing.id
                skipped += 1
                continue

            status = sprint_to_cycle_status(sprint.start_date, sprint.end_date, sprint.is_closed)
            cycle_end_date = sprint.start_date + timedelta(days=4)  # lunes + 4 = viernes

            now = datetime.utcnow()
            closed_at = None
            archived_at = None
            if status in ("closed", "archived"):
                # Use end_date (friday) at end of business hours as closed_at
                closed_at = datetime.combine(cycle_end_date, datetime.min.time()).replace(hour=18)
            if status == "archived":
                archived_at = closed_at + timedelta(days=7) if closed_at else now

            cycle = Cycle(
                name=sprint.name,  # keep same name (e.g. "Sprint 2026-W22")
                iso_year=iso_year,
                iso_week=iso_week,
                start_date=sprint.start_date,
                end_date=cycle_end_date,
                status=status,
                is_legacy=True,
                closed_at=closed_at,
                archived_at=archived_at,
                created_at=now,
                updated_at=now,
            )
            session.add(cycle)
            session.flush()  # get cycle.id

            sprint_to_cycle[sprint.id] = cycle.id
            created_by_status[status] = created_by_status.get(status, 0) + 1

        session.commit()
        print(f"\nCiclos creados: {sum(created_by_status.values())}")
        for status, count in sorted(created_by_status.items()):
            print(f"  {status}: {count}")
        print(f"Ciclos ya existentes (skipped): {skipped}")

        # ── Backfill cycle_id en subtasks ────────────────────────────────────
        subtask_mapped = 0
        subtask_null = 0
        subtasks = session.execute(select(Subtask)).scalars().all()
        for st in subtasks:
            if st.sprint_id and st.sprint_id in sprint_to_cycle:
                st.cycle_id = sprint_to_cycle[st.sprint_id]
                subtask_mapped += 1
            else:
                subtask_null += 1
        session.commit()
        print(f"\nSubtasks mapeadas a cycle_id: {subtask_mapped}")
        print(f"Subtasks sin cycle_id (sprint_id NULL o sin match): {subtask_null}")

        # ── Backfill cycle_id en leaderboard_snapshots ───────────────────────
        ls_mapped = 0
        ls_null = 0
        snapshots = session.execute(select(LeaderboardSnapshot)).scalars().all()
        for ls in snapshots:
            if ls.sprint_id and ls.sprint_id in sprint_to_cycle:
                ls.cycle_id = sprint_to_cycle[ls.sprint_id]
                ls_mapped += 1
            else:
                ls_null += 1
        session.commit()
        print(f"\nLeaderboard snapshots mapeados: {ls_mapped}")
        print(f"Leaderboard snapshots sin match: {ls_null}")

        # ── Validación final ─────────────────────────────────────────────────
        active_count = session.execute(
            select(Cycle).where(Cycle.status == "active")
        ).scalars().all()
        print(f"\nCiclos activos (debe ser 1): {len(active_count)}")
        if active_count:
            a = active_count[0]
            print(f"  → {a.name} ({a.start_date} – {a.end_date})")

    finally:
        session.close()


if __name__ == "__main__":
    main()
