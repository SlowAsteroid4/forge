"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from "recharts";
import type { DevQaFirstPass } from "@/lib/types/analytics";

function colorForPct(pct: number): string {
  if (pct >= 80) return "#4ADE80";
  if (pct >= 50) return "#FCD34D";
  return "#F87171";
}

interface QaFirstPassChartProps {
  devs: DevQaFirstPass[];
}

export function QaFirstPassChart({ devs }: QaFirstPassChartProps) {
  // Exclude devs with total=0 (NULLs don't count)
  const withData = devs.filter((d) => d.total > 0);

  if (!withData.length) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        Sin datos de QA para este horizonte.
      </p>
    );
  }

  // Sort desc by first_pass_pct
  const sorted = [...withData].sort((a, b) => b.first_pass_pct - a.first_pass_pct);

  const data = sorted.map((d) => ({
    name: d.display_name.split(" ").slice(0, 2).join(" "),
    fullName: d.display_name,
    area: d.area,
    pct: +d.first_pass_pct.toFixed(1),
    passed: d.passed,
    total: d.total,
  }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(240, data.length * 28)}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 48, left: 120, bottom: 4 }}>
        <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fontSize: 11 }}
          width={120}
          tickFormatter={(v: string) => v}
        />
        <Tooltip
          formatter={(value, _name, props) => {
            const p = props.payload as { fullName?: string; area?: string; passed?: number; total?: number } | undefined;
            return [
              `${Number(value ?? 0)}% (${p?.passed ?? 0}/${p?.total ?? 0})`,
              `${p?.fullName ?? ""} — ${p?.area ?? ""}`,
            ];
          }}
          contentStyle={{ fontSize: 12 }}
        />
        <ReferenceLine x={80} stroke="#4ADE80" strokeDasharray="3 3" label={{ value: "80%", fontSize: 10, fill: "#4ADE80" }} />
        <ReferenceLine x={50} stroke="#FCD34D" strokeDasharray="3 3" label={{ value: "50%", fontSize: 10, fill: "#FCD34D" }} />
        <Bar dataKey="pct" name="QA first-pass %" radius={[0, 2, 2, 0]}>
          {data.map((entry, idx) => (
            <Cell key={idx} fill={colorForPct(entry.pct)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
