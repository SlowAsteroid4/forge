"use client";

import { useEffect, useState } from "react";
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { cn } from "@/lib/utils";
import type {
  CycleLeadGrouping,
  CycleLeadTimeResponse,
} from "@/lib/types/analytics";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

const GROUPINGS: { value: CycleLeadGrouping; label: string }[] = [
  { value: "cycle", label: "Por ciclo" },
  { value: "month", label: "Por mes" },
  { value: "historical", label: "Histórico" },
];

interface Props {
  apartado: string | null;
}

/**
 * CAMBIO 5 — Cycle time (In Progress→Done) y Lead time (Backlog→Done) en horas hábiles.
 * Serie temporal por ciclo/mes con toggle, + el agregado histórico. Cycle se recalcula
 * canónicamente; lead viene de lt_biz_hours (creación real). Hereda el filtro de apartado.
 */
export function CycleLeadChart({ apartado }: Props) {
  const [grouping, setGrouping] = useState<CycleLeadGrouping>("cycle");
  const [data, setData] = useState<CycleLeadTimeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    const ap = apartado ? `&apartado=${encodeURIComponent(apartado)}` : "";
    fetch(`${API_BASE}/analytics/cycle-lead-time?grouping=${grouping}${ap}`, {
      cache: "no-store",
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => active && setData(d))
      .catch(() => active && setData(null))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [grouping, apartado]);

  const o = data?.overall;
  const chartData = (data?.periods ?? []).map((p) => ({
    name: p.label.replace("Ciclo ", "").replace("2026-", ""),
    cycle: p.cycle_avg_h,
    lead: p.lead_avg_h,
    done: p.done_count,
  }));

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-1 p-1 rounded-lg bg-muted w-fit">
          {GROUPINGS.map((g) => (
            <button
              key={g.value}
              onClick={() => setGrouping(g.value)}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                grouping === g.value
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {g.label}
            </button>
          ))}
        </div>
        {o && (
          <div className="flex items-center gap-4 text-xs">
            <span className="text-muted-foreground">
              Histórico ({o.done_count} Done):
            </span>
            <span>
              <span className="text-muted-foreground">Cycle </span>
              <span className="font-semibold tabular-nums">
                {fmt(o.cycle_avg_h)}h
              </span>
              <span className="text-[10px] text-muted-foreground">
                {" "}
                med {fmt(o.cycle_median_h)}h
              </span>
            </span>
            <span>
              <span className="text-muted-foreground">Lead </span>
              <span className="font-semibold tabular-nums">{fmt(o.lead_avg_h)}h</span>
              <span className="text-[10px] text-muted-foreground">
                {" "}
                med {fmt(o.lead_median_h)}h
              </span>
            </span>
          </div>
        )}
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground py-12 text-center">Cargando…</p>
      ) : !chartData.length ? (
        <p className="text-sm text-muted-foreground py-12 text-center">
          Sin datos para este horizonte.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis
              tick={{ fontSize: 11 }}
              label={{ value: "horas háb.", angle: -90, position: "insideLeft", fontSize: 10 }}
            />
            <Tooltip
              contentStyle={{
                fontSize: 12,
                backgroundColor: "var(--popover)",
                border: "1px solid var(--border)",
                color: "var(--popover-foreground)",
                borderRadius: "var(--radius-md)",
              }}
              cursor={{ stroke: "var(--muted-foreground)" }}
              formatter={(v) => (v == null ? "—" : `${v}h`)}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line
              type="monotone"
              dataKey="cycle"
              name="Cycle time"
              stroke="#60A5FA"
              strokeWidth={2}
              dot={{ r: 3 }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="lead"
              name="Lead time"
              stroke="#A78BFA"
              strokeWidth={2}
              dot={{ r: 3 }}
              connectNulls
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function fmt(v: number | null): string {
  return v == null ? "—" : v.toFixed(1);
}
