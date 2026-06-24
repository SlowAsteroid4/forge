import type { FlowCounter } from "@/lib/types/pulse";
import { ZONE_DOT, ZONE_TEXT } from "@/lib/pulse-zones";
import { cn } from "@/lib/utils";

interface Props {
  counters: FlowCounter[];
}

/**
 * CAMBIO 1: franja de contadores por estado en orden de flujo
 * (Backlog → Ready → In Progress → Code Review → Ready for QA → In QA → Done).
 * Cada contador = nº de subtasks en ese paso AHORA. "In Progress" pliega los
 * sub-estados activos (Active/Implementation/In Design/UI Implementation); el
 * tooltip muestra los statuses reales plegados.
 */
export function FlowCountersBar({ counters }: Props) {
  return (
    <div className="flex items-stretch gap-1.5 overflow-x-auto">
      {counters.map((c, i) => (
        <div key={c.key} className="flex items-stretch gap-1.5">
          <div
            className="rounded-lg border border-border bg-card px-3 py-2 min-w-[92px] flex-1"
            title={`Statuses reales: ${c.raw_statuses.join(", ")}`}
          >
            <div className="flex items-center gap-1.5">
              <span className={cn("h-2 w-2 rounded-full flex-shrink-0", ZONE_DOT[c.zone])} />
              <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground truncate">
                {c.label}
              </span>
            </div>
            <p className={cn("text-2xl font-bold tabular-nums mt-0.5", ZONE_TEXT[c.zone])}>
              {c.count}
            </p>
          </div>
          {i < counters.length - 1 && (
            <span className="self-center text-muted-foreground/40 text-xs select-none">→</span>
          )}
        </div>
      ))}
    </div>
  );
}
