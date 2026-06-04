import type { PulseGlobals } from "@/lib/types/pulse";
import { cn } from "@/lib/utils";

interface Props {
  globals: PulseGlobals;
}

export function PulseGlobalsBar({ globals }: Props) {
  const metrics = [
    { label: "Activas", value: globals.activas, highlight: false },
    {
      label: "Bloqueadas",
      value: globals.bloqueadas,
      highlight: globals.bloqueadas > 0,
      danger: true,
    },
    {
      label: "En espera",
      value: "—",
      subtitle: "no disponible",
      highlight: false,
    },
    { label: "Cola Ready", value: globals.cola_ready, highlight: false },
    {
      label: "Aging máx",
      value: `${globals.aging_max_dias_habiles}d`,
      highlight: globals.aging_max_dias_habiles >= 5,
      warn: true,
    },
  ];

  return (
    <div className="grid grid-cols-5 gap-3">
      {metrics.map((m) => (
        <div
          key={m.label}
          className={cn(
            "rounded-lg border border-border bg-card p-3",
            m.highlight && m.danger && "border-destructive/60 bg-destructive/5",
            m.highlight && m.warn && !m.danger && "border-amber-500/60 bg-amber-500/5",
          )}
        >
          <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            {m.label}
          </p>
          <p
            className={cn(
              "text-2xl font-bold tabular-nums mt-0.5",
              m.highlight && m.danger && "text-destructive",
              m.highlight && m.warn && !m.danger && "text-amber-500",
            )}
          >
            {m.value}
          </p>
          {m.subtitle && (
            <p className="text-[10px] text-muted-foreground/60 mt-0.5">{m.subtitle}</p>
          )}
        </div>
      ))}
    </div>
  );
}
