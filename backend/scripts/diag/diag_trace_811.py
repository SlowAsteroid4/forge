"""Traza el pipeline de sync para YAP-811 en memoria, sin escribir a forge.db.

Lee customfield_10851 vía dos rutas:
  (A) get_issue — fetch individual con todos los fields (siempre funciona)
  (B) search_issues — fetch vía JQL con fields restringidos (lo que usa sync_all)
Compara el valor de customfield_10851 en ambas para cazar si el campo
se pierde en la búsqueda antes de llegar al upsert.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from forge.core.config import get_settings
from forge.db.models.subtask import Subtask
from forge.db.session import SessionLocal
from forge.etl.jira_client import JiraClient
from forge.etl.quality_metrics import extract_quality_metrics
from forge.etl.time_metrics import extract_time_metrics
from forge.services.engine.cp_calculator import calculate_cp, needs_approval

KEY = "YAP-811"


async def main() -> None:
    settings = get_settings()
    client = JiraClient()
    session = SessionLocal()

    print(f"\n{'='*70}")
    print(f"TRAZA DE PIPELINE PARA {KEY} — solo lectura, sin writes")
    print(f"{'='*70}")

    # ── Estado actual en BD ──────────────────────────────────────────────────
    existing = session.get(Subtask, KEY)
    print("\n[BD actual]")
    print(f"  complexity_size = {existing.complexity_size!r}")
    print(f"  cp              = {existing.cp!r}")
    print(f"  cp_approved_at  = {existing.cp_approved_at!r}")
    print(f"  last_synced_at  = {existing.last_synced_at!r}")
    print(f"  → guard activo (cp_approved_at IS NOT NULL): {existing.cp_approved_at is not None}")

    # ── (A) get_issue — fetch individual ────────────────────────────────────
    print("\n[A] get_issue (fetch individual, todos los fields)")
    issue_full = await client.get_issue(KEY, expand="changelog")
    f_full = issue_full.get("fields", {})
    cf_full = f_full.get("customfield_10851")
    print(f"  issuetype           = {f_full.get('issuetype', {}).get('name')!r}")
    print(f"  status              = {f_full.get('status', {}).get('name')!r}")
    print(f"  customfield_10851   = {cf_full!r}")
    talla_full = cf_full.get("value", "").strip().upper() if isinstance(cf_full, dict) else None
    cp_full = calculate_cp(talla_full) if talla_full else None
    print(f"  → complexity_size parseada: {talla_full!r}")
    print(f"  → cp calculado:             {cp_full!r}")

    # ── (B) search_issues con JQL — simula lo que hace sync_all ─────────────
    print("\n[B] search_issues via JQL (simula sync_all)")
    jql_default = "project = YAP AND updated >= -14d ORDER BY updated DESC"
    jql_specific = f'issue = "{KEY}"'   # forzamos YAP-811 para el diagnóstico
    print(f"  JQL sync real:      {jql_default!r}")
    print(f"  JQL diagnóstico:    {jql_specific!r}  (fuerza YAP-811 sin filtro de fecha)")

    resp = await client.search_issues(jql=jql_specific, max_results=1, expand="changelog")
    issues = resp.get("issues", [])

    if not issues:
        print("  ⚠️  issue NO retornado en search_issues — ¿excluido por la API?")
        print(f"  Respuesta cruda: {json.dumps(resp)[:300]}")
        session.close()
        return

    issue_search = issues[0]
    f_search = issue_search.get("fields", {})
    cf_search = f_search.get("customfield_10851")
    print(f"\n  customfield_10851 en search_issues = {cf_search!r}")
    talla_search = cf_search.get("value", "").strip().upper() if isinstance(cf_search, dict) else None
    cp_search = calculate_cp(talla_search) if talla_search else None
    print(f"  → complexity_size parseada: {talla_search!r}")
    print(f"  → cp calculado:             {cp_search!r}")

    # ── (C) Construir subtask_data completo (replica _sync_subtask) ──────────
    print("\n[C] subtask_data en MEMORIA justo antes del upsert (usando issue de search)")
    fields = f_search
    time_metrics = extract_time_metrics(issue_search)
    quality_metrics = extract_quality_metrics(issue_search)

    complexity_option = fields.get("customfield_10851")
    complexity_size: str | None = None
    if isinstance(complexity_option, dict):
        raw_value = complexity_option.get("value")
        if raw_value:
            complexity_size = raw_value.strip().upper()

    cp = calculate_cp(complexity_size) if complexity_size else None
    cp_approval_required = needs_approval(complexity_size) if complexity_size else False

    subtask_data = {
        "jira_key": KEY,
        "complexity_size": complexity_size,
        "cp": cp,
        "cp_approval_required": cp_approval_required,
        **time_metrics,
        **quality_metrics,
    }

    print(f"  complexity_size (en memoria) = {subtask_data.get('complexity_size')!r}")
    print(f"  cp (en memoria)              = {subtask_data.get('cp')!r}")

    # Simula el guard de inmutabilidad
    if existing.cp_approved_at is not None:
        popped_cp   = subtask_data.pop("cp", None)
        popped_size = subtask_data.pop("complexity_size", None)
        subtask_data.pop("cp_approval_required", None)
        print("\n  ⚠️  GUARD ACTIVO (cp_approved_at IS NOT NULL)")
        print(f"     → popped complexity_size = {popped_size!r}")
        print(f"     → complexity_size tras pop = {subtask_data.get('complexity_size')!r}")
    else:
        print("\n  Guard inactivo (cp_approved_at IS NULL) — complexity_size permanece en subtask_data")
        print(f"  complexity_size TRAS guard = {subtask_data.get('complexity_size')!r}")

    # ── Comparación final ────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("DIAGNÓSTICO")
    print(f"  get_issue  → complexity_size = {talla_full!r}")
    print(f"  search_issues → complexity_size = {talla_search!r}")
    in_memory = subtask_data.get("complexity_size")
    print(f"  En memoria (pre-write) = {in_memory!r}")
    print(f"  En BD = {existing.complexity_size!r}")

    if talla_full != talla_search:
        print(f"\n  ❌ MISMATCH: get_issue='{talla_full}' vs search_issues='{talla_search}'")
        print("     → El campo se pierde en la búsqueda (campos restringidos del JQL search)")
    elif in_memory is None:
        print("\n  ❌ Se pierde en el MAPEO (parseo en memoria ya da None)")
    elif in_memory is not None and existing.complexity_size is None:
        print(f"\n  ⚠️  En memoria = {in_memory!r} pero BD = NULL")
        print("     → Se pierde en el WRITE o en el COMMIT")
    else:
        print("\n  ✅ Coinciden — problema no detectado en esta ruta")

    session.close()


if __name__ == "__main__":
    asyncio.run(main())
