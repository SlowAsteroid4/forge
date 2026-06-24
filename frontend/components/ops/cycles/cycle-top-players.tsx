"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import type { TopPlayer } from "@/lib/types/cycle-close";

interface Props {
  players: TopPlayer[];
  jiraBaseUrl: string | null;
}

function fmt(n: number | null): string {
  return n == null ? "—" : n.toFixed(1);
}

function signed(n: number): string {
  return `${n >= 0 ? "+" : ""}${n.toFixed(1)}`;
}

export function CycleTopPlayers({ players, jiraBaseUrl }: Props) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  function toggle(playerId: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(playerId)) next.delete(playerId);
      else next.add(playerId);
      return next;
    });
  }

  return (
    <div className="rounded-md border border-border overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted/30">
          <tr>
            <th className="px-4 py-2 text-left font-medium text-muted-foreground w-8" />
            <th className="px-4 py-2 text-left font-medium text-muted-foreground">
              #
            </th>
            <th className="px-4 py-2 text-left font-medium text-muted-foreground">
              Player
            </th>
            <th className="px-4 py-2 text-left font-medium text-muted-foreground">
              Área
            </th>
            <th className="px-4 py-2 text-right font-medium text-muted-foreground">
              SP
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {players.map((p, i) => {
            const isOpen = expanded.has(p.player_id);
            const hasDetail =
              p.por_issue.length > 0 || p.ajustes_no_issue.length > 0;
            return (
              <ExpandableRow
                key={p.player_id}
                player={p}
                index={i}
                isOpen={isOpen}
                hasDetail={hasDetail}
                jiraBaseUrl={jiraBaseUrl}
                onToggle={() => toggle(p.player_id)}
              />
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ExpandableRow({
  player: p,
  index: i,
  isOpen,
  hasDetail,
  jiraBaseUrl,
  onToggle,
}: {
  player: TopPlayer;
  index: number;
  isOpen: boolean;
  hasDetail: boolean;
  jiraBaseUrl: string | null;
  onToggle: () => void;
}) {
  return (
    <>
      <tr
        className={hasDetail ? "cursor-pointer hover:bg-accent/30" : ""}
        onClick={hasDetail ? onToggle : undefined}
      >
        <td className="px-4 py-2 text-muted-foreground tabular-nums text-center">
          {hasDetail ? (isOpen ? "▾" : "▸") : ""}
        </td>
        <td className="px-4 py-2 text-muted-foreground tabular-nums">{i + 1}</td>
        <td className="px-4 py-2 font-medium">{p.display_name}</td>
        <td className="px-4 py-2">
          <Badge variant="outline" className="text-xs">
            {p.area}
          </Badge>
        </td>
        <td className="px-4 py-2 text-right tabular-nums font-mono text-sm">
          {p.sp.toFixed(1)}
        </td>
      </tr>
      {isOpen && hasDetail && (
        <tr className="bg-muted/20">
          <td />
          <td colSpan={4} className="px-4 py-3">
            <div className="space-y-3">
              {p.por_issue.length > 0 && (
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-muted-foreground">
                      <th className="text-left font-medium py-1">Issue</th>
                      <th className="text-left font-medium py-1">Título</th>
                      <th className="text-right font-medium py-1 w-12">CP</th>
                      <th className="text-right font-medium py-1 w-16">SP</th>
                    </tr>
                  </thead>
                  <tbody>
                    {p.por_issue.map((it) => (
                      <tr key={it.jira_key} className="border-t border-border/50">
                        <td className="py-1 pr-2">
                          {jiraBaseUrl ? (
                            <a
                              href={`${jiraBaseUrl}/browse/${it.jira_key}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-mono text-primary hover:underline"
                            >
                              {it.jira_key} ↗
                            </a>
                          ) : (
                            <code className="font-mono select-all">
                              {it.jira_key}
                            </code>
                          )}
                        </td>
                        <td className="py-1 pr-2 text-muted-foreground truncate max-w-xs">
                          {it.title}
                        </td>
                        <td className="py-1 text-right tabular-nums">
                          {it.cp ?? "—"}
                        </td>
                        <td className="py-1 text-right tabular-nums font-mono">
                          {fmt(it.sp_final)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {p.ajustes_no_issue.length > 0 && (
                <ul className="space-y-1 text-xs">
                  {p.ajustes_no_issue.map((adj, idx) => (
                    <li
                      key={idx}
                      className="flex justify-between border-t border-border/50 py-1"
                    >
                      <span className="text-muted-foreground">{adj.label}</span>
                      <span
                        className={[
                          "tabular-nums font-mono",
                          adj.amount_sp >= 0 ? "text-green-600" : "text-destructive",
                        ].join(" ")}
                      >
                        {signed(adj.amount_sp)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}

              <div className="flex justify-between text-xs font-medium border-t border-border pt-1.5">
                <span className="text-muted-foreground">Total del ciclo</span>
                <span className="tabular-nums font-mono">{p.sp.toFixed(1)} SP</span>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
