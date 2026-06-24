import { api } from "@/lib/api";
import type { PlayerAdminListResponse } from "@/lib/types/players";
import { PlayersClient } from "@/components/ops/players/PlayersClient";

export const dynamic = "force-dynamic";

async function getPlayers(): Promise<PlayerAdminListResponse> {
  return api
    .get<PlayerAdminListResponse>("/admin/players")
    .catch(() => ({ players: [], total: 0 }));
}

export default async function PlayersAdminPage() {
  const data = await getPlayers();

  return (
    <div className="flex flex-col flex-1 overflow-auto">
      <div className="flex-1 p-6 space-y-6">
        <div>
          <h1 className="text-xl font-semibold">Players</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Administración de perfiles, costos y flags. Los campos marcados como "sincronizados
            desde Jira" son solo lectura.
          </p>
        </div>
        <PlayersClient initialPlayers={data.players} total={data.total} />
      </div>
    </div>
  );
}
