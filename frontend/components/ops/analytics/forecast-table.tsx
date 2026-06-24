"use client";

import { useState } from "react";
import type { EpicForecastItem, EpicForecastDetail } from "@/lib/types/forecast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronRight, AlertTriangle, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface ForecastTableProps {
  epics: EpicForecastItem[];
  apiBase: string;
}

function fmt(dateStr: string | null): string {
  if (!dateStr) return "—";
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "2-digit" });
}

function pctColor(pct: number): string {
  if (pct >= 80) return "text-green-600";
  if (pct >= 50) return "text-yellow-600";
  return "text-red-600";
}

function AreaRow({ area }: { area: NonNullable<EpicForecastDetail["areas"]>[number] }) {
  return (
    <tr className="border-b border-border/30 bg-muted/20 text-xs">
      <td className="py-1.5 pl-10 pr-2 text-muted-foreground font-mono">{area.area}</td>
      <td className="py-1.5 px-2 text-right text-muted-foreground">
        {area.cp_done.toFixed(0)} / {(area.cp_done + area.cp_pending).toFixed(0)}
      </td>
      <td className="py-1.5 px-2 text-right text-muted-foreground">
        {area.cp_pending.toFixed(0)}
      </td>
      <td className="py-1.5 px-2 text-right text-muted-foreground">
        {area.velocity_avg.toFixed(1)} CP/sem
        {area.preliminary && (
          <span className="ml-1 text-orange-500" title={`Solo ${area.n_cycles_data} ciclos de datos`}>
            *
          </span>
        )}
      </td>
      <td className="py-1.5 px-2 text-right text-green-700 font-medium">
        {fmt(area.date_optimistic)}
      </td>
      <td className="py-1.5 px-2 text-right text-blue-700 font-medium">
        {fmt(area.date_realistic)}
      </td>
      <td className="py-1.5 px-2 text-right text-orange-700 font-medium">
        {fmt(area.date_conservative)}
      </td>
      <td className="py-1.5 px-2" />
    </tr>
  );
}

function EpicRow({
  epic,
  apiBase,
}: {
  epic: EpicForecastItem;
  apiBase: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState<EpicForecastDetail | null>(null);
  const [loading, setLoading] = useState(false);

  const hasCP = epic.cp_total > 0;

  async function toggleDetail() {
    if (!hasCP) return;
    if (!expanded && !detail) {
      setLoading(true);
      try {
        const r = await fetch(`${apiBase}/forecast/epics/${epic.epic_key}`);
        if (r.ok) setDetail(await r.json());
      } finally {
        setLoading(false);
      }
    }
    setExpanded((v) => !v);
  }

  return (
    <>
      <tr
        className={cn(
          "border-b border-border text-sm",
          hasCP ? "cursor-pointer hover:bg-accent/30" : "opacity-60",
        )}
        onClick={toggleDetail}
      >
        <td className="py-2 pl-3 pr-2 w-6">
          {hasCP ? (
            loading ? (
              <span className="animate-spin inline-block w-3 h-3 border border-foreground/30 border-t-foreground rounded-full" />
            ) : expanded ? (
              <ChevronDown size={14} />
            ) : (
              <ChevronRight size={14} />
            )
          ) : null}
        </td>
        <td className="py-2 px-2 font-mono text-xs text-muted-foreground">{epic.epic_key}</td>
        <td className="py-2 px-2 max-w-[260px] truncate" title={epic.summary}>
          {epic.summary}
          {epic.preliminary && (
            <span
              className="ml-1 text-orange-500 text-[10px]"
              title={epic.warning ?? "Forecast preliminar"}
            >
              ⚠ prelim
            </span>
          )}
        </td>
        <td className="py-2 px-2 text-right">
          <span className={cn("font-medium tabular-nums", pctColor(epic.pct_done))}>
            {epic.pct_done.toFixed(0)}%
          </span>
        </td>
        <td className="py-2 px-2 text-right tabular-nums text-muted-foreground">
          {epic.cp_done.toFixed(0)}/{epic.cp_total.toFixed(0)}
        </td>
        <td className="py-2 px-2 text-right tabular-nums text-muted-foreground">
          {hasCP ? epic.cp_pending.toFixed(0) : "—"}
        </td>
        <td className="py-2 px-2 text-right text-green-700 font-medium tabular-nums">
          {hasCP ? fmt(epic.date_optimistic) : "—"}
        </td>
        <td className="py-2 px-2 text-right text-blue-700 font-medium tabular-nums">
          {hasCP ? fmt(epic.date_realistic) : "—"}
        </td>
        <td className="py-2 px-2 text-right text-orange-700 font-medium tabular-nums">
          {hasCP ? fmt(epic.date_conservative) : "—"}
        </td>
        <td className="py-2 px-2 text-center">
          {epic.blocked_count > 0 && (
            <Badge variant="destructive" className="h-4 px-1 text-[10px]">
              {epic.blocked_count}
            </Badge>
          )}
        </td>
      </tr>
      {expanded && detail && detail.areas.map((af) => (
        <AreaRow key={af.area} area={af} />
      ))}
      {expanded && detail && detail.areas.length === 0 && (
        <tr className="border-b border-border/30">
          <td colSpan={10} className="py-2 pl-10 text-xs text-muted-foreground">
            Sin desglose por área disponible
          </td>
        </tr>
      )}
    </>
  );
}

export function ForecastTable({ epics, apiBase }: ForecastTableProps) {
  if (epics.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground gap-2">
        <TrendingUp size={32} className="opacity-30" />
        <p className="text-sm">Sin épicas activas</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            <th className="py-2 pl-3 pr-2 w-6" />
            <th className="py-2 px-2 text-left text-xs font-semibold text-muted-foreground">Clave</th>
            <th className="py-2 px-2 text-left text-xs font-semibold text-muted-foreground">Épica</th>
            <th className="py-2 px-2 text-right text-xs font-semibold text-muted-foreground">%</th>
            <th className="py-2 px-2 text-right text-xs font-semibold text-muted-foreground">CP hecho/total</th>
            <th className="py-2 px-2 text-right text-xs font-semibold text-muted-foreground">CP pend.</th>
            <th className="py-2 px-2 text-right text-xs font-semibold text-green-700">Optimista</th>
            <th className="py-2 px-2 text-right text-xs font-semibold text-blue-700">Realista</th>
            <th className="py-2 px-2 text-right text-xs font-semibold text-orange-700">Conservador</th>
            <th className="py-2 px-2 text-center text-xs font-semibold text-muted-foreground">Bloq.</th>
          </tr>
        </thead>
        <tbody>
          {epics.map((e) => (
            <EpicRow key={e.epic_key} epic={e} apiBase={apiBase} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
