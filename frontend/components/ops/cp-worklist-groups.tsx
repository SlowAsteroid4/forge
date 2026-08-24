"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { ApartadoGroup } from "@/lib/types/cp-worklist";

interface Props {
  groups: ApartadoGroup[];
  jiraBaseUrl: string | null;
}

/** Subtasks sin CP agrupadas por apartado — grupos colapsables, read-only (WP-24). */
export function CpWorklistGroups({ groups, jiraBaseUrl }: Props) {
  // Todos los grupos abiertos por default; el estado guarda los colapsados.
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  if (groups.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No hay subtasks sin CP. Todo el trabajo está tallado. 🎉
      </p>
    );
  }

  function toggle(apartado: string) {
    setCollapsed((prev) => ({ ...prev, [apartado]: !prev[apartado] }));
  }

  return (
    <div className="space-y-3">
      {groups.map((group) => {
        const isOpen = !collapsed[group.apartado];
        return (
          <div key={group.apartado} className="rounded-md border border-border overflow-hidden">
            <button
              type="button"
              onClick={() => toggle(group.apartado)}
              className="w-full flex items-center gap-2 px-4 py-2.5 bg-muted/30 hover:bg-muted/50 transition-colors text-left"
            >
              <ChevronDown
                size={14}
                className={cn(
                  "text-muted-foreground transition-transform",
                  !isOpen && "-rotate-90",
                )}
              />
              <span className="text-sm font-medium flex-1">{group.apartado}</span>
              <Badge variant="secondary" className="h-4 px-1.5 text-[10px]">
                {group.count}
              </Badge>
            </button>
            {isOpen && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Key</TableHead>
                    <TableHead>Summary</TableHead>
                    <TableHead>Área</TableHead>
                    <TableHead>Player</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">En BD</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {group.items.map((item) => (
                    <TableRow key={item.jira_key}>
                      <TableCell className="font-mono text-xs">
                        {jiraBaseUrl ? (
                          <a
                            href={`${jiraBaseUrl}/browse/${item.jira_key}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:underline text-primary"
                          >
                            {item.jira_key}
                          </a>
                        ) : (
                          item.jira_key
                        )}
                      </TableCell>
                      <TableCell className="text-sm max-w-xs">
                        <span className="line-clamp-2">{item.summary}</span>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{item.area}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {item.assignee_name ?? "—"}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{item.status}</TableCell>
                      <TableCell className="text-right text-xs text-muted-foreground">
                        {item.age_days}d
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        );
      })}
    </div>
  );
}
