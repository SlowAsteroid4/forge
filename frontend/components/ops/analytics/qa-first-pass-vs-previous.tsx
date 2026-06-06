import type { DevQaVsPrevious, QaFirstPassVsPreviousResponse } from "@/lib/types/analytics";
import { cn } from "@/lib/utils";

interface Props {
  data: QaFirstPassVsPreviousResponse;
}

function barColor(pct: number): string {
  if (pct >= 80) return "#4ADE80";
  if (pct >= 50) return "#FCD34D";
  return "#F87171";
}

function DeltaPts({ dev }: { dev: DevQaVsPrevious }) {
  if (dev.previous_pct === null || dev.delta_pts === null) {
    return <span className="text-[11px] text-muted-foreground">sin comparativa</span>;
  }
  const flat = dev.delta_pts === 0;
  const up = dev.delta_pts > 0;
  return (
    <span
      className={cn(
        "text-[11px] font-medium tabular-nums",
        flat && "text-muted-foreground",
        !flat && up && "text-emerald-600",
        !flat && !up && "text-red-500",
      )}
      title={`Ciclo anterior: ${dev.previous_pct}%`}
    >
      {flat ? "→" : up ? "▲" : "▼"} {dev.delta_pts > 0 ? "+" : ""}
      {dev.delta_pts} pts
    </span>
  );
}

export function QaFirstPassVsPrevious({ data }: Props) {
  const devs = data.devs.filter((d) => d.total > 0);

  if (!devs.length) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        Sin datos de QA para este ciclo.
      </p>
    );
  }

  return (
    <div className="space-y-2.5">
      {devs.map((dev) => {
        const name = dev.display_name.split(" ").slice(0, 2).join(" ");
        return (
          <div key={dev.player_id} className="flex items-center gap-3 text-xs">
            <div className="w-32 shrink-0 truncate" title={`${dev.display_name} · ${dev.area}`}>
              {name}
            </div>
            <div className="relative flex-1 h-5 rounded bg-muted overflow-hidden">
              <div
                className="h-full rounded-l transition-all"
                style={{ width: `${dev.first_pass_pct}%`, backgroundColor: barColor(dev.first_pass_pct) }}
              />
              {/* Marcador del ciclo anterior */}
              {dev.previous_pct !== null && (
                <div
                  className="absolute top-0 h-full border-l-2 border-dashed border-foreground/50"
                  style={{ left: `${dev.previous_pct}%` }}
                  title={`Anterior: ${dev.previous_pct}%`}
                />
              )}
            </div>
            <div className="w-14 shrink-0 text-right font-medium tabular-nums">
              {dev.first_pass_pct}%
            </div>
            <div className="w-28 shrink-0 text-right">
              <DeltaPts dev={dev} />
            </div>
          </div>
        );
      })}
      <p className="text-[10px] text-muted-foreground pt-1">
        Barra = % first-pass del ciclo de referencia
        {data.reference_cycle ? ` (${data.reference_cycle.name})` : ""}. Línea punteada = ciclo
        anterior{data.previous_cycle ? ` (${data.previous_cycle.name})` : ""}.
      </p>
    </div>
  );
}
