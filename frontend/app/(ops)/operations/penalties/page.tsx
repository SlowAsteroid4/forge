import { api } from "@/lib/api";
import type {
  PenaltyListResponse,
  DebuffCatalogResponse,
} from "@/lib/types/penalties";
import { PenaltiesClient } from "./PenaltiesClient";

interface PageProps {
  searchParams: Promise<{
    cycle_id?: string;
    player_id?: string;
    type?: string;
    applied_by?: string;
  }>;
}

async function getPenalties(
  cycleId?: string,
  playerId?: string,
  type?: string,
  appliedBy?: string,
): Promise<PenaltyListResponse> {
  const params = new URLSearchParams();
  if (cycleId) params.set("cycle_id", cycleId);
  if (playerId) params.set("player_id", playerId);
  if (type) params.set("adjustment_type", type);
  if (appliedBy) params.set("applied_by", appliedBy);
  const q = params.toString() ? `?${params}` : "";
  return api
    .get<PenaltyListResponse>(`/penalties${q}`)
    .catch(() => ({ total: 0, page: 1, page_size: 50, items: [] }));
}

async function getCatalog(): Promise<DebuffCatalogResponse> {
  return api
    .get<DebuffCatalogResponse>("/penalties/debuffs")
    .catch(() => ({ total: 0, items: [] }));
}

export default async function PenaltiesPage({ searchParams }: PageProps) {
  const { cycle_id, player_id, type, applied_by } = await searchParams;

  const [penalties, catalog] = await Promise.all([
    getPenalties(cycle_id, player_id, type, applied_by),
    getCatalog(),
  ]);

  return (
    <div className="flex flex-col flex-1 overflow-auto">
      <div className="flex-1 p-6 space-y-6">
        <PenaltiesClient
          items={penalties.items}
          catalog={catalog.items}
          total={penalties.total}
        />
      </div>
    </div>
  );
}
