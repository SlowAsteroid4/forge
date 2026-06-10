"use client";

import { useEffect, useState } from "react";
import type { DevDrilldown, WipSemaphore } from "@/lib/types/pulse";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ZONE_ROW, ZONE_DOT } from "@/lib/pulse-zones";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

interface Props {
  playerId: number | null;
  fallbackName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// WP-20: colores de semáforo (solo el WIP dispara color)
const SEMAPHORE_BG: Record<WipSemaphore, string> = {
  green: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  yellow: "bg-yellow-400/20 text-yellow-700 dark:text-yellow-400",
  red: "bg-red-500/15 text-red-700 dark:text-red-400",
};

const SEMAPHORE_DOT: Record<WipSemaphore, string> = {
  green: "bg-emerald-500",
  yellow: "bg-yellow-400",
  red: "bg-red-500",
};

function WipBar({ summary }: { summary: DevDrilldown["wip_summary"] }) {
  const cols = [
    { label: "WIP", value: summary.wip, isWip: true },
    { label: "Review", value: summary.review, isWip: false },
    { label: "QA", value: summary.qa, isWip: false },
    { label: "Waiting", value: summary.waiting, isWip: false },
    { label: "Ready", value: summary.ready, isWip: false },
  ];

  return (
    <div className="mt-3 mb-2 rounded-lg border border-border bg-muted/40 p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
          WIP vs límite ({summary.wip_limit})
        </span>
        <span
          className={cn(
            "flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full",
            SEMAPHORE_BG[summary.semaphore],
          )}
        >
          <span className={cn("h-1.5 w-1.5 rounded-full", SEMAPHORE_DOT[summary.semaphore])} />
          {summary.wip} / {summary.wip_limit}
        </span>
      </div>
      <div className="grid grid-cols-5 gap-1">
        {cols.map(({ label, value, isWip }) => (
          <div
            key={label}
            className={cn(
              "flex flex-col items-center rounded px-1 py-1.5",
              isWip
                ? cn("font-semibold", SEMAPHORE_BG[summary.semaphore])
                : "text-muted-foreground",
            )}
          >
            <span className="text-base tabular-nums leading-none">{value}</span>
            <span className="text-[9px] mt-0.5 uppercase tracking-wide">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * CAMBIO 3 + WP-20: drill-down de dev con WIP canónico y semáforo.
 * Solo la columna "WIP" (In Progress + In Code) lleva color de semáforo.
 * Las demás columnas son informativas, sin color de límite.
 */
export function DevDrilldownPanel({ playerId, fallbackName, open, onOpenChange }: Props) {
  const [data, setData] = useState<DevDrilldown | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || playerId === null) return;
    setLoading(true);
    setData(null);
    fetch(`${API_BASE}/pulse/dev/${playerId}`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d: DevDrilldown | null) => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [open, playerId]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {data?.display_name ?? fallbackName}
            {data?.is_aggregate_team && (
              <span className="text-xs font-normal text-muted-foreground italic">
                (equipo agregado)
              </span>
            )}
          </DialogTitle>
          <DialogDescription>
            {loading
              ? "Cargando tareas…"
              : data
                ? `${data.total} tarea${data.total === 1 ? "" : "s"} operativa${data.total === 1 ? "" : "s"}${
                    data.area ? ` · ${data.area}` : ""
                  }`
                : "No se pudo cargar el drill-down."}
          </DialogDescription>
        </DialogHeader>

        {/* WP-20: barra de WIP con semáforo */}
        {data && <WipBar summary={data.wip_summary} />}

        <div className="max-h-[50vh] overflow-auto space-y-1">
          {data && data.tasks.length === 0 && (
            <p className="text-sm text-muted-foreground py-4 text-center">
              Sin tareas operativas.
            </p>
          )}
          {data?.tasks.map((t) => (
            <div
              key={t.jira_key}
              className={cn("border-l-2 rounded-r px-2 py-1.5", ZONE_ROW[t.zone])}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-[11px] text-muted-foreground">{t.jira_key}</span>
                <span className="flex items-center gap-1.5 text-[11px]">
                  <span className={cn("h-2 w-2 rounded-full", ZONE_DOT[t.zone])} />
                  {t.status}
                  <span className="text-muted-foreground tabular-nums">· {t.dias_en_estado}d</span>
                </span>
              </div>
              <p className="text-xs text-foreground/80 truncate mt-0.5" title={t.summary}>
                {t.summary}
              </p>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
