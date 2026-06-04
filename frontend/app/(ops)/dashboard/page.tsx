import Link from "next/link";
import { api } from "@/lib/api";
import type { DashboardResponse } from "@/lib/types/dashboard";
import { OpsHeader } from "@/components/ops/header";
import { KpiCard } from "@/components/ops/kpi-card";
import { AreaProgressGrid } from "@/components/ops/area-progress";
import { DevTable } from "@/components/ops/dev-table";
import { AlertsPanel } from "@/components/ops/alerts-panel";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";

/**
 * Parsea un string "YYYY-MM-DD" como fecha LOCAL (no UTC).
 * new Date("2026-06-01") se interpreta como UTC medianoche → en CDMX (UTC-6)
 * aparece como 31 may. Al pasar "2026-06-01T00:00:00" sin Z se usa hora local.
 */
function localDate(dateStr: string): Date {
  return new Date(`${dateStr}T00:00:00`);
}

interface PageProps {
  searchParams: Promise<{ project?: string; cycle_id?: string }>;
}

async function getDashboard(projectCode?: string, cycleId?: string): Promise<DashboardResponse | null> {
  const params = new URLSearchParams();
  if (projectCode) params.set("project_code", projectCode);
  if (cycleId) params.set("cycle_id", cycleId);
  const query = params.toString() ? `?${params}` : "";
  return api.get<DashboardResponse>(`/dashboard/cycle${query}`).catch(() => null);
}

export default async function DashboardPage({ searchParams }: PageProps) {
  const { project, cycle_id } = await searchParams;
  const dashboard = await getDashboard(project, cycle_id);

  const cycle = dashboard?.cycle ?? null;
  const noData = !dashboard || !cycle;

  return (
    <div className="flex flex-col flex-1 overflow-auto">
      <OpsHeader
        projects={dashboard?.available_projects ?? []}
        lastSyncAt={dashboard?.last_synced_at ?? null}
      />

      <div className="flex-1 p-6 space-y-6">
        {noData ? (
          <div className="rounded-lg border border-dashed border-border p-8 text-center">
            <p className="text-sm text-muted-foreground">
              {dashboard?.no_cycle_message ?? "No hay ciclo activo. Crea uno para comenzar."}
            </p>
          </div>
        ) : (
          <>
            {/* Ciclo banner */}
            <div className="rounded-lg border border-border bg-card p-4 space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold">{cycle.name}</h2>
                  <p className="text-xs text-muted-foreground">
                    {localDate(cycle.start_date).toLocaleDateString("es-MX", {
                      day: "numeric",
                      month: "short",
                    })}{" "}
                    —{" "}
                    {localDate(cycle.end_date).toLocaleDateString("es-MX", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    })}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {cycle.progress_pct >= 100 && (
                    <Link
                      href="/operations/cycles/close"
                      className="text-xs font-medium text-primary hover:underline flex items-center gap-1"
                    >
                      Este ciclo está listo para cerrar →
                    </Link>
                  )}
                  <span className="text-sm text-muted-foreground tabular-nums">
                    Día {cycle.days_elapsed} de {cycle.days_total} (ciclo)
                  </span>
                </div>
              </div>
              <Progress value={cycle.progress_pct} className="h-2" />
            </div>

            {/* KPI cards */}
            <div className="grid grid-cols-2 gap-3">
              <KpiCard title="CP completados esta semana" value={dashboard.kpis.cp_done} />
              <div className="rounded-lg border border-border bg-card p-4">
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-1">
                  QA First-pass
                </p>
                <div className="flex items-end gap-2">
                  <span className="text-3xl font-bold tabular-nums">
                    {(dashboard.kpis.qa_first_pass.rate * 100).toFixed(0)}%
                  </span>
                  {dashboard.kpis.qa_first_pass.total > 0 && (
                    <Badge variant="outline" className="mb-1 text-[10px]">
                      {dashboard.kpis.qa_first_pass.passed}/{dashboard.kpis.qa_first_pass.total}
                    </Badge>
                  )}
                </div>
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  Subtasks Done que pasaron QA al primer intento
                </p>
              </div>
            </div>

            {/* Area throughput */}
            <section>
              <h3 className="text-sm font-semibold mb-3">CP completados por área esta semana</h3>
              {dashboard.area_progress.length > 0 ? (
                <AreaProgressGrid areas={dashboard.area_progress} />
              ) : (
                <p className="text-sm text-muted-foreground">Sin datos de área en este ciclo.</p>
              )}
            </section>

            {/* All devs + live WIP */}
            <section>
              <h3 className="text-sm font-semibold mb-3">
                Equipo — WIP actual{" "}
                <span className="text-muted-foreground font-normal">
                  ({dashboard.player_status.length} devs)
                </span>
              </h3>
              <div className="rounded-md border border-border overflow-hidden">
                <DevTable players={dashboard.player_status} />
              </div>
            </section>

            {/* Alerts */}
            <section>
              <h3 className="text-sm font-semibold mb-3">
                Alertas activas{" "}
                {dashboard.alerts.length > 0 && (
                  <span className="text-muted-foreground font-normal">
                    ({dashboard.alerts.length})
                  </span>
                )}
              </h3>
              <AlertsPanel alerts={dashboard.alerts} />
            </section>
          </>
        )}
      </div>
    </div>
  );
}
