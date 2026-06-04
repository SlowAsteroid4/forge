"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { TimeInStatusRow } from "@/lib/types/analytics";

// Canonical JPDS palette per Manifiesto
const BUCKET_COLORS: Record<string, string> = {
  dev_resp_h: "#60A5FA", // blue — dev zone
  qa_h: "#FCA5A5",       // red — QA/testing (bottleneck zone)
  review_h: "#C7D2FE",   // indigo — review
  blocked_h: "#F87171",  // strong red — blocked
  waiting_h: "#E5E7EB",  // neutral — waiting
};

const BUCKET_LABELS: Record<string, string> = {
  dev_resp_h: "Dev",
  qa_h: "QA / Testing",
  review_h: "Review",
  blocked_h: "Bloqueado",
  waiting_h: "Waiting",
};

interface TimeInStatusChartProps {
  rows: TimeInStatusRow[];
}

export function TimeInStatusChart({ rows }: TimeInStatusChartProps) {
  if (!rows.length) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        Sin datos para este horizonte.
      </p>
    );
  }

  const buckets = ["dev_resp_h", "qa_h", "review_h", "blocked_h", "waiting_h"] as const;

  const data = rows.map((row) => ({
    name: row.group_key,
    dev_resp_h: row.dev_resp_h,
    qa_h: row.qa_h,
    review_h: row.review_h,
    blocked_h: row.blocked_h,
    waiting_h: row.waiting_h,
    done_count: row.done_count,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 11 }} unit="h" width={48} />
        <Tooltip
          formatter={(value, name) => [
            `${Number(value ?? 0).toFixed(1)}h`,
            BUCKET_LABELS[String(name ?? "")] ?? String(name ?? ""),
          ]}
          contentStyle={{ fontSize: 12 }}
        />
        <Legend
          formatter={(value: string) => BUCKET_LABELS[value] ?? value}
          wrapperStyle={{ fontSize: 11 }}
        />
        {buckets.map((bucket) => (
          <Bar key={bucket} dataKey={bucket} stackId="a" fill={BUCKET_COLORS[bucket]}>
            {data.map((_, idx) => (
              <Cell key={idx} fill={BUCKET_COLORS[bucket]} />
            ))}
          </Bar>
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
