"use client";

import { useEffect, useState } from "react";
import type { DevDrilldown } from "@/lib/types/pulse";
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

/**
 * CAMBIO 3: drill-down de dev. Al hacer click en un dev, muestra sus tareas
 * en progreso con estatus y días en estado. Para "Equipo de Producto" (cuenta
 * agregada) lista todas las tareas del grupo, etiquetado como tal.
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
                ? `${data.total} tarea${data.total === 1 ? "" : "s"} en progreso${
                    data.area ? ` · ${data.area}` : ""
                  }`
                : "No se pudo cargar el drill-down."}
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[60vh] overflow-auto space-y-1">
          {data && data.tasks.length === 0 && (
            <p className="text-sm text-muted-foreground py-4 text-center">
              Sin tareas en progreso.
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
