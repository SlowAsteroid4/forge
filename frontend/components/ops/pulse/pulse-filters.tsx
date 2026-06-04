"use client";

import { useState } from "react";

const AREAS = ["BE", "FE", "Design", "DB", "QA"];

interface Filters {
  areas: string[];
  projectCode: string | null;
  playerId: string | null;
}

interface Props {
  filters: Filters;
  onChange: (f: Filters) => void;
}

export function PulseFilters({ filters, onChange }: Props) {
  const [open, setOpen] = useState(false);

  const toggleArea = (area: string) => {
    const next = filters.areas.includes(area)
      ? filters.areas.filter((a) => a !== area)
      : [...filters.areas, area];
    onChange({ ...filters, areas: next });
  };

  const hasActive = filters.areas.length > 0 || !!filters.projectCode || !!filters.playerId;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={`text-xs px-3 py-1.5 rounded border transition-colors ${
          hasActive
            ? "border-primary text-primary bg-primary/5"
            : "border-border text-muted-foreground hover:border-foreground/30"
        }`}
      >
        Filtros {hasActive ? `(activos)` : ""}
      </button>

      {open && (
        <div className="absolute right-0 top-9 z-50 w-56 rounded-lg border border-border bg-popover shadow-md p-3 space-y-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
              Área
            </p>
            <div className="flex flex-wrap gap-1.5">
              {AREAS.map((a) => (
                <button
                  key={a}
                  onClick={() => toggleArea(a)}
                  className={`text-[11px] px-2 py-0.5 rounded border transition-colors ${
                    filters.areas.includes(a)
                      ? "border-primary text-primary bg-primary/10"
                      : "border-border text-muted-foreground hover:border-foreground/30"
                  }`}
                >
                  {a}
                </button>
              ))}
            </div>
          </div>

          {hasActive && (
            <button
              onClick={() => {
                onChange({ areas: [], projectCode: null, playerId: null });
                setOpen(false);
              }}
              className="text-[11px] text-muted-foreground hover:text-foreground underline"
            >
              Limpiar filtros
            </button>
          )}

          <button
            onClick={() => setOpen(false)}
            className="w-full text-[11px] px-2 py-1 rounded border border-border text-muted-foreground hover:bg-accent/50"
          >
            Cerrar
          </button>
        </div>
      )}
    </div>
  );
}
