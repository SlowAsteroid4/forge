"use client";

import { useState } from "react";
import type { WipAreaCard } from "@/lib/types/pulse";
import { cn } from "@/lib/utils";

interface Props {
  cards: WipAreaCard[];
}

const SEMAFORO_STYLES = {
  verde: "border-emerald-500/60 bg-emerald-500/5",
  amarillo: "border-amber-500/60 bg-amber-500/5",
  rojo: "border-destructive/60 bg-destructive/5",
};

const SEMAFORO_DOT = {
  verde: "bg-emerald-500",
  amarillo: "bg-amber-500",
  rojo: "bg-destructive",
};

const SEMAFORO_TEXT = {
  verde: "text-emerald-600",
  amarillo: "text-amber-600",
  rojo: "text-destructive",
};

export function WipByArea({ cards }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (cards.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Sin límites WIP configurados o no hay actividad.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-4 gap-3">
      {cards.map((card) => (
        <div
          key={card.area}
          className={cn(
            "rounded-lg border p-3 cursor-pointer transition-colors",
            SEMAFORO_STYLES[card.semaforo],
          )}
          onClick={() => setExpanded(expanded === card.area ? null : card.area)}
        >
          {/* Header del card */}
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-sm">{card.area}</span>
            <span
              className={cn(
                "h-2 w-2 rounded-full flex-shrink-0",
                SEMAFORO_DOT[card.semaforo],
              )}
            />
          </div>

          {/* WIP por dev (señal principal) */}
          <p className={cn("text-xl font-bold tabular-nums", SEMAFORO_TEXT[card.semaforo])}>
            {card.max_wip_individual}
            <span className="text-xs font-normal text-muted-foreground">
              {" "}/ {card.wip_limit} límite/dev
            </span>
          </p>

          {/* Devs sobre el límite */}
          {card.devs_over_limit > 0 ? (
            <p className="text-[11px] text-destructive mt-0.5 font-medium">
              {card.devs_over_limit} dev{card.devs_over_limit > 1 ? "s" : ""} excede
              {card.devs_over_limit > 1 ? "n" : ""} su límite
            </p>
          ) : (
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {card.assignee_count} dev{card.assignee_count !== 1 ? "s" : ""} ·{" "}
              {card.wip_actual} activas total
            </p>
          )}

          {/* Detalle expandible */}
          {expanded === card.area && card.activas.length > 0 && (
            <div className="mt-2 pt-2 border-t border-border/50 space-y-1">
              {card.activas.map((t) => (
                <div key={t.jira_key} className="text-[11px]">
                  <span className="font-mono text-muted-foreground">{t.jira_key}</span>{" "}
                  <span className="text-foreground/80 truncate block">
                    {t.assignee_name ?? "Sin asignee"} — {t.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
