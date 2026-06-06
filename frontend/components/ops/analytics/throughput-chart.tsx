"use client";

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { ThroughputPoint } from "@/lib/types/analytics";

interface ThroughputChartProps {
  cycles: ThroughputPoint[];
}

export function ThroughputChart({ cycles }: ThroughputChartProps) {
  if (!cycles.length) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        Sin datos para este horizonte.
      </p>
    );
  }

  const data = cycles.map((c) => ({
    name: `W${c.iso_week}`,
    subtasks: c.done_count,
    cp: c.total_cp,
    status: c.status,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <ComposedChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
        <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
        <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
        <Tooltip contentStyle={{ fontSize: 12, backgroundColor: "var(--popover)", border: "1px solid var(--border)", color: "var(--popover-foreground)", borderRadius: "var(--radius-md)" }} cursor={{ fill: "var(--muted)" }} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Bar yAxisId="left" dataKey="subtasks" name="Subtasks Done" fill="#60A5FA" radius={[2, 2, 0, 0]} />
        <Line
          yAxisId="right"
          type="monotone"
          dataKey="cp"
          name="CP"
          stroke="#4ADE80"
          strokeWidth={2}
          dot={{ r: 3 }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
