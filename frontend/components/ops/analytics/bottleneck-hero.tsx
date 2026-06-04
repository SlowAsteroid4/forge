"use client";

import type { StatusDetailRow } from "@/lib/types/analytics";

// JPDS Nivel 1 (gobierno/producto: PO, PM) no genera métricas de flujo/delivery.
// Solo las áreas de entrega participan en cuellos de botella y velocity.
export const DELIVERY_AREAS = new Set(["BE", "FE", "DESIGN", "DB", "QA"]);

// Terminal/passive states that are not bottlenecks
const PASSIVE_STATES = new Set([
  "Done",
  "Cerrado",
  "Closed",
  "To Do",
  "Triaged",
  "Refinement",
  "Staging",
  "Backlog",
  "Nueva",
  "Nuevo",
  "Ready for Release",
  "Ready for dev",
]);

interface BottleneckHeroProps {
  rows: StatusDetailRow[];
}

interface BottleneckResult {
  area: string;
  status: string;
  hours: number;
}

function findBottleneck(rows: StatusDetailRow[]): BottleneckResult | null {
  let best: BottleneckResult | null = null;

  for (const row of rows) {
    // Skip governance areas (JPDS Nivel 1 — PO/PM excluded from flow metrics)
    if (!DELIVERY_AREAS.has(row.group_key)) continue;

    for (const [status, hours] of Object.entries(row.by_status)) {
      if (PASSIVE_STATES.has(status)) continue;
      if (hours <= 0) continue;
      if (!best || hours > best.hours) {
        best = { area: row.group_key, status, hours };
      }
    }
  }

  return best;
}

export function BottleneckHero({ rows }: BottleneckHeroProps) {
  const bottleneck = findBottleneck(rows);

  if (!bottleneck) {
    return (
      <div className="rounded-lg border border-dashed border-border p-4">
        <p className="text-sm text-muted-foreground">Sin datos de time-in-status.</p>
      </div>
    );
  }

  const { area, status, hours } = bottleneck;
  const hoursDisplay = hours >= 1000 ? `${(hours / 1000).toFixed(1)}k h` : `${Math.round(hours)}h`;

  return (
    <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 flex items-start gap-4">
      <div className="text-2xl select-none">🔴</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-foreground">
          Cuello de botella: <span className="text-destructive">{area}</span> acumula{" "}
          <span className="text-destructive font-bold tabular-nums">{hoursDisplay}</span> en &ldquo;
          {status}&rdquo;.
        </p>
        <p className="text-[11px] text-muted-foreground mt-1">
          Calculado sobre{" "}
          <code className="font-mono bg-muted px-1 rounded">time-in-status-detail</code> — mayor
          acumulado excluyendo estados terminales (Done, Cerrado, Backlog…).
          <br />
          Campo fuente:{" "}
          <code className="font-mono bg-muted px-1 rounded">
            rows[{`group_key="${area}"`}].by_status[&quot;{status}&quot;]
          </code>{" "}
          = {hours.toFixed(1)}h
        </p>
      </div>
    </div>
  );
}
