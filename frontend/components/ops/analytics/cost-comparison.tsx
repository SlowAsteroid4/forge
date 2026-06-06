"use client";

import type { IntExtComparisonItem } from "@/lib/types/cost";

function Bar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="h-2 w-full rounded-full bg-muted/40 overflow-hidden">
      <div
        className={`h-full rounded-full ${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export function CostComparison({ comparisons }: { comparisons: IntExtComparisonItem[] }) {
  // Solo áreas con al menos un lado con datos
  const relevant = comparisons.filter(
    (c) => c.int_cost_per_cp !== null || c.ext_cost_per_cp !== null,
  );

  if (relevant.length === 0) {
    return (
      <div className="rounded-lg border p-4">
        <h2 className="text-sm font-semibold mb-2">Comparativa interno vs externo</h2>
        <p className="text-xs text-muted-foreground">
          Sin datos suficientes para comparar (se necesitan players de ambos tipos con costo y CP en el periodo).
        </p>
      </div>
    );
  }

  const maxCostPerCp = Math.max(
    ...relevant.flatMap((c) => [c.int_cost_per_cp ?? 0, c.ext_cost_per_cp ?? 0]),
  );

  const fmt = (n: number) =>
    new Intl.NumberFormat("es-MX", {
      style: "currency",
      currency: "MXN",
      maximumFractionDigits: 0,
    }).format(n);

  return (
    <div className="rounded-lg border overflow-hidden">
      <div className="px-4 py-3 border-b bg-muted/30">
        <h2 className="text-sm font-semibold">Comparativa interno vs externo · $/CP</h2>
      </div>
      <div className="divide-y">
        {relevant.map((c) => (
          <div key={c.area} className="p-4 space-y-2">
            <div className="flex items-start justify-between gap-4">
              <div>
                <span className="font-medium text-sm">{c.area}</span>
                {c.multiplier !== null && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    {c.insight}
                  </span>
                )}
              </div>
              {c.multiplier !== null && (
                <span
                  className={`text-xs font-semibold px-2 py-0.5 rounded ${
                    c.multiplier > 1.5
                      ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300"
                      : c.multiplier > 1
                        ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                        : "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                  }`}
                >
                  {c.multiplier.toFixed(2)}×
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Interno ({c.int_players})</span>
                  <span className="font-medium">
                    {c.int_cost_per_cp !== null ? fmt(c.int_cost_per_cp) : "—"}
                  </span>
                </div>
                {c.int_cost_per_cp !== null && (
                  <Bar value={c.int_cost_per_cp} max={maxCostPerCp} color="bg-blue-500" />
                )}
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Externo ({c.ext_players})</span>
                  <span className="font-medium">
                    {c.ext_cost_per_cp !== null ? fmt(c.ext_cost_per_cp) : "—"}
                  </span>
                </div>
                {c.ext_cost_per_cp !== null && (
                  <Bar value={c.ext_cost_per_cp} max={maxCostPerCp} color="bg-orange-500" />
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
