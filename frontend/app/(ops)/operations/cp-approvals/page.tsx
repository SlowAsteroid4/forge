import { api } from "@/lib/api";
import type {
  CpApprovalListResponse,
  XxlListResponse,
} from "@/lib/types/cp-approvals";
import { Badge } from "@/components/ui/badge";
import { ApprovalFilters } from "@/components/ops/cp-approvals-filters";
import { ApprovalTable } from "@/components/ops/cp-approvals-table";
import { XxlSection } from "@/components/ops/xxl-section";

interface PageProps {
  searchParams: Promise<{
    area?: string;
    player_id?: string;
    project_code?: string;
  }>;
}

async function getPending(
  area?: string,
  playerId?: string,
  projectCode?: string,
): Promise<CpApprovalListResponse> {
  const params = new URLSearchParams();
  if (area) params.set("area", area);
  if (playerId) params.set("player_id", playerId);
  if (projectCode) params.set("project_code", projectCode);
  const q = params.toString() ? `?${params}` : "";
  return api
    .get<CpApprovalListResponse>(`/cp-approvals/pending${q}`)
    .catch(() => ({ total: 0, items: [] }));
}

async function getXxl(): Promise<XxlListResponse> {
  return api
    .get<XxlListResponse>("/cp-approvals/xxl-detected")
    .catch(() => ({ total: 0, items: [] }));
}

export default async function CpApprovalsPage({ searchParams }: PageProps) {
  const { area, player_id, project_code } = await searchParams;

  const [pending, xxl] = await Promise.all([
    getPending(area, player_id, project_code),
    getXxl(),
  ]);

  // Derivar opciones de filtro a partir de los ítems disponibles
  const areas = [
    ...new Set(pending.items.map((i) => i.area)),
  ].sort();
  const projects = [
    ...new Set(
      pending.items
        .map((i) => i.project_code)
        .filter((p): p is string => p !== null),
    ),
  ].sort();

  return (
    <div className="flex flex-col flex-1 overflow-auto">
      <div className="flex-1 p-6 space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-lg font-semibold">Aprobaciones CP</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            {pending.total} pendiente{pending.total !== 1 ? "s" : ""}
            {xxl.total > 0 &&
              ` · ${xxl.total} XXL detectada${xxl.total !== 1 ? "s" : ""}`}
          </p>
        </div>

        {/* Filtros */}
        <ApprovalFilters areas={areas} projects={projects} />

        {/* Cola de pendientes */}
        <section>
          <ApprovalTable items={pending.items} />
        </section>

        {/* Sección XXL */}
        {xxl.total > 0 && (
          <section>
            <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
              XXL detectadas — requieren ruptura
              <Badge variant="destructive">{xxl.total}</Badge>
            </h2>
            <XxlSection items={xxl.items} />
          </section>
        )}
      </div>
    </div>
  );
}
