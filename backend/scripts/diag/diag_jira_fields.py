"""Diagnóstico forense de campos Jira para subtasks de Juan Castillo.

Fetchea el payload crudo de 6 subtasks y determina qué customfield
contiene la talla (XS/S/M/L/XL/XXL). Read-only, no escribe a forge.db.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from forge.etl.jira_client import JiraClient

# Subtasks de Juan (Done, varios tipos)
JUAN_KEYS = ["YAP-518", "YAP-721", "YAP-841", "YAP-700", "YAP-770", "YAP-811"]
TALLA_VALUES = {"XS", "S", "M", "L", "XL", "XXL"}


async def fetch_issue(client: JiraClient, key: str) -> dict:
    try:
        return await client.get_issue(key, expand="changelog,names")
    except Exception as e:
        return {"error": str(e), "key": key}


def scan_talla_fields(fields: dict) -> dict[str, str]:
    """Encuentra todos los customfields con valor de talla (XS/S/M/L/XL/XXL)."""
    hits = {}
    for k, v in fields.items():
        if not k.startswith("customfield_"):
            continue
        # dict with 'value' key (select/radio fields)
        if isinstance(v, dict) and isinstance(v.get("value"), str):
            if v["value"].strip().upper() in TALLA_VALUES:
                hits[k] = v["value"]
        # plain string
        elif isinstance(v, str) and v.strip().upper() in TALLA_VALUES:
            hits[k] = v
        # list of dicts (multi-select)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict) and isinstance(item.get("value"), str):
                    if item["value"].strip().upper() in TALLA_VALUES:
                        hits[k] = item["value"]
    return hits


async def main() -> None:
    client = JiraClient()  # reads settings internally

    print(f"\n{'='*80}")
    print("DIAGNÓSTICO CAMPO DE TALLA — subtasks de Juan Castillo")
    print("ETL lee: customfield_10851 (sync_orchestrator.py:191, jira_client.py:100)")
    print(f"{'='*80}\n")

    all_talla_fields: dict[str, set] = {}  # field_id → set of values seen

    for key in JUAN_KEYS:
        print(f"--- {key} ---")
        issue = await fetch_issue(client, key)

        if "error" in issue:
            print(f"  ERROR: {issue['error']}")
            continue

        fields = issue.get("fields", {})
        itype = fields.get("issuetype", {}).get("name", "?")
        status = fields.get("status", {}).get("name", "?")

        print(f"  issuetype: {itype}")
        print(f"  status:    {status}")

        # Específicos solicitados
        cf_10851 = fields.get("customfield_10851")
        cf_10019 = fields.get("customfield_10019")
        cf_10016 = fields.get("customfield_10016")
        cf_10020 = fields.get("customfield_10020")
        print(f"  customfield_10851 (ETL reads): {cf_10851}")
        print(f"  customfield_10019:             {cf_10019}")
        print(f"  customfield_10016:             {cf_10016}")
        print(f"  customfield_10020:             {cf_10020}")

        # Scan all customfields for talla values
        talla_hits = scan_talla_fields(fields)
        if talla_hits:
            print(f"  CAMPOS CON TALLA: {talla_hits}")
            for fid, val in talla_hits.items():
                if fid not in all_talla_fields:
                    all_talla_fields[fid] = set()
                all_talla_fields[fid].add(val)
        else:
            print("  (ningún customfield tiene valor de talla)")

        # Scan for CP-like numeric values in customfields
        cp_like = {}
        for k, v in fields.items():
            if not k.startswith("customfield_"):
                continue
            if isinstance(v, (int, float)) and 0 < v <= 100:
                cp_like[k] = v
        if cp_like:
            print(f"  Customfields numéricos 0-100 (posibles CP): {cp_like}")

        print()

    # Summary
    print(f"{'='*80}")
    print("RESUMEN: customfields con valores de talla encontrados")
    if all_talla_fields:
        for fid, vals in sorted(all_talla_fields.items()):
            print(f"  {fid}: {sorted(vals)}")
    else:
        print("  Ninguno → la talla NO está en customfields estándar de estas subtasks")

    print("\nVEREDICTO:")
    if "customfield_10851" in all_talla_fields:
        print("  ✅ customfield_10851 SÍ contiene talla → ETL correcto")
    else:
        others = [f for f in all_talla_fields if f != "customfield_10851"]
        if others:
            print(f"  ❌ customfield_10851 vacío. Campo real: {others} → MISMATCH (bug P1)")
        else:
            print("  ⚠️  Ningún customfield tiene talla en estas subtasks")
            print("     Posibles causas: (A) talla no asignada en Jira, (B) campo diferente")


if __name__ == "__main__":
    asyncio.run(main())
