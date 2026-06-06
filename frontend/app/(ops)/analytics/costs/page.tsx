
import type {
  AreaCostResponse,
  ComparisonResponse,
  EvolutionResponse,
} from "@/lib/types/cost";
import { CostTable } from "@/components/ops/analytics/cost-table";
import { CostComparison } from "@/components/ops/analytics/cost-comparison";
import { CostEvolution } from "@/components/ops/analytics/cost-evolution";
import { CostExportButton } from "@/components/ops/analytics/cost-export-button";
import { AlertTriangle, DollarSign, Users } from "lucide-react";
import Link from "next/link";

export const dynamic = "force-dynamic";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

async function fetchByArea(
  period: string,
  projectCode?: string,
): Promise<AreaCostResponse | null> {
  try {
    const params = new URLSearchParams({ period });
    if (projectCode) params.set("project_code", projectCode);
    const res = await fetch(`${API_BASE}/costs/by-area?${params}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json() as Promise<AreaCostResponse>;
  } catch {
    return null;
  }
}

async function fetchComparison(
  period: string,
  projectCode?: string,
): Promise<ComparisonResponse | null> {
  try {
    const params = new URLSearchParams({ period });
    if (projectCode) params.set("project_code", projectCode);
    const res = await fetch(`${API_BASE}/costs/comparison?${params}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json() as Promise<ComparisonResponse>;
  } catch {
    return null;
  }
}

async function fetchEvolution(area?: string): Promise<EvolutionResponse | null> {
  try {
    const params = new URLSearchParams();
    if (area) params.set("area", area);
    const res = await fetch(
      `${API_BASE}/costs/evolution${params.size ? `?${params}` : ""}`,
      { cache: "no-store" },
    );
    if (!res.ok) return null;
    return res.json() as Promise<EvolutionResponse>;
  } catch {
    return null;
  }
}

const PERIOD_LABELS: Record<string, string> = {
  q_current: "Trimestre actual",
  q_prev: "Trimestre anterior",
  last_12m: "Últimos 12 meses",
  y_current: "Año actual",
};

interface PageProps {
  searchParams: Promise<{ period?: string; project_code?: string }>;
}

export default async function CostsByAreaPage({ searchParams }: PageProps) {
  const { period = "q_current", project_code } = await searchParams;

  const [data, comparison, evolution] = await Promise.all([
    fetchByArea(period, project_code),
    fetchComparison(period, project_code),
    fetchEvolution(),
  ]);

  const periodLabel = PERIOD_LABELS[period] ?? period;

  // Empty state: API reachable pero sin costos capturados
  if (data && !data.has_any_cost) {
    return (
      <div className="flex flex-col gap-6 p-6 max-w-full">
        <div>
          <h1 className="text-xl font-semibold">Costo por área</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Vista ejecutiva de costos · acceso restringido</p>
        </div>
        <div className="flex flex-col items-center justify-center gap-4 py-20 border rounded-lg border-dashed">
          <DollarSign size={40} className="text-muted-foreground/30" />
          <div className="text-center">
            <p className="font-medium">Sin costos capturados</p>
            <p className="text-sm text-muted-foreground mt-1">
              Ningún player del equipo tiene costo registrado aún.
            </p>
          </div>
          <Link
            href="/admin/players"
            className="text-sm text-primary hover:underline"
          >
            Capturar costos en /admin/players →
          </Link>
        </div>
      </div>
    );
  }

  const totalCostFormatted = data?.total_cost
    ? new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(data.total_cost)
    : null;

  return (
    <div className="flex flex-col gap-6 p-6 max-w-full">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Costo por área</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Vista ejecutiva · {periodLabel}
            {data && (
              <span className="ml-2 text-[11px] opacity-60">
                {data.period_start} — {data.period_end}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Selector de periodo */}
          <PeriodSelector current={period} projectCode={project_code} />
          {/* Export CSV */}
          {data && data.areas.length > 0 && (
            <CostExportButton period={period} projectCode={project_code} />
          )}
        </div>
      </div>

      {/* KPI cards */}
      {data && (
        <div className="grid grid-cols-3 gap-4">
          <div className="rounded-lg border p-4">
            <p className="text-xs text-muted-foreground">CP producidos</p>
            <p className="text-2xl font-bold mt-1">{data.total_cp}</p>
          </div>
          <div className="rounded-lg border p-4">
            <p className="text-xs text-muted-foreground">Costo total (con datos)</p>
            <p className="text-2xl font-bold mt-1">{totalCostFormatted ?? "—"}</p>
            {!data.total_cost && (
              <p className="text-[10px] text-muted-foreground mt-1">
                Costo parcial (faltan datos)
              </p>
            )}
          </div>
          <div className="rounded-lg border p-4">
            <p className="text-xs text-muted-foreground">Áreas con datos</p>
            <p className="text-2xl font-bold mt-1">{data.areas.length}</p>
          </div>
        </div>
      )}

      {/* Aviso parcialidad */}
      {data && data.areas.some((a) => a.players.some((p) => p.cost_not_captured)) && (
        <div className="flex items-start gap-2 rounded-lg border border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-950/20 p-3 text-sm">
          <AlertTriangle size={16} className="text-yellow-600 mt-0.5 shrink-0" />
          <div>
            <span className="font-medium text-yellow-700 dark:text-yellow-400">Vista parcial —</span>{" "}
            <span className="text-yellow-700 dark:text-yellow-400">
              algunos players no tienen costo capturado. Los $/CP son estimaciones incompletas.{" "}
              <Link href="/admin/players" className="underline">
                Completar en /admin/players
              </Link>
            </span>
          </div>
        </div>
      )}

      {/* Tabla por área + expansión por player */}
      {data && data.areas.length > 0 ? (
        <CostTable areas={data.areas} />
      ) : (
        <div className="flex flex-col items-center justify-center gap-3 py-16 border rounded-lg border-dashed">
          <Users size={32} className="text-muted-foreground/30" />
          <p className="text-sm text-muted-foreground">Sin producción en este periodo.</p>
        </div>
      )}

      {/* Comparativa int vs ext */}
      {comparison && comparison.comparisons.length > 0 && (
        <CostComparison comparisons={comparison.comparisons} />
      )}

      {/* Evolución 12 meses */}
      {evolution && evolution.points.length > 0 && (
        <CostEvolution points={evolution.points} />
      )}
    </div>
  );
}

// ── Selector de periodo (Server Component inline) ──────────────
function PeriodSelector({
  current,
  projectCode,
}: {
  current: string;
  projectCode?: string;
}) {
  const periods = [
    { value: "q_current", label: "Trim. actual" },
    { value: "q_prev", label: "Trim. anterior" },
    { value: "last_12m", label: "12 meses" },
    { value: "y_current", label: "Año actual" },
  ];

  return (
    <div className="flex items-center gap-1 rounded-lg border p-0.5 bg-muted/30">
      {periods.map((p) => {
        const params = new URLSearchParams({ period: p.value });
        if (projectCode) params.set("project_code", projectCode);
        return (
          <Link
            key={p.value}
            href={`/analytics/costs?${params}`}
            className={`px-3 py-1 text-xs rounded-md transition-colors ${
              current === p.value
                ? "bg-background font-medium shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {p.label}
          </Link>
        );
      })}
    </div>
  );
}
