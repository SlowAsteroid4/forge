import type { DeltaMetric, QualitySummaryResponse } from "@/lib/types/analytics";
import { cn } from "@/lib/utils";

interface QualityCardsProps {
  data: QualitySummaryResponse;
}

interface CardSpec {
  key: keyof Pick<QualitySummaryResponse, "tested" | "pending" | "avg_qa_hours">;
  label: string;
  hint: string;
  unit?: string;
  /** true ⇒ subir es bueno (verde). false ⇒ subir es malo (rojo). */
  higherIsBetter: boolean;
  decimals?: number;
}

const CARDS: CardSpec[] = [
  {
    key: "tested",
    label: "Probadas",
    hint: "Done que pasaron por QA en el ciclo",
    higherIsBetter: true,
  },
  {
    key: "pending",
    label: "Por probar",
    hint: "En cola de QA ahora (In QA / Ready for QA)",
    higherIsBetter: false,
  },
  {
    key: "avg_qa_hours",
    label: "Tiempo prom. en QA",
    hint: "Horas hábiles promedio en QA (tiempo de Edgar)",
    unit: "h",
    higherIsBetter: false,
    decimals: 1,
  },
];

function fmt(n: number, decimals = 0): string {
  return n.toLocaleString("es-MX", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function DeltaBadge({ metric, higherIsBetter }: { metric: DeltaMetric; higherIsBetter: boolean }) {
  if (metric.delta_abs === null) {
    return <span className="text-[11px] text-muted-foreground">sin comparativa</span>;
  }
  const up = metric.delta_abs > 0;
  const flat = metric.delta_abs === 0;
  const good = flat ? null : up === higherIsBetter;
  const arrow = flat ? "→" : up ? "▲" : "▼";
  const pct = metric.delta_pct !== null ? ` ${metric.delta_pct > 0 ? "+" : ""}${metric.delta_pct}%` : "";

  return (
    <span
      className={cn(
        "text-[11px] font-medium tabular-nums",
        good === null && "text-muted-foreground",
        good === true && "text-emerald-600",
        good === false && "text-red-500",
      )}
    >
      {arrow} {metric.delta_abs > 0 ? "+" : ""}
      {fmt(metric.delta_abs, Math.abs(metric.delta_abs) % 1 === 0 ? 0 : 1)}
      {pct}
      <span className="text-muted-foreground font-normal"> vs anterior</span>
    </span>
  );
}

export function QualityCards({ data }: QualityCardsProps) {
  const refLabel = data.reference_cycle
    ? `${data.reference_cycle.name}`
    : "—";
  const prevLabel = data.previous_cycle ? ` · anterior: ${data.previous_cycle.name}` : "";

  return (
    <div>
      <p className="text-[11px] text-muted-foreground mb-2">
        Ciclo de referencia: <span className="font-medium text-foreground">{refLabel}</span>
        {prevLabel}
      </p>
      <div className="grid grid-cols-3 gap-4">
        {CARDS.map((spec) => {
          const metric = data[spec.key];
          return (
            <div key={spec.key} className="rounded-lg border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">{spec.label}</p>
              <p className="mt-1 text-2xl font-bold tabular-nums">
                {fmt(metric.current, spec.decimals ?? 0)}
                {spec.unit && <span className="text-base font-normal text-muted-foreground"> {spec.unit}</span>}
              </p>
              <div className="mt-1">
                <DeltaBadge metric={metric} higherIsBetter={spec.higherIsBetter} />
              </div>
              <p className="mt-2 text-[10px] text-muted-foreground leading-tight">{spec.hint}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
