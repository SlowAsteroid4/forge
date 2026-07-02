import { api } from "@/lib/api";
import type { CpWorklistResponse } from "@/lib/types/cp-worklist";
import { Badge } from "@/components/ui/badge";
import { CpWorklistGroups } from "@/components/ops/cp-worklist-groups";
import { XxlSection } from "@/components/ops/xxl-section";

/**
 * WP-24 — Subtasks sin CP, agrupadas por apartado (read-only).
 * Reemplaza la pantalla de aprobación manual de CP (retirada por ADR-016:
 * el CP se auto-lockea en el sync). Asignar CP inline es un WP futuro.
 */

const EMPTY: CpWorklistResponse = {
  total: 0,
  groups: [],
  xxl_total: 0,
  xxl_items: [],
  jira_base_url: null,
};

async function getWorklist(): Promise<CpWorklistResponse> {
  return api.get<CpWorklistResponse>("/cp-worklist").catch(() => EMPTY);
}

export default async function CpWorklistPage() {
  const data = await getWorklist();

  return (
    <div className="flex flex-col flex-1 overflow-auto">
      <div className="flex-1 p-6 space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-lg font-semibold">Subtasks sin CP</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            {data.total} sin tallar, por apartado
            {data.xxl_total > 0 &&
              ` · ${data.xxl_total} XXL detectada${data.xxl_total !== 1 ? "s" : ""}`}
          </p>
        </div>

        {/* Sección XXL — alerta primero: son inválidas y bloquean el flujo */}
        {data.xxl_total > 0 && (
          <section>
            <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
              XXL detectadas — requieren ruptura
              <Badge variant="destructive">{data.xxl_total}</Badge>
            </h2>
            <XxlSection items={data.xxl_items} jiraBaseUrl={data.jira_base_url} />
          </section>
        )}

        {/* Grupos por apartado */}
        <section>
          <CpWorklistGroups groups={data.groups} jiraBaseUrl={data.jira_base_url} />
        </section>
      </div>
    </div>
  );
}
