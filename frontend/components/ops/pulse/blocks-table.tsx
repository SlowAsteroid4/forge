import type { BlockItem } from "@/lib/types/pulse";
import { cn } from "@/lib/utils";

interface Props {
  items: BlockItem[];
}

export function BlocksTable({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card p-4 text-center">
        <p className="text-sm text-muted-foreground">Sin bloqueos activos</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Key</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Summary</th>
            <th className="text-right px-3 py-2 font-medium text-muted-foreground">Horas</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Razón</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.jira_key}
              className={cn(
                "border-b border-border last:border-0",
                item.es_critico && "bg-destructive/5",
              )}
            >
              <td className="px-3 py-2 font-mono text-muted-foreground whitespace-nowrap">
                {item.es_critico && <span className="mr-1">🚨</span>}
                {item.jira_key}
              </td>
              <td className="px-3 py-2 max-w-[200px]">
                <div className="truncate">{item.summary}</div>
                {item.assignee_name && (
                  <div className="text-[10px] text-muted-foreground">{item.assignee_name}</div>
                )}
              </td>
              <td
                className={cn(
                  "px-3 py-2 text-right tabular-nums font-medium",
                  item.es_critico ? "text-destructive" : "text-amber-500",
                )}
              >
                {item.horas_bloqueado}h
              </td>
              <td className="px-3 py-2 text-muted-foreground/60 italic">
                {item.block_reason ?? "no disponible"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
