"use client";

import { Fragment, useState } from "react";
import { ChevronDown, ChevronRight, AlertTriangle, Info } from "lucide-react";
import type { AreaCostItem, PlayerCostItem } from "@/lib/types/cost";

function fmt(n: number | null, style: "currency" | "number" = "number"): string {
  if (n === null) return "—";
  if (style === "currency") {
    return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 }).format(n);
  }
  return new Intl.NumberFormat("es-MX", { maximumFractionDigits: 2 }).format(n);
}

function DeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null) return <span className="text-muted-foreground text-xs">—</span>;
  const positive = delta >= 0;
  return (
    <span className={`text-xs font-medium ${positive ? "text-red-500" : "text-green-600"}`}>
      {positive ? "▲" : "▼"} {Math.abs(delta).toFixed(1)}%
    </span>
  );
}

function PlayerRow({ p }: { p: PlayerCostItem }) {
  return (
    <tr className="border-t border-border/40 bg-muted/20">
      <td className="py-2 pl-10 pr-2">
        <span className="text-sm text-muted-foreground">{p.display_name}</span>
        {p.employment_type === "external" && (
          <span className="ml-2 text-[10px] rounded px-1 py-0.5 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
            ext
          </span>
        )}
      </td>
      <td className="py-2 px-3 text-center text-sm">{p.cp_total}</td>
      <td className="py-2 px-3 text-center text-sm">{p.done_subtasks}</td>
      <td className="py-2 px-3 text-right text-sm">
        {p.cost_not_captured ? (
          <span className="text-muted-foreground text-xs italic">Costo no capturado</span>
        ) : (
          fmt(p.cost_total, "currency")
        )}
      </td>
      <td className="py-2 px-3 text-right text-sm">
        {p.no_production ? (
          <span className="text-muted-foreground text-xs" title="Costo capturado pero sin CP producidos">
            — <span className="opacity-60 text-[10px]">(sin prod.)</span>
          </span>
        ) : p.cost_not_captured ? (
          <span className="text-muted-foreground">—</span>
        ) : (
          fmt(p.cost_per_cp, "currency")
        )}
      </td>
      <td className="py-2 px-3 text-right text-sm">
        {p.no_production || p.cost_not_captured ? (
          <span className="text-muted-foreground">—</span>
        ) : (
          fmt(p.cost_per_sp, "currency")
        )}
      </td>
      <td className="py-2 px-3 text-right">—</td>
    </tr>
  );
}

function AreaRow({
  area,
  expanded,
  onToggle,
}: {
  area: AreaCostItem;
  expanded: boolean;
  onToggle: () => void;
}) {
  const allUncaptured = area.players.every((p) => p.cost_not_captured);
  return (
    <tr
      className="border-t border-border hover:bg-muted/30 cursor-pointer transition-colors"
      onClick={onToggle}
    >
      <td className="py-3 pl-4 pr-2">
        <div className="flex items-center gap-2">
          {expanded ? (
            <ChevronDown size={14} className="text-muted-foreground shrink-0" />
          ) : (
            <ChevronRight size={14} className="text-muted-foreground shrink-0" />
          )}
          <span className="font-medium text-sm">{area.area}</span>
          <span className="text-xs text-muted-foreground">({area.players_active} devs)</span>
          {allUncaptured && (
            <span className="text-[10px] text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30 rounded px-1">
              sin costos
            </span>
          )}
        </div>
      </td>
      <td className="py-3 px-3 text-center font-semibold text-sm">{area.cp_total}</td>
      <td className="py-3 px-3 text-center text-sm text-muted-foreground">{area.done_subtasks}</td>
      <td className="py-3 px-3 text-right font-medium text-sm">
        {allUncaptured ? (
          <span className="text-muted-foreground text-xs italic">Costo no capturado</span>
        ) : (
          fmt(area.cost_total, "currency")
        )}
      </td>
      <td className="py-3 px-3 text-right font-medium text-sm">
        {area.cost_per_cp !== null ? fmt(area.cost_per_cp, "currency") : "—"}
      </td>
      <td className="py-3 px-3 text-right text-sm">
        {area.cost_per_sp !== null ? fmt(area.cost_per_sp, "currency") : "—"}
      </td>
      <td className="py-3 px-3 text-right">
        <DeltaBadge delta={area.delta_pct} />
      </td>
    </tr>
  );
}

export function CostTable({ areas }: { areas: AreaCostItem[] }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggle = (area: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(area)) next.delete(area);
      else next.add(area);
      return next;
    });
  };

  return (
    <div className="rounded-lg border overflow-hidden">
      <div className="px-4 py-3 border-b bg-muted/30 flex items-center justify-between">
        <h2 className="text-sm font-semibold">Costos por área</h2>
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Info size={12} />
          Haz clic en un área para ver por developer
        </div>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/20">
            <th className="py-2 pl-4 pr-2 text-left text-xs font-medium text-muted-foreground">Área</th>
            <th className="py-2 px-3 text-center text-xs font-medium text-muted-foreground">CP</th>
            <th className="py-2 px-3 text-center text-xs font-medium text-muted-foreground">Tareas</th>
            <th className="py-2 px-3 text-right text-xs font-medium text-muted-foreground">Costo</th>
            <th className="py-2 px-3 text-right text-xs font-medium text-muted-foreground">$/CP</th>
            <th className="py-2 px-3 text-right text-xs font-medium text-muted-foreground">$/SP</th>
            <th className="py-2 px-3 text-right text-xs font-medium text-muted-foreground">Δ trimestre</th>
          </tr>
        </thead>
        <tbody>
          {areas.map((area) => (
            <Fragment key={area.area}>
              <AreaRow
                area={area}
                expanded={expanded.has(area.area)}
                onToggle={() => toggle(area.area)}
              />
              {expanded.has(area.area) &&
                area.players.map((p) => (
                  <PlayerRow key={p.player_id} p={p} />
                ))}
            </Fragment>
          ))}
        </tbody>
      </table>
      {areas.length === 0 && (
        <div className="py-10 text-center text-sm text-muted-foreground">
          Sin datos de producción para este periodo.
        </div>
      )}
    </div>
  );
}
