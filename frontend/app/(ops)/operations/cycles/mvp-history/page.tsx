import { api } from "@/lib/api";
import type { MvpHistoryItem, PlayerOption } from "@/lib/types/cycle-close";
import { Badge } from "@/components/ui/badge";
import { MvpEditButton } from "@/components/ops/cycles/mvp-edit-button";

interface PageProps {
  searchParams: Promise<{ area?: string; player_id?: string }>;
}

async function getMvpHistory(
  area?: string,
  playerId?: string,
): Promise<MvpHistoryItem[]> {
  const params = new URLSearchParams();
  if (area) params.set("area", area);
  if (playerId) params.set("player_id", playerId);
  const q = params.toString() ? `?${params}` : "";
  return api.get<MvpHistoryItem[]>(`/admin/cycles/mvp-history${q}`).catch(() => []);
}

async function getAllPlayers(): Promise<PlayerOption[]> {
  return api.get<PlayerOption[]>("/admin/players").catch(() => []);
}

function isWithin24BusinessHours(closedAt: string | null): boolean {
  if (!closedAt) return false;
  const closed = new Date(closedAt);
  const now = new Date();
  const diffMs = now.getTime() - closed.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);
  return diffHours <= 24;
}

export default async function MvpHistoryPage({ searchParams }: PageProps) {
  const { area, player_id } = await searchParams;
  const [history, allPlayers] = await Promise.all([
    getMvpHistory(area, player_id),
    getAllPlayers(),
  ]);

  const playerMap = new Map(
    allPlayers.map((p) => [p.id, p.display_name]),
  );

  return (
    <div className="flex flex-col flex-1 overflow-auto">
      <div className="flex-1 p-6 space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-lg font-semibold">Historial de MVPs</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            {history.length} ciclo{history.length !== 1 ? "s" : ""} con MVP asignado
          </p>
        </div>

        {history.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-8 text-center">
            <p className="text-sm text-muted-foreground">
              Aún no hay ciclos cerrados con MVP asignado.
            </p>
          </div>
        ) : (
          <div className="rounded-md border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/30">
                <tr>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">
                    Ciclo
                  </th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">
                    MVP
                  </th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">
                    Área
                  </th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">
                    Razón
                  </th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">
                    Cierre
                  </th>
                  <th className="px-4 py-2.5 text-right font-medium text-muted-foreground">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {history.map((item) => {
                  const canEdit = isWithin24BusinessHours(item.closed_at);
                  return (
                    <tr key={item.cycle_id}>
                      <td className="px-4 py-3 font-medium">{item.cycle_name}</td>
                      <td className="px-4 py-3">{item.mvp_display_name}</td>
                      <td className="px-4 py-3">
                        <Badge variant="outline" className="text-xs">
                          {item.mvp_area}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground text-xs max-w-xs">
                        <span className="line-clamp-2">{item.mvp_reason ?? "—"}</span>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground text-xs tabular-nums">
                        {item.closed_at
                          ? new Date(item.closed_at).toLocaleDateString("es-MX", {
                              day: "numeric",
                              month: "short",
                              year: "numeric",
                            })
                          : "—"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <MvpEditButton
                          cycleId={item.cycle_id}
                          cycleName={item.cycle_name}
                          currentMvpName={
                            playerMap.get(item.mvp_player_id) ??
                            item.mvp_display_name
                          }
                          allPlayers={allPlayers}
                          canEdit={canEdit}
                        />
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
