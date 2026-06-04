"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import type { DevCpPerDay } from "@/lib/types/analytics";

interface CpPerDayChartProps {
  devs: DevCpPerDay[];
  bizDays: number;
  usesWindowFallback?: boolean;
}

// Color by cp_per_day performance
function colorForRate(rate: number): string {
  if (rate >= 1.0) return "#4ADE80";
  if (rate >= 0.5) return "#FCD34D";
  return "#F87171";
}

export function CpPerDayChart({ devs, bizDays, usesWindowFallback }: CpPerDayChartProps) {
  if (!devs.length) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        Sin datos para este horizonte.
      </p>
    );
  }

  const sorted = [...devs].sort((a, b) => b.cp_per_day - a.cp_per_day);
  const data = sorted.map((d) => ({
    name: d.display_name.split(" ")[0], // first name only
    fullName: d.display_name,
    area: d.area,
    cp_per_day: +d.cp_per_day.toFixed(2),
    total_cp: d.total_cp,
  }));

  const teamAvg = devs.reduce((s, d) => s + d.cp_per_day, 0) / devs.length;

  return (
    <div>
      {usesWindowFallback && (
        <p className="text-[10px] text-muted-foreground mb-1">
          * Scope histórico no soportado — mostrando ventana móvil ({bizDays} días hábiles)
        </p>
      )}
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 40, left: 60, bottom: 4 }}>
          <XAxis type="number" tick={{ fontSize: 11 }} unit=" CP/d" />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={60} />
          <Tooltip
            formatter={(value, _name, props) => [
              `${Number(value ?? 0)} CP/día`,
              `${(props.payload as { fullName?: string; area?: string })?.fullName ?? ""} (${(props.payload as { area?: string })?.area ?? ""})`,
            ]}
            contentStyle={{ fontSize: 12 }}
          />
          <ReferenceLine
            x={+teamAvg.toFixed(2)}
            stroke="#94A3B8"
            strokeDasharray="3 3"
            label={{ value: `avg ${teamAvg.toFixed(1)}`, fontSize: 10, fill: "#94A3B8" }}
          />
          <Bar dataKey="cp_per_day" name="CP/día" radius={[0, 2, 2, 0]}>
            {data.map((entry, idx) => (
              <Cell key={idx} fill={colorForRate(entry.cp_per_day)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
