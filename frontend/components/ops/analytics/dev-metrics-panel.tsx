"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import type {
  AnalyticsScope,
  DevListItem,
  DevMetricsResponse,
  DevStateRow,
} from "@/lib/types/analytics";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

interface Props {
  devs: DevListItem[];
  scope: AnalyticsScope;
  apartado: string | null;
}

/**
 * CAMBIO 7 — Métricas por dev. Al seleccionar un dev: cycle/lead/qa + tiempo promedio
 * por estado CRUDO (los reales de Jira) y CANÓNICO (los 9 agregados vía el mismo
 * CANONICAL_STATUS_MAP de WP-17a). 'Equipo de Producto' funciona igual (agregado).
 */
export function DevMetricsPanel({ devs, scope, apartado }: Props) {
  const [selected, setSelected] = useState<number | null>(devs[0]?.player_id ?? null);
  const [data, setData] = useState<DevMetricsResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selected == null) return;
    let active = true;
    setLoading(true);
    const ap = apartado ? `&apartado=${encodeURIComponent(apartado)}` : "";
    fetch(
      `${API_BASE}/analytics/dev-metrics?player_id=${selected}&scope=${scope}${ap}`,
      { cache: "no-store" },
    )
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => active && setData(d))
      .catch(() => active && setData(null))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [selected, scope, apartado]);

  if (!devs.length) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        Sin devs con tareas Done en este filtro.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {/* Selector de dev */}
      <div className="flex items-center gap-1 flex-wrap">
        {devs.map((d) => (
          <button
            key={d.player_id}
            onClick={() => setSelected(d.player_id)}
            className={cn(
              "px-2.5 py-1 rounded-md text-xs font-medium transition-colors border",
              selected === d.player_id
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border text-muted-foreground hover:text-foreground hover:bg-muted",
            )}
          >
            {d.display_name}
            <span className="ml-1 text-[10px] opacity-70">{d.area}</span>
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground py-8 text-center">Cargando…</p>
      ) : !data ? (
        <p className="text-sm text-muted-foreground py-8 text-center">
          No se pudo cargar el dev.
        </p>
      ) : data.done_count === 0 ? (
        <p className="text-sm text-muted-foreground py-8 text-center">
          {data.display_name} no tiene tareas Done en este filtro.
        </p>
      ) : (
        <>
          {/* KPIs del dev */}
          <div className="flex items-center gap-2 flex-wrap">
            {data.is_aggregate && (
              <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-amber-500/15 text-amber-600 dark:text-amber-400">
                cuenta agregada
              </span>
            )}
            <Kpi label="Done" value={`${data.done_count}`} />
            <Kpi label="Cycle prom." value={hrs(data.cycle_avg_h)} />
            <Kpi label="Lead prom." value={hrs(data.lead_avg_h)} />
            <Kpi
              label="QA 1er intento"
              value={data.qa_first_pass_pct == null ? "—" : `${data.qa_first_pass_pct}%`}
            />
          </div>

          {/* Tablas crudo / canónico */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <StateTable
              title="Estados crudos (Jira)"
              subtitle="Tiempo promedio por estado real por el que pasó"
              rows={data.raw_states}
              showCanonical
            />
            <StateTable
              title="Estados canónicos (9)"
              subtitle="Agregado por los 9 del Manifiesto JPDS"
              rows={data.canonical_states}
            />
          </div>
        </>
      )}
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-card px-3 py-1.5">
      <span className="text-[10px] text-muted-foreground block">{label}</span>
      <span className="text-sm font-semibold tabular-nums">{value}</span>
    </div>
  );
}

function StateTable({
  title,
  subtitle,
  rows,
  showCanonical = false,
}: {
  title: string;
  subtitle: string;
  rows: DevStateRow[];
  showCanonical?: boolean;
}) {
  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      <div className="px-3 py-2 border-b border-border">
        <h4 className="text-xs font-semibold">{title}</h4>
        <p className="text-[10px] text-muted-foreground">{subtitle}</p>
      </div>
      {rows.length === 0 ? (
        <p className="text-xs text-muted-foreground px-3 py-4 text-center">Sin datos.</p>
      ) : (
        <table className="w-full text-xs">
          <thead>
            <tr className="text-[10px] text-muted-foreground border-b border-border">
              <th className="text-left font-medium px-3 py-1.5">Estado</th>
              {showCanonical && <th className="text-left font-medium px-2 py-1.5">→ canónico</th>}
              <th className="text-right font-medium px-2 py-1.5">prom.</th>
              <th className="text-right font-medium px-3 py-1.5">n</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.status} className="border-b border-border/50 last:border-0">
                <td className="px-3 py-1.5">{r.status}</td>
                {showCanonical && (
                  <td className="px-2 py-1.5 text-muted-foreground">{r.canonical}</td>
                )}
                <td className="px-2 py-1.5 text-right tabular-nums">{r.avg_h}h</td>
                <td className="px-3 py-1.5 text-right tabular-nums text-muted-foreground">
                  {r.n}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function hrs(v: number | null): string {
  return v == null ? "—" : `${v.toFixed(1)}h`;
}
