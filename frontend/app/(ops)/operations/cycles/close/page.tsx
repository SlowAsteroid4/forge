export const dynamic = "force-dynamic";

import { api } from "@/lib/api";
import type {
  CycleCloseSummary,
  CycleCandidate,
  PlayerOption,
} from "@/lib/types/cycle-close";
import type { DashboardResponse } from "@/lib/types/dashboard";
import { Badge } from "@/components/ui/badge";
import { CycleCloseClient } from "@/components/ops/cycles/cycle-close-client";

async function getActiveCycleId(): Promise<number | null> {
  const data = await api
    .get<DashboardResponse>("/dashboard/cycle")
    .catch(() => null);
  return data?.cycle?.id ?? null;
}

async function getCloseSummary(cycleId: number): Promise<CycleCloseSummary> {
  return api.get<CycleCloseSummary>(`/admin/cycles/${cycleId}/close-summary`);
}

async function getMvpCandidates(cycleId: number): Promise<CycleCandidate[]> {
  return api
    .get<CycleCandidate[]>(`/admin/cycles/${cycleId}/mvp-candidates`)
    .catch(() => []);
}

async function getAllPlayers(): Promise<PlayerOption[]> {
  return api.get<PlayerOption[]>("/admin/players").catch(() => []);
}

export default async function CycleClosePage() {
  const cycleId = await getActiveCycleId();

  if (!cycleId) {
    return (
      <div className="flex flex-col flex-1 overflow-auto">
        <div className="flex-1 p-6">
          <div className="rounded-lg border border-dashed border-border p-8 text-center">
            <p className="text-sm text-muted-foreground">
              No hay un ciclo activo en este momento.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const [summary, candidates, allPlayers] = await Promise.all([
    getCloseSummary(cycleId),
    getMvpCandidates(cycleId),
    getAllPlayers(),
  ]);

  return (
    <div className="flex flex-col flex-1 overflow-auto">
      <div className="flex-1 p-6 space-y-6 max-w-4xl">
        {/* ── Header ──────────────────────────────────────────────────── */}
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold">
                Cerrar {summary.cycle_name}
              </h1>
              <Badge variant="secondary" className="capitalize">
                {summary.cycle_status}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              Revisa el resumen del ciclo, elige el MVP y confirma el cierre.
            </p>
          </div>
        </div>

        {/* ── Blocking errors ──────────────────────────────────────────── */}
        {summary.blocking_errors.length > 0 && (
          <div className="rounded-md border border-destructive/50 bg-destructive/5 p-4 space-y-1">
            <p className="text-xs font-semibold text-destructive uppercase tracking-wide">
              Errores bloqueantes
            </p>
            <ul className="space-y-1">
              {summary.blocking_errors.map((err, i) => (
                <li key={i} className="text-sm text-destructive flex gap-2">
                  <span>•</span>
                  <span>{err}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* ── Warnings ─────────────────────────────────────────────────── */}
        {summary.warnings.length > 0 && (
          <div className="rounded-md border border-yellow-500/30 bg-yellow-500/5 p-4 space-y-1">
            <p className="text-xs font-semibold text-yellow-600 uppercase tracking-wide">
              Advertencias
            </p>
            <ul className="space-y-1">
              {summary.warnings.map((w, i) => (
                <li key={i} className="text-sm text-yellow-700 flex gap-2">
                  <span>•</span>
                  <span>{w}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* ── KPI Cards ────────────────────────────────────────────────── */}
        <section>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-3">
            Resumen del ciclo
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <KPICard label="CP completados" value={summary.kpis.cp_done} />
            <KPICard
              label="SP generados"
              value={summary.kpis.sp_generated.toFixed(1)}
            />
            <KPICard label="Subtasks Done" value={summary.kpis.subtasks_done} />
            <KPICard label="Bugs derivados" value={summary.kpis.bugs_derived} />
          </div>
        </section>

        {/* ── Top players por área ──────────────────────────────────────── */}
        {summary.top_players.length > 0 && (
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-3">
              Top players del ciclo
            </h2>
            <div className="rounded-md border border-border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/30">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">
                      #
                    </th>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">
                      Player
                    </th>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">
                      Área
                    </th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">
                      SP
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {summary.top_players.map((p, i) => (
                    <tr key={p.player_id}>
                      <td className="px-4 py-2 text-muted-foreground tabular-nums">
                        {i + 1}
                      </td>
                      <td className="px-4 py-2 font-medium">{p.display_name}</td>
                      <td className="px-4 py-2">
                        <Badge variant="outline" className="text-xs">
                          {p.area}
                        </Badge>
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums font-mono text-sm">
                        {p.sp.toFixed(1)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* ── Formulario de cierre (Client Component) ──────────────────── */}
        <CycleCloseClient
          cycleId={cycleId}
          cycleName={summary.cycle_name}
          candidates={candidates}
          allPlayers={allPlayers}
          canClose={summary.can_close}
        />
      </div>
    </div>
  );
}

function KPICard({
  label,
  value,
}: {
  label: string;
  value: number | string;
}) {
  return (
    <div className="rounded-lg border border-border p-4 space-y-1">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-2xl font-bold tabular-nums">{value}</p>
    </div>
  );
}
