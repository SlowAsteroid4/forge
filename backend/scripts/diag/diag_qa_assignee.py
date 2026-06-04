"""Diagnóstico: ¿cambia el assignee a Edgar durante In QA?

Parsea raw_changelog de subtasks que tocaron QA, interleando transiciones
de STATUS y de ASSIGNEE en orden cronológico. Read-only.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from forge.db.session import SessionLocal
from forge.db.models import Subtask, Player

JUAN_ID = 7
EDGAR_JIRA_ID = "712020:306bd3d6-6ce2-4e7c-a4ca-265297c06c99"

# Subtasks de Juan que tocaron QA (qa_first_pass IS NOT NULL)
QA_SUBTASKS = ["YAP-721", "YAP-700", "YAP-770"]
QA_STATES = {"In QA", "Ready for QA", "Testing", "In Testing"}


def parse_timeline(raw: str | None) -> list[dict]:
    """Extrae eventos de status y assignee en orden cronológico."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []

    events = []
    histories = data.get("histories", [])
    for h in sorted(histories, key=lambda x: x.get("created", "")):
        ts = h.get("created", "")[:16]
        author = h.get("author", {}).get("displayName", "?")
        for item in h.get("items", []):
            field = item.get("field", "")
            if field == "status":
                events.append({
                    "ts": ts,
                    "type": "STATUS",
                    "from": item.get("fromString", ""),
                    "to": item.get("toString", ""),
                    "author": author,
                })
            elif field == "assignee":
                events.append({
                    "ts": ts,
                    "type": "ASSIGNEE",
                    "from": item.get("fromString", ""),
                    "to": item.get("toString", ""),
                    "from_id": item.get("from", ""),
                    "to_id": item.get("to", ""),
                    "author": author,
                })
    return events


def main() -> None:
    session = SessionLocal()
    try:
        # Fetch player names for display
        players = {p.jira_account_id: p.display_name
                   for p in session.query(Player).all()}

        edgar_name = players.get(EDGAR_JIRA_ID, "Edgar (no encontrado)")

        print(f"\n{'='*80}")
        print(f"ASSIGNEE EN QA — subtasks de Juan Castillo (player_id=7)")
        print(f"Edgar Marroquin ID: {EDGAR_JIRA_ID[:20]}... = {edgar_name}")
        print(f"{'='*80}")

        has_assignee_changes = False
        edgar_in_qa_count = 0
        total_qa_entries = 0
        all_assignee_during_qa: dict[str, int] = {}

        # Also analyze ALL Done subtasks from Juan with QA to get team-wide picture
        all_juan_done = (
            session.query(Subtask)
            .filter(
                Subtask.assignee_player_id == JUAN_ID,
                Subtask.status == "Done",
                Subtask.qa_first_pass.is_not(None),
            )
            .all()
        )

        for st in session.query(Subtask).filter(Subtask.jira_key.in_(QA_SUBTASKS)).all():
            events = parse_timeline(st.raw_changelog)
            print(f"\n{'─'*60}")
            print(f"{st.jira_key} | qa_first_pass={st.qa_first_pass} | qa_attempts={st.qa_attempts}")
            print(f"{'─'*60}")

            if not events:
                print("  (sin eventos en changelog)")
                continue

            current_assignee = "?"
            in_qa_since = None
            qa_assignees = []

            for ev in events:
                if ev["type"] == "ASSIGNEE":
                    has_assignee_changes = True
                    current_assignee = ev["to"]
                    to_id = ev.get("to_id", "")
                    tag = " ← EDGAR" if to_id == EDGAR_JIRA_ID else ""
                    print(f"  {ev['ts']} [ASSIGNEE] {ev['from']!r} → {ev['to']!r}{tag}")
                elif ev["type"] == "STATUS":
                    in_qa = ev["to"] in QA_STATES
                    leaving_qa = ev["from"] in QA_STATES and not in_qa
                    tag = ""
                    if in_qa:
                        tag = " ← ENTRA QA"
                        in_qa_since = ev["ts"]
                        qa_assignees.append(current_assignee)
                        total_qa_entries += 1
                        assignee_key = current_assignee or "?"
                        all_assignee_during_qa[assignee_key] = all_assignee_during_qa.get(assignee_key, 0) + 1
                        if current_assignee == edgar_name or ev.get("to_id") == EDGAR_JIRA_ID:
                            edgar_in_qa_count += 1
                    elif leaving_qa:
                        tag = " ← SALE QA"
                    print(f"  {ev['ts']} [STATUS ] {ev['from']!r} → {ev['to']!r}{tag}")

            print(f"\n  Assignee al entrar a QA: {qa_assignees}")
            is_edgar = any(a == edgar_name for a in qa_assignees)
            print(f"  ¿Es Edgar durante QA? {'SÍ' if is_edgar else 'NO'}")

        # ──────────────────────────────────────────────────────────
        # Summary
        print(f"\n{'='*80}")
        print("RESUMEN")
        print(f"  ¿raw_changelog registra cambios de assignee? {'SÍ' if has_assignee_changes else 'NO — CRÍTICO'}")
        print(f"  Entradas a QA analizadas (3 subtasks): {total_qa_entries}")

        if has_assignee_changes:
            print(f"\n  Assignee durante entradas a QA (3 subtasks de Juan):")
            for name, count in sorted(all_assignee_during_qa.items(), key=lambda x: -x[1]):
                tag = " ← EDGAR" if edgar_name in name else ""
                print(f"    {name!r}: {count} veces{tag}")
        else:
            print("\n  ⚠️  El changelog NO registra cambios de assignee.")
            print("     → Atribución de QA debe hacerse por CONVENCIÓN DE ESTADO,")
            print("       no por assignee. Todo tiempo en 'In QA'/'Ready for QA' = Edgar.")

        # Team-wide: scan all subtasks with QA data
        print(f"\n{'='*80}")
        print("ANÁLISIS EQUIPO — Assignee durante In QA (todas subtasks Done con QA_first_pass)")
        team_qa_assignees: dict[str, int] = {}
        for st in session.query(Subtask).filter(
            Subtask.status == "Done",
            Subtask.qa_first_pass.is_not(None),
        ).limit(50).all():
            events = parse_timeline(st.raw_changelog)
            cur_assignee = "?"
            for ev in events:
                if ev["type"] == "ASSIGNEE":
                    cur_assignee = ev["to"]
                elif ev["type"] == "STATUS" and ev["to"] in QA_STATES:
                    team_qa_assignees[cur_assignee] = team_qa_assignees.get(cur_assignee, 0) + 1

        if team_qa_assignees:
            total = sum(team_qa_assignees.values())
            print(f"  (muestra: 50 subtasks Done con qa_first_pass NOT NULL)")
            for name, count in sorted(team_qa_assignees.items(), key=lambda x: -x[1]):
                pct = count / total * 100
                tag = " ← EDGAR" if edgar_name in name else ""
                print(f"    {name!r}: {count}/{total} ({pct:.0f}%){tag}")
        else:
            print("  No hay datos de assignee en los changelogs (sin ASSIGNEE events).")

    finally:
        session.close()


if __name__ == "__main__":
    main()
