import type { DayMovementItem } from "@/lib/types/pulse";

interface Props {
  items: DayMovementItem[];
}

export function DayMovements({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card p-3 text-center">
        <p className="text-sm text-muted-foreground">Sin movimientos en las últimas 24h</p>
      </div>
    );
  }

  const entradas = items.filter((m) => m.to_status === "Ready");
  const salidas = items.filter((m) => m.from_status === "Ready" && m.to_status !== "Done");
  const otros = items.filter(
    (m) => m.to_status !== "Ready" && !(m.from_status === "Ready" && m.to_status !== "Done"),
  );

  return (
    <div className="grid grid-cols-3 gap-3">
      <MovementCol
        title="Entraron a Ready"
        items={entradas}
        emptyMsg="Ninguna"
        accentClass="text-emerald-600"
      />
      <MovementCol
        title="Repriorizaciones (salieron de Ready)"
        items={salidas}
        emptyMsg="Ninguna"
        accentClass="text-amber-600"
        subtitle="Cambios legítimos de prioridad"
      />
      <MovementCol
        title="Otros movimientos"
        items={otros}
        emptyMsg="Ninguno"
        accentClass="text-muted-foreground"
      />
    </div>
  );
}

function MovementCol({
  title,
  items,
  emptyMsg,
  accentClass,
  subtitle,
}: {
  title: string;
  items: DayMovementItem[];
  emptyMsg: string;
  accentClass: string;
  subtitle?: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <p className="text-xs font-semibold mb-0.5">{title}</p>
      {subtitle && <p className="text-[10px] text-muted-foreground mb-1.5">{subtitle}</p>}
      {items.length === 0 ? (
        <p className="text-[11px] text-muted-foreground">{emptyMsg}</p>
      ) : (
        <ul className="space-y-1.5 mt-1.5">
          {items.map((m, i) => (
            <li key={`${m.jira_key}-${i}`} className="text-[11px]">
              <span className={`font-mono ${accentClass}`}>{m.jira_key}</span>
              <span className="text-muted-foreground">
                {" "}
                {m.from_status} → {m.to_status}
              </span>
              {m.assignee_name && (
                <span className="text-muted-foreground/60"> · {m.assignee_name}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
