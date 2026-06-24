"use client";

import { useState } from "react";
import type { AgingItem } from "@/lib/types/pulse";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

interface Props {
  items: AgingItem[];
}

export function AgingTable({ items }: Props) {
  const [flagged, setFlagged] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState<string | null>(null);

  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-card p-4 text-center">
        <p className="text-sm text-muted-foreground">Sin subtasks con aging crítico (&gt;5 días)</p>
      </div>
    );
  }

  const handleFlag = async (jiraKey: string) => {
    if (flagged[jiraKey] || loading) return;
    setLoading(jiraKey);
    try {
      const res = await fetch(`${API_BASE}/pulse/flag/${jiraKey}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note: "Marcada desde Pulso Operativo — aging crítico" }),
      });
      if (res.ok) {
        setFlagged((prev) => ({ ...prev, [jiraKey]: true }));
      }
    } catch {
      // silencioso — el botón vuelve a quedar disponible
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Key</th>
            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Summary</th>
            <th className="text-right px-3 py-2 font-medium text-muted-foreground">En estado</th>
            <th className="text-right px-3 py-2 font-medium text-muted-foreground">Edad total</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.jira_key}
              className="border-b border-border last:border-0"
            >
              <td className="px-3 py-2 font-mono text-muted-foreground whitespace-nowrap">
                {item.jira_key}
              </td>
              <td className="px-3 py-2 max-w-[170px]">
                <div className="truncate">{item.summary}</div>
                <div className="text-[10px] text-muted-foreground">
                  {item.assignee_name ?? "Sin asignee"} · {item.status}
                </div>
              </td>
              <td
                className={cn(
                  "px-3 py-2 text-right tabular-nums font-medium",
                  item.dias_en_estado >= 10 ? "text-destructive" : "text-amber-500",
                )}
              >
                {item.dias_en_estado}d
              </td>
              <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                {item.edad_total_dias}d
              </td>
              <td className="px-3 py-2 text-right">
                <button
                  onClick={() => handleFlag(item.jira_key)}
                  disabled={!!flagged[item.jira_key] || loading === item.jira_key}
                  className={cn(
                    "text-[10px] px-2 py-0.5 rounded border transition-colors",
                    flagged[item.jira_key]
                      ? "border-emerald-500 text-emerald-600 cursor-default"
                      : "border-border text-muted-foreground hover:border-amber-500 hover:text-amber-600 disabled:opacity-50",
                  )}
                >
                  {flagged[item.jira_key]
                    ? "✓ Marcada"
                    : loading === item.jira_key
                      ? "..."
                      : "Marcar para revisión"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
