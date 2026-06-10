export const dynamic = "force-dynamic";

import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { MonthCloseSummary, MonthCycleInfo } from "@/lib/types/monthly-mvp";
import { MonthCloseClient } from "@/components/ops/months/month-close-client";

interface PageProps {
  params: Promise<{ month: string }>;
}

/** Desplaza un mes "YYYY-MM" en `delta` meses y devuelve "YYYY-MM". */
function shiftMonth(month: string, delta: number): string {
  const [year, mon] = month.split("-").map(Number);
  const d = new Date(year, mon - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function KPICard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-border p-3 space-y-1">
      <p className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">
        {label}
      </p>
      <p className="text-xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}

function CycleStatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    closed: "bg-blue-100 text-blue-700",
    archived: "bg-gray-100 text-gray-600",
    active: "bg-green-100 text-green-700",
    planned: "bg-yellow-100 text-yellow-700",
  };
  return (
    <span className={["text-[10px] font-semibold px-1.5 py-0.5 rounded", map[status] ?? "bg-muted"].join(" ")}>
      {status}
    </span>
  );
}

export default async function MonthClosePage({ params }: PageProps) {
  const { month } = await params;

  let summary: MonthCloseSummary;
  try {
    summary = await api.get<MonthCloseSummary>(`/admin/months/${month}/close-summary`);
  } catch {
    notFound();
  }

  return (
    <div className="flex flex-col flex-1 overflow-auto">
      <div className="flex-1 p-6 space-y-6 max-w-4xl">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold">
                Cierre mensual — {summary.period_label}
              </h1>
              {summary.already_closed && (
                <Badge variant="secondary">Cerrado</Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              Elige el MVP del Mes entre los MVPs semanales del período.
            </p>
          </div>
          {/* Navegación entre meses */}
          <div className="flex items-center gap-1 shrink-0">
            <Link
              href={`/operations/months/${shiftMonth(month, -1)}/close`}
              className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs hover:bg-muted transition-colors"
              aria-label="Mes anterior"
            >
              <ChevronLeft size={14} />
              {shiftMonth(month, -1)}
            </Link>
            <Link
              href={`/operations/months/${shiftMonth(month, 1)}/close`}
              className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs hover:bg-muted transition-colors"
              aria-label="Mes siguiente"
            >
              {shiftMonth(month, 1)}
              <ChevronRight size={14} />
            </Link>
          </div>
        </div>

        {/* Blocking errors */}
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

        {/* Warnings */}
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

        {/* KPI Cards */}
        <section>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-3">
            KPIs del mes
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <KPICard label="CP completados" value={summary.kpis.cp_done} />
            <KPICard label="SP generados" value={summary.kpis.sp_generated.toFixed(1)} />
            <KPICard label="Subtasks Done" value={summary.kpis.subtasks_done} />
            <KPICard label="Ciclos totales" value={summary.kpis.cycles_total} />
            <KPICard
              label="Ciclos cerrados"
              value={`${summary.kpis.cycles_closed_or_archived}/${summary.kpis.cycles_total}`}
            />
          </div>
        </section>

        {/* Ciclos del mes */}
        <section>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-3">
            Ciclos del mes
          </h2>
          <div className="rounded-md border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/30">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">Ciclo</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">Estado</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">MVP semanal</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {summary.cycles.map((c: MonthCycleInfo) => (
                  <tr key={c.cycle_id}>
                    <td className="px-4 py-2 font-medium">{c.name}</td>
                    <td className="px-4 py-2">
                      <CycleStatusBadge status={c.status} />
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">
                      {c.mvp_player_id ? (
                        <span className="text-foreground font-medium">Player {c.mvp_player_id}</span>
                      ) : (
                        <span className="text-xs italic">Sin MVP asignado</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Close form (client) */}
        <MonthCloseClient
          periodLabel={summary.period_label}
          candidates={summary.candidates}
          canClose={summary.can_close}
          alreadyClosed={summary.already_closed}
        />
      </div>
    </div>
  );
}
