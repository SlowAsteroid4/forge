"use client";

import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { CanonicalTimeRow } from "@/lib/types/analytics";
import { CANONICAL_COLORS, MEASURED_CANONICAL } from "@/lib/canonical-status";
import { cn } from "@/lib/utils";

interface CanonicalTimeBarsProps {
  rows: CanonicalTimeRow[];
  /** Áreas a incluir; si se omite, se muestran todas las filas. */
  includeKeys?: Set<string>;
  emptyLabel?: string;
}

interface Datum {
  name: string;
  total: number;
  done: number;
  [canonical: string]: number | string;
}

function fmtH(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : n.toFixed(1);
}

export function CanonicalTimeBars({
  rows,
  includeKeys,
  emptyLabel = "Sin datos para este horizonte.",
}: CanonicalTimeBarsProps) {
  const [active, setActive] = useState<string | null>(null);

  const filtered = includeKeys
    ? rows.filter((r) => includeKeys.has(r.group_key) || (r.area && includeKeys.has(r.area)))
    : rows;

  const usable = filtered.filter((r) => r.total_h > 0);

  if (!usable.length) {
    return <p className="text-sm text-muted-foreground py-8 text-center">{emptyLabel}</p>;
  }

  // Solo canónicos con tiempo medido (WP-07h). Oculta los que son 0 en todas las filas.
  const visibleStatuses = MEASURED_CANONICAL.filter((s) =>
    usable.some((r) => (r.by_canonical[s] ?? 0) > 0),
  );

  const data: Datum[] = usable.map((r) => {
    const d: Datum = { name: r.display_name, total: r.total_h, done: r.done_count };
    for (const s of visibleStatuses) d[s] = r.by_canonical[s] ?? 0;
    return d;
  });

  const height = Math.max(160, data.length * 56 + 24);

  return (
    <div>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 56, left: 8, bottom: 4 }}
          barCategoryGap="22%"
        >
          <XAxis type="number" tick={{ fontSize: 11 }} unit="h" />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 12 }}
            width={96}
          />
          <Tooltip
            cursor={{ fill: "rgba(0,0,0,0.04)" }}
            content={({ active: tipActive, payload, label }) => {
              if (!tipActive || !payload?.length) return null;
              const row = payload[0]?.payload as Datum | undefined;
              if (!row) return null;
              return (
                <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-md">
                  <p className="font-semibold mb-1">
                    {String(label)}{" "}
                    <span className="text-muted-foreground font-normal">
                      · {fmtH(row.total)}h · {row.done} Done
                    </span>
                  </p>
                  <ul className="space-y-0.5">
                    {visibleStatuses.map((s) => {
                      const h = (row[s] as number) ?? 0;
                      if (h <= 0) return null;
                      const pct = row.total > 0 ? (h / row.total) * 100 : 0;
                      return (
                        <li key={s} className="flex items-center gap-2 tabular-nums">
                          <span
                            className="inline-block h-2 w-2 rounded-sm"
                            style={{ backgroundColor: CANONICAL_COLORS[s] }}
                          />
                          <span className="flex-1">{s}</span>
                          <span className="font-medium">{fmtH(h)}h</span>
                          <span className="text-muted-foreground">{pct.toFixed(0)}%</span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              );
            }}
          />
          {visibleStatuses.map((s) => (
            <Bar
              key={s}
              dataKey={s}
              stackId="t"
              isAnimationActive={false}
              onMouseEnter={() => setActive(s)}
              onMouseLeave={() => setActive(null)}
            >
              {data.map((_, i) => (
                <Cell
                  key={i}
                  fill={CANONICAL_COLORS[s]}
                  opacity={active === null || active === s ? 1 : 0.35}
                />
              ))}
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>

      {/* Leyenda interactiva — resalta el estado al pasar el mouse */}
      <div className="mt-2 flex flex-wrap gap-3">
        {visibleStatuses.map((s) => (
          <button
            key={s}
            type="button"
            onMouseEnter={() => setActive(s)}
            onMouseLeave={() => setActive(null)}
            className={cn(
              "flex items-center gap-1.5 text-[11px] transition-opacity",
              active !== null && active !== s ? "opacity-40" : "opacity-100",
            )}
          >
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ backgroundColor: CANONICAL_COLORS[s] }}
            />
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
