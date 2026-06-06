import type { EpicForecastListResponse } from "@/lib/types/forecast";
import { ForecastTable } from "@/components/ops/analytics/forecast-table";
import { ForecastTimeline } from "@/components/ops/analytics/forecast-timeline";
import { ForecastExportButton } from "@/components/ops/analytics/forecast-export-button";
import { AlertTriangle, RefreshCw } from "lucide-react";

export const dynamic = "force-dynamic";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

async function fetchForecast(
  project_code?: string,
  epic_status?: string,
): Promise<EpicForecastListResponse | null> {
  try {
    const params = new URLSearchParams();
    if (project_code) params.set("project_code", project_code);
    if (epic_status) params.set("epic_status", epic_status);
    const url = `${API_BASE}/forecast/epics${params.size ? `?${params}` : ""}`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json() as Promise<EpicForecastListResponse>;
  } catch {
    return null;
  }
}

interface PageProps {
  searchParams: Promise<{ project_code?: string; epic_status?: string }>;
}

export default async function ForecastPage({ searchParams }: PageProps) {
  const { project_code, epic_status } = await searchParams;
  const data = await fetchForecast(project_code, epic_status);

  const preliminaryEpics = data?.epics.filter((e) => e.preliminary && e.cp_total > 0) ?? [];
  const epicsWithCP = data?.epics.filter((e) => e.cp_total > 0) ?? [];
  const epicsNoCP = data?.epics.filter((e) => e.cp_total === 0) ?? [];

  return (
    <div className="flex flex-col gap-6 p-6 max-w-full">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Forecast P30/P50/P85</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Proyección de cierre por épica · ventana de {data?.window_size ?? 4} ciclos cerrados
            {data && (
              <span className="ml-2 text-[11px] opacity-60">
                ({data.n_closed_cycles} disponibles · calculado{" "}
                {new Date(data.calculated_at).toLocaleTimeString("es-MX", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
                )
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <ForecastExportButton apiBase={API_BASE} projectCode={project_code} epicStatus={epic_status} />
        </div>
      </div>

      {/* Filters */}
      <form method="GET" className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <label className="text-xs text-muted-foreground font-medium">Estado épica</label>
          <select
            name="epic_status"
            defaultValue={epic_status ?? ""}
            className="h-8 text-xs rounded-md border border-border bg-background px-2 focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="">Todos</option>
            <option value="In Progress">In Progress</option>
            <option value="Backlog">Backlog</option>
          </select>
        </div>
        <button
          type="submit"
          className="h-8 px-3 text-xs rounded-md bg-secondary text-secondary-foreground hover:bg-secondary/80 flex items-center gap-1"
        >
          <RefreshCw size={12} />
          Filtrar
        </button>
      </form>

      {/* Banner preliminar */}
      {preliminaryEpics.length > 0 && (
        <div className="flex items-start gap-2 rounded-md border border-orange-300 bg-orange-50 p-3 text-sm text-orange-800">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" />
          <div>
            <p className="font-medium">Forecast preliminar en {preliminaryEpics.length} épica(s)</p>
            <p className="text-xs mt-0.5 opacity-80">
              Menos de 4 ciclos de historia para calcular velocity en estas áreas. Las estimaciones
              mejorarán conforme se cierren más ciclos.
            </p>
            <ul className="mt-1 text-xs opacity-70 list-disc list-inside">
              {preliminaryEpics.map((e) => (
                <li key={e.epic_key}>
                  {e.epic_key} — {e.summary}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Empty state: no data at all */}
      {!data && (
        <div className="rounded-md border border-border p-8 text-center text-muted-foreground text-sm">
          No se pudo obtener el forecast. Verifica que el backend esté corriendo.
        </div>
      )}

      {data && data.total === 0 && (
        <div className="rounded-md border border-border p-8 text-center text-muted-foreground text-sm">
          Sin épicas activas{project_code ? ` para el proyecto ${project_code}` : ""}.
        </div>
      )}

      {/* Timeline */}
      {data && epicsWithCP.length > 0 && (
        <section className="rounded-lg border border-border bg-card">
          <div className="px-4 py-3 border-b border-border">
            <h2 className="text-sm font-semibold">Timeline de cierre estimado</h2>
            <p className="text-xs text-muted-foreground">
              Haz clic en una fila de la tabla para ver el desglose por área
            </p>
          </div>
          <div className="p-4">
            <ForecastTimeline epics={epicsWithCP} />
          </div>
        </section>
      )}

      {/* Main table */}
      {data && data.total > 0 && (
        <section className="rounded-lg border border-border bg-card overflow-hidden">
          <div className="px-4 py-3 border-b border-border flex items-center justify-between">
            <h2 className="text-sm font-semibold">
              Épicas activas ({data.total})
              {epicsNoCP.length > 0 && (
                <span className="text-muted-foreground font-normal ml-1 text-xs">
                  · {epicsNoCP.length} sin CP estimado
                </span>
              )}
            </h2>
            <p className="text-xs text-muted-foreground">
              Click en una fila para ver desglose por área
            </p>
          </div>
          <ForecastTable epics={data.epics} apiBase={API_BASE} />
        </section>
      )}

      {/* Sin CP notice */}
      {data && epicsNoCP.length > 0 && epicsWithCP.length === 0 && (
        <div className="rounded-md border border-border p-6 text-center text-sm text-muted-foreground">
          <p className="font-medium">Sin CP estimado en épicas activas</p>
          <p className="text-xs mt-1 opacity-70">
            El forecast requiere que las subtasks tengan CP asignado. Ejecuta una sincronización o
            aprueba subtasks pendientes.
          </p>
        </div>
      )}
    </div>
  );
}
