"use client";

import { useMemo } from "react";
import type { EpicForecastItem } from "@/lib/types/forecast";

interface ForecastTimelineProps {
  epics: EpicForecastItem[];
}

const SCENARIO_COLORS = {
  optimistic: "#16a34a",
  realistic: "#2563eb",
  conservative: "#ea580c",
};

function parseDate(dateStr: string | null): Date | null {
  if (!dateStr) return null;
  return new Date(dateStr + "T00:00:00");
}

function formatTick(d: Date): string {
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short" });
}

export function ForecastTimeline({ epics }: ForecastTimelineProps) {
  const withCP = useMemo(() => epics.filter((e) => e.cp_total > 0), [epics]);

  const allDates = useMemo(() => {
    const dates: Date[] = [new Date()];
    for (const e of withCP) {
      if (e.date_optimistic) dates.push(parseDate(e.date_optimistic)!);
      if (e.date_conservative) dates.push(parseDate(e.date_conservative)!);
    }
    return dates;
  }, [withCP]);

  const minDate = useMemo(() => new Date(Math.min(...allDates.map((d) => d.getTime()))), [allDates]);
  const maxDate = useMemo(
    () => new Date(Math.max(...allDates.map((d) => d.getTime()))),
    [allDates],
  );

  const totalMs = Math.max(maxDate.getTime() - minDate.getTime(), 7 * 24 * 3600 * 1000);

  function pct(d: Date): number {
    return ((d.getTime() - minDate.getTime()) / totalMs) * 100;
  }

  // Generate monthly ticks
  const ticks = useMemo(() => {
    const result: Date[] = [];
    const cursor = new Date(minDate.getFullYear(), minDate.getMonth(), 1);
    while (cursor <= maxDate) {
      result.push(new Date(cursor));
      cursor.setMonth(cursor.getMonth() + 1);
    }
    return result;
  }, [minDate, maxDate]);

  if (withCP.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        Sin épicas con CP estimado para mostrar en el timeline
      </div>
    );
  }

  const today = new Date();
  const todayPct = pct(today);

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[600px] px-4 py-2">
        {/* Month ticks */}
        <div className="relative h-6 mb-1 border-b border-border">
          {ticks.map((t) => (
            <div
              key={t.toISOString()}
              className="absolute top-0 text-[10px] text-muted-foreground"
              style={{ left: `${pct(t)}%` }}
            >
              {formatTick(t)}
            </div>
          ))}
          {/* Today line */}
          <div
            className="absolute top-0 bottom-0 w-px bg-foreground/50"
            style={{ left: `${todayPct}%` }}
          />
        </div>

        {/* Epic rows */}
        {withCP.map((e) => {
          const optD = parseDate(e.date_optimistic);
          const realD = parseDate(e.date_realistic);
          const consD = parseDate(e.date_conservative);
          if (!optD || !realD || !consD) return null;

          const optPct = pct(optD);
          const realPct = pct(realD);
          const consPct = pct(consD);

          return (
            <div key={e.epic_key} className="relative h-8 flex items-center mb-1 group">
              {/* Range bar: optimistic → conservative */}
              <div
                className="absolute h-2 rounded-full opacity-20 bg-blue-500"
                style={{
                  left: `${optPct}%`,
                  width: `${Math.max(consPct - optPct, 0.5)}%`,
                }}
              />
              {/* Dot optimistic */}
              <div
                className="absolute w-2 h-2 rounded-full border-2 border-white"
                style={{ left: `${optPct}%`, transform: "translate(-50%, 0)", backgroundColor: SCENARIO_COLORS.optimistic }}
                title={`Optimista: ${e.date_optimistic}`}
              />
              {/* Dot realistic */}
              <div
                className="absolute w-3 h-3 rounded-full border-2 border-white shadow"
                style={{ left: `${realPct}%`, transform: "translate(-50%, 0)", backgroundColor: SCENARIO_COLORS.realistic }}
                title={`Realista: ${e.date_realistic}`}
              />
              {/* Dot conservative */}
              <div
                className="absolute w-2 h-2 rounded-full border-2 border-white"
                style={{ left: `${consPct}%`, transform: "translate(-50%, 0)", backgroundColor: SCENARIO_COLORS.conservative }}
                title={`Conservador: ${e.date_conservative}`}
              />
              {/* Label */}
              <div className="absolute right-0 text-[10px] text-muted-foreground truncate max-w-[160px] pl-1 pr-0">
                {e.epic_key}
                {e.preliminary && <span className="text-orange-500 ml-0.5">*</span>}
              </div>
            </div>
          );
        })}

        {/* Legend */}
        <div className="flex gap-4 mt-3 text-[10px] text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full" style={{ background: SCENARIO_COLORS.optimistic }} />
            Optimista
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full" style={{ background: SCENARIO_COLORS.realistic }} />
            Realista
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full" style={{ background: SCENARIO_COLORS.conservative }} />
            Conservador
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-px h-3 bg-foreground/50" />
            Hoy
          </span>
        </div>
      </div>
    </div>
  );
}
