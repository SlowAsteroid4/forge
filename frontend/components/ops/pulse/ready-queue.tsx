import type { ReadyQueueItem } from "@/lib/types/pulse";
import { cn } from "@/lib/utils";

interface Props {
  items: ReadyQueueItem[];
}

const PRIORITY_BADGE: Record<string, string> = {
  Highest: "bg-destructive/10 text-destructive border-destructive/30",
  High: "bg-orange-500/10 text-orange-600 border-orange-500/30",
  Medium: "bg-amber-500/10 text-amber-600 border-amber-500/30",
  Low: "bg-muted text-muted-foreground border-border",
  Lowest: "bg-muted text-muted-foreground/60 border-border",
};

export function ReadyQueue({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card p-4 text-center">
        <p className="text-sm text-muted-foreground">Cola Ready vacía</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">#</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Key</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Summary</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Área</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Prioridad</th>
            <th className="text-right px-3 py-2 font-medium text-muted-foreground">CP</th>
            <th className="text-right px-3 py-2 font-medium text-muted-foreground">En Ready</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr key={item.jira_key} className="border-b border-border last:border-0">
              <td className="px-3 py-2 text-muted-foreground/50 tabular-nums">{idx + 1}</td>
              <td className="px-3 py-2 font-mono text-muted-foreground whitespace-nowrap">
                {item.jira_key}
              </td>
              <td className="px-3 py-2 max-w-[260px]">
                <div className="truncate">{item.summary}</div>
                {item.assignee_name && (
                  <div className="text-[10px] text-muted-foreground">{item.assignee_name}</div>
                )}
              </td>
              <td className="px-3 py-2 text-muted-foreground">{item.area}</td>
              <td className="px-3 py-2">
                {item.priority ? (
                  <span
                    className={cn(
                      "inline-block text-[10px] px-1.5 py-0.5 rounded border",
                      PRIORITY_BADGE[item.priority] ?? "bg-muted text-muted-foreground border-border",
                    )}
                  >
                    {item.priority}
                  </span>
                ) : (
                  <span className="text-muted-foreground/40 text-[10px]">—</span>
                )}
              </td>
              <td className="px-3 py-2 text-right tabular-nums font-medium">
                {item.cp ?? <span className="text-muted-foreground/40">—</span>}
              </td>
              <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                {item.tiempo_en_ready_horas}h
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
