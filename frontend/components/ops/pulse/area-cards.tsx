"use client";

import { useState } from "react";
import type { AreaCard, AreaTask } from "@/lib/types/pulse";
import { ZONE_ROW, ZONE_DOT } from "@/lib/pulse-zones";
import { cn } from "@/lib/utils";

interface Props {
  cards: AreaCard[];
  onDevClick: (playerId: number, name: string) => void;
}

/**
 * CAMBIO 2: cards por área (BE/DB/DESIGN/FE).
 * - Card = nº de tareas activas asignadas al área (sin "WIP", sin semáforo).
 * - Click card → expande a cantidad por estado.
 * - Click cantidad-por-estado → lista código + dueño, fila coloreada por estado.
 * - Click en el dueño → drill-down del dev (onDevClick).
 */
export function AreaCards({ cards, onDevClick }: Props) {
  const [openArea, setOpenArea] = useState<string | null>(null);
  const [openStatus, setOpenStatus] = useState<string | null>(null);

  if (cards.length === 0) {
    return <p className="text-sm text-muted-foreground">Sin áreas configuradas o sin actividad.</p>;
  }

  return (
    <div className="grid grid-cols-4 gap-3">
      {cards.map((card) => {
        const isOpen = openArea === card.area;
        const unassigned = card.by_status.reduce(
          (n, g) => n + g.tasks.filter((t) => t.assignee_player_id === null).length,
          0,
        );
        return (
          <div key={card.area} className="rounded-lg border border-border bg-card p-3">
            {/* Header de la card */}
            <button
              type="button"
              className="w-full text-left cursor-pointer"
              onClick={() => {
                setOpenArea(isOpen ? null : card.area);
                setOpenStatus(null);
              }}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-sm">{card.area}</span>
                <span className="text-muted-foreground text-xs">{isOpen ? "▾" : "▸"}</span>
              </div>
              <p className="text-2xl font-bold tabular-nums mt-0.5">
                {card.total_active}
                <span className="text-xs font-normal text-muted-foreground"> activas</span>
              </p>
              {unassigned > 0 && (
                <p className="text-[10px] text-muted-foreground mt-0.5">{unassigned} sin asignar</p>
              )}
            </button>

            {/* Nivel 1: cantidad por estado */}
            {isOpen && (
              <div className="mt-2 pt-2 border-t border-border/50 space-y-1">
                {card.by_status.map((g) => {
                  const statusKey = `${card.area}:${g.status}`;
                  const statusOpen = openStatus === statusKey;
                  return (
                    <div key={statusKey}>
                      <button
                        type="button"
                        className="w-full flex items-center justify-between text-[11px] py-0.5 hover:bg-muted/50 rounded px-1 cursor-pointer"
                        onClick={() => setOpenStatus(statusOpen ? null : statusKey)}
                      >
                        <span className="flex items-center gap-1.5">
                          <span className={cn("h-2 w-2 rounded-full", ZONE_DOT[g.zone])} />
                          {g.status}
                        </span>
                        <span className="tabular-nums font-medium">{g.count}</span>
                      </button>

                      {/* Nivel 2: lista código + dueño (fila coloreada por estado) */}
                      {statusOpen && (
                        <div className="mt-1 space-y-0.5 pl-1">
                          {g.tasks.map((t) => (
                            <TaskRow key={t.jira_key} task={t} onDevClick={onDevClick} />
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function TaskRow({
  task,
  onDevClick,
}: {
  task: AreaTask;
  onDevClick: (playerId: number, name: string) => void;
}) {
  return (
    <div
      className={cn(
        "border-l-2 rounded-r px-1.5 py-1 text-[11px] leading-tight",
        ZONE_ROW[task.zone],
      )}
    >
      <span className="font-mono text-muted-foreground">{task.jira_key}</span>
      <div className="truncate text-foreground/80" title={task.summary}>
        {task.assignee_player_id !== null ? (
          <button
            type="button"
            className="hover:underline cursor-pointer text-left"
            onClick={() => onDevClick(task.assignee_player_id!, task.assignee_name ?? "")}
          >
            {task.assignee_name}
            {task.is_aggregate_team && (
              <span className="text-muted-foreground italic"> (equipo agregado)</span>
            )}
          </button>
        ) : (
          <span className="text-muted-foreground italic">Sin asignar</span>
        )}
      </div>
    </div>
  );
}
