"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { PulseSnapshot } from "@/lib/types/pulse";
import { FlowCountersBar } from "./flow-counters-bar";
import { AreaCards } from "./area-cards";
import { DevDrilldownPanel } from "./dev-drilldown";
import { BlocksTable } from "./blocks-table";
import { DayMovements } from "./day-movements";
import { AgingTable } from "./aging-table";
import { ReadyQueue } from "./ready-queue";
import { PulseFilters } from "./pulse-filters";
import { PulseExport } from "./pulse-export";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
const REFRESH_INTERVAL_S = 60;

interface Filters {
  areas: string[];
  projectCode: string | null;
  playerId: string | null;
}

interface Props {
  initialPulse: PulseSnapshot | null;
  initialFilters: Filters;
}

export function PulseClient({ initialPulse, initialFilters }: Props) {
  const [pulse, setPulse] = useState<PulseSnapshot | null>(initialPulse);
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [secondsAgo, setSecondsAgo] = useState(0);
  const [loading, setLoading] = useState(false);
  const [drilldown, setDrilldown] = useState<{ playerId: number; name: string } | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const counterRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchPulse = useCallback(async (f: Filters) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      for (const a of f.areas) params.append("area", a);
      if (f.projectCode) params.set("project_code", f.projectCode);
      if (f.playerId) params.set("player_id", f.playerId);
      const query = params.toString() ? `?${params}` : "";
      const res = await fetch(`${API_BASE}/pulse/now${query}`, { cache: "no-store" });
      if (res.ok) {
        const data = (await res.json()) as PulseSnapshot;
        setPulse(data);
        setSecondsAgo(0);
      }
    } catch {
      // mantener el snapshot anterior si falla
    } finally {
      setLoading(false);
    }
  }, []);

  // Refresh automático cada 60s
  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = setInterval(() => fetchPulse(filters), REFRESH_INTERVAL_S * 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [filters, fetchPulse]);

  // Contador de "actualizado hace X segundos"
  useEffect(() => {
    if (counterRef.current) clearInterval(counterRef.current);
    counterRef.current = setInterval(() => setSecondsAgo((s) => s + 1), 1000);
    return () => {
      if (counterRef.current) clearInterval(counterRef.current);
    };
  }, [pulse]);

  const handleFilterChange = (newFilters: Filters) => {
    setFilters(newFilters);
    fetchPulse(newFilters);
  };

  const generatedAt = pulse?.generated_at
    ? new Date(pulse.generated_at).toLocaleTimeString("es-MX", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      })
    : null;

  return (
    <div className="flex flex-col flex-1 overflow-auto" id="pulse-root">
      {/* Header */}
      <div className="border-b border-border px-6 py-3 flex items-center justify-between gap-4 bg-background">
        <div>
          <h1 className="text-base font-semibold">Pulso Operativo</h1>
          <p className="text-xs text-muted-foreground">
            Vista en tiempo real del trabajo del equipo — se refresca automáticamente cada 60s
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Timestamp */}
          <span className="text-[11px] text-muted-foreground tabular-nums">
            {generatedAt
              ? `Actualizado hace ${secondsAgo}s (${generatedAt})`
              : "Cargando..."}
            {loading && " ↻"}
          </span>
          <PulseExport />
          <PulseFilters filters={filters} onChange={handleFilterChange} />
        </div>
      </div>

      {pulse === null ? (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-muted-foreground">
            No se pudo cargar el Pulso. Verifica que el backend esté corriendo.
          </p>
        </div>
      ) : (
        <div className="flex-1 p-5 space-y-5 overflow-auto">
          {/* CAMBIO 1: franja de contadores por estado (orden de flujo) */}
          <FlowCountersBar counters={pulse.flow_counters} />

          {/* CAMBIO 2: cards por área */}
          <section>
            <h2 className="text-sm font-semibold mb-2">Tareas por área</h2>
            <AreaCards
              cards={pulse.area_cards}
              onDevClick={(playerId, name) => setDrilldown({ playerId, name })}
            />
          </section>

          {/* C + E: Bloqueos + Aging (lado a lado) */}
          <div className="grid grid-cols-2 gap-4">
            <section>
              <h2 className="text-sm font-semibold mb-2">
                Bloqueos{" "}
                {pulse.blocks.length > 0 && (
                  <span className="text-destructive">({pulse.blocks.length})</span>
                )}
              </h2>
              <BlocksTable items={pulse.blocks} />
            </section>
            <section>
              <h2 className="text-sm font-semibold mb-2">
                Aging crítico{" "}
                {pulse.aging_critical.length > 0 && (
                  <span className="text-amber-500">({pulse.aging_critical.length})</span>
                )}
              </h2>
              <AgingTable items={pulse.aging_critical} />
            </section>
          </div>

          {/* D: Movimientos del día */}
          <section>
            <h2 className="text-sm font-semibold mb-2">Movimientos (últimas 24h)</h2>
            <DayMovements items={pulse.day_movements} />
          </section>

          {/* F: Cola Ready */}
          <section>
            <h2 className="text-sm font-semibold mb-2">
              Cola Ready{" "}
              <span className="text-muted-foreground font-normal text-xs">
                (top 10 por prioridad + antigüedad)
              </span>
            </h2>
            <ReadyQueue items={pulse.ready_queue} />
          </section>
        </div>
      )}

      {/* CAMBIO 3: drill-down de dev (panel) */}
      <DevDrilldownPanel
        playerId={drilldown?.playerId ?? null}
        fallbackName={drilldown?.name ?? ""}
        open={drilldown !== null}
        onOpenChange={(o) => {
          if (!o) setDrilldown(null);
        }}
      />
    </div>
  );
}
