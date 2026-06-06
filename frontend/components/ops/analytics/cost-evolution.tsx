"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { EvolutionPointItem } from "@/lib/types/cost";

export function CostEvolution({ points }: { points: EvolutionPointItem[] }) {
  const hasAnyCost = points.some((p) => p.cost_per_cp !== null);

  const chartData = points.map((p) => ({
    label: p.period_label.slice(0, 7), // "2026-01"
    cp: p.cp_total,
    cost_per_cp: p.cost_per_cp ?? null,
    cost_total: p.cost_total ?? null,
  }));

  return (
    <div className="rounded-lg border overflow-hidden">
      <div className="px-4 py-3 border-b bg-muted/30">
        <h2 className="text-sm font-semibold">Evolución $/CP · últimos 12 meses</h2>
        {!hasAnyCost && (
          <p className="text-xs text-muted-foreground mt-0.5">
            Sin costos capturados en los últimos 12 meses.
          </p>
        )}
      </div>
      {hasAnyCost ? (
        <div className="p-4">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData} margin={{ top: 4, right: 16, left: 8, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 10 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tick={{ fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) =>
                  new Intl.NumberFormat("es-MX", {
                    notation: "compact",
                    style: "currency",
                    currency: "MXN",
                    maximumFractionDigits: 0,
                  }).format(v)
                }
              />
              <Tooltip
                formatter={(value, name) => [
                  typeof value === "number"
                    ? new Intl.NumberFormat("es-MX", {
                        style: "currency",
                        currency: "MXN",
                        maximumFractionDigits: 2,
                      }).format(value)
                    : String(value),
                  name === "cost_per_cp" ? "$/CP" : name,
                ]}
                labelClassName="text-xs"
                contentStyle={{ fontSize: 12, backgroundColor: "var(--popover)", border: "1px solid var(--border)", color: "var(--popover-foreground)", borderRadius: "var(--radius-md)" }}
              />
              <Legend
                formatter={(value) => (value === "cost_per_cp" ? "$/CP" : value)}
                wrapperStyle={{ fontSize: 11 }}
              />
              <Line
                type="monotone"
                dataKey="cost_per_cp"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ r: 3 }}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="py-10 text-center text-sm text-muted-foreground">
          Captura costos en /admin/players para ver la evolución histórica.
        </div>
      )}
    </div>
  );
}
