"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import type { AreaBreakdown } from "@/lib/types/analytics";

const AREA_COLORS: Record<string, string> = {
  BE: "#60A5FA",
  FE: "#4ADE80",
  PO: "#F59E0B",
  DB: "#C084FC",
  QA: "#F87171",
};

interface CpByAreaChartProps {
  areas: AreaBreakdown[];
  usesWindowFallback?: boolean;
}

export function CpByAreaChart({ areas, usesWindowFallback }: CpByAreaChartProps) {
  if (!areas.length) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        Sin datos para este horizonte.
      </p>
    );
  }

  const data = areas.map((a) => ({
    name: a.area,
    cp: a.total_cp,
    subtasks: a.done_count,
  }));

  return (
    <div>
      {usesWindowFallback && (
        <p className="text-[10px] text-muted-foreground mb-1">
          * Scope histórico no soportado — mostrando ventana móvil (4 ciclos)
        </p>
      )}
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
          <XAxis dataKey="name" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip
            formatter={(value, name) => [
              Number(value ?? 0),
              String(name ?? "").toLowerCase() === "cp" ? "CP" : "Subtasks",
            ]}
            contentStyle={{ fontSize: 12, backgroundColor: "var(--popover)", border: "1px solid var(--border)", color: "var(--popover-foreground)", borderRadius: "var(--radius-md)" }}
            itemStyle={{ color: "var(--popover-foreground)" }}
            labelStyle={{ color: "var(--popover-foreground)" }}
            cursor={{ fill: "var(--muted)" }}
          />
          <Bar dataKey="cp" name="CP" radius={[2, 2, 0, 0]}>
            {data.map((entry, idx) => (
              <Cell key={idx} fill={AREA_COLORS[entry.name] ?? "#94A3B8"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
