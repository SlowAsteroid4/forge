import { api } from "@/lib/api";
import type { DashboardResponse } from "@/lib/types/dashboard";
import { OpsHeader } from "@/components/ops/header";
import { KpiCard } from "@/components/ops/kpi-card";
import { AreaProgressGrid } from "@/components/ops/area-progress";
import { DevTable } from "@/components/ops/dev-table";
import { AlertsPanel } from "@/components/ops/alerts-panel";
import { Progress } from "@/components/ui/progress";

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
                    {new Date(cycle.start_date).toLocaleDateString("es-MX", {
                      day: "numeric",
                      month: "short",
                    })}{" "}
                    —{" "}
                    {new Date(cycle.end_date).toLocaleDateString("es-MX", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    })}
                  </p>
                </div>
                <span className="text-sm text-muted-foreground tabular-nums">
                  {cycle.days_elapsed} de {cycle.days_total} días
                </span>
              </div>
              <Progress value={cycle.progress_pct} className="h-2" />
            </div>

            {/* KPI cards */}
            <div className="grid grid-cols-4 gap-3">
              <KpiCard title="CP Done" value={dashboard.kpis.cp_done} />
              <KpiCard title="CP Pendientes" value={dashboard.kpis.cp_pending} />
              <KpiCard title="SP Totales" value={dashboard.kpis.sp_total} decimals={1} />
              <KpiCard title="Bugs Derivados" value={dashboard.kpis.bugs_derived} invertDelta />
            </div>

            {/* Area progress */}
            <section>
              <h3 className="text-sm font-semibold mb-3">Progreso por área</h3>
              {dashboard.area_progress.length > 0 ? (
                <AreaProgressGrid areas={dashboard.area_progress} />
              ) : (
                <p className="text-sm text-muted-foreground">Sin datos de área en este ciclo.</p>
              )}
            </section>

            {/* Active devs */}
            <section>
              <h3 className="text-sm font-semibold mb-3">
                Devs activos{" "}
                <span className="text-muted-foreground font-normal">
                  ({dashboard.player_status.length})
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
