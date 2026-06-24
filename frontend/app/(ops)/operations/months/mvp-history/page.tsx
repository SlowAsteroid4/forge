export const dynamic = "force-dynamic";

import Link from "next/link";
import { api } from "@/lib/api";
import type { MonthlyMvpHistoryItem } from "@/lib/types/monthly-mvp";
import { Badge } from "@/components/ui/badge";

interface PageProps {
  searchParams: Promise<{ year?: string; player_id?: string }>;
}

async function getMonthlyMvpHistory(
  year?: string,
  playerId?: string,
): Promise<MonthlyMvpHistoryItem[]> {
  const params = new URLSearchParams();
  if (year) params.set("year", year);
  if (playerId) params.set("player_id", playerId);
  const q = params.toString() ? `?${params}` : "";
  return api.get<MonthlyMvpHistoryItem[]>(`/admin/months/mvp-history${q}`).catch(() => []);
}

function isWithin72BusinessHours(assignedAt: string): boolean {
  const assigned = new Date(assignedAt);
  const now = new Date();
  const diffHours = (now.getTime() - assigned.getTime()) / (1000 * 60 * 60);
  // Rough approximation (72 biz hours ≈ 9 calendar days). Backend enforces exact.
  return diffHours <= 216;
}

const AREA_COLORS: Record<string, string> = {
  BE: "bg-blue-100 text-blue-700",
  FE: "bg-purple-100 text-purple-700",
  QA: "bg-green-100 text-green-700",
  PM: "bg-orange-100 text-orange-700",
};

export default async function MonthlyMvpHistoryPage({ searchParams }: PageProps) {
  const { year, player_id } = await searchParams;
  const history = await getMonthlyMvpHistory(year, player_id);

  const years = Array.from(new Set(history.map((h) => h.year))).sort((a, b) => b - a);

  return (
    <div className="flex flex-col flex-1 overflow-auto">
      <div className="flex-1 p-6 space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-lg font-semibold">Historial MVP del Mes</h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              {history.length} mes{history.length !== 1 ? "es" : ""} con MVP del Mes asignado
            </p>
          </div>
          <Link
            href="/operations/months/2026-05/close"
            className="text-xs text-muted-foreground hover:text-foreground underline underline-offset-2 transition-colors"
          >
            Cerrar mes actual →
          </Link>
        </div>

        {/* Filters */}
        {years.length > 1 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Año:</span>
            <Link
              href="/operations/months/mvp-history"
              className={[
                "text-xs px-2 py-1 rounded transition-colors",
                !year ? "bg-accent text-foreground font-medium" : "text-muted-foreground hover:text-foreground",
              ].join(" ")}
            >
              Todos
            </Link>
            {years.map((y) => (
              <Link
                key={y}
                href={`/operations/months/mvp-history?year=${y}`}
                className={[
                  "text-xs px-2 py-1 rounded transition-colors",
                  year === String(y) ? "bg-accent text-foreground font-medium" : "text-muted-foreground hover:text-foreground",
                ].join(" ")}
              >
                {y}
              </Link>
            ))}
          </div>
        )}

        {history.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-8 text-center">
            <p className="text-sm text-muted-foreground">
              Aún no hay cierres mensuales registrados.
            </p>
            <Link
              href="/operations/months/2026-05/close"
              className="mt-3 inline-block text-xs text-primary underline"
            >
              Ir a cerrar el mes
            </Link>
          </div>
        ) : (
          <div className="rounded-md border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/30">
                <tr>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Mes</th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">MVP del Mes</th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Área</th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">+SP</th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Razón</th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Asignado</th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Ciclos</th>
                  <th className="px-4 py-2.5 text-right font-medium text-muted-foreground">Editar</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {history.map((item) => {
                  const canEdit = isWithin72BusinessHours(item.assigned_at);
                  return (
                    <tr key={item.id}>
                      <td className="px-4 py-3 font-semibold tabular-nums">{item.period_label}</td>
                      <td className="px-4 py-3 font-medium">{item.display_name}</td>
                      <td className="px-4 py-3">
                        {item.area ? (
                          <span
                            className={[
                              "inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold",
                              AREA_COLORS[item.area] ?? "bg-muted text-muted-foreground",
                            ].join(" ")}
                          >
                            {item.area}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant="secondary" className="font-semibold">
                          +{item.sp_reward} SP
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground text-xs max-w-xs">
                        <span className="line-clamp-2">{item.reason ?? "—"}</span>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground text-xs tabular-nums whitespace-nowrap">
                        {new Date(item.assigned_at).toLocaleDateString("es-MX", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                        <br />
                        <span className="text-[10px]">por {item.assigned_by_name}</span>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {item.source_cycle_ids.length > 0
                          ? `${item.source_cycle_ids.length} ciclos`
                          : "—"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {canEdit ? (
                          <Link
                            href={`/operations/months/${item.period_label}/close`}
                            className="text-xs text-primary hover:underline"
                          >
                            Editar
                          </Link>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
