"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AppealResolutionModal } from "@/components/ops/penalties/AppealResolutionModal";
import type { PenaltyListItem } from "@/lib/types/penalties";

const JIRA_BASE = "https://beyapsi-org.atlassian.net";

interface Props {
  items: PenaltyListItem[];
  total: number;
}

export function AppealsClient({ items, total }: Props) {
  const router = useRouter();
  const [selected, setSelected] = useState<PenaltyListItem | null>(null);

  return (
    <>
      <div>
        <h1 className="text-lg font-semibold">Apelaciones pendientes</h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          {total} apelación{total !== 1 ? "es" : ""} pendiente
          {total !== 1 ? "s" : ""} de resolver
        </p>
      </div>

      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground py-12 text-center">
          No hay apelaciones pendientes.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Subtask</TableHead>
              <TableHead>Player</TableHead>
              <TableHead>Código</TableHead>
              <TableHead className="text-right">SP</TableHead>
              <TableHead>Razón</TableHead>
              <TableHead>Aplicado por</TableHead>
              <TableHead className="text-right">Acción</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="font-mono text-xs">
                  {item.subtask_key ? (
                    <a
                      href={`${JIRA_BASE}/browse/${item.subtask_key}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      {item.subtask_key}
                    </a>
                  ) : (
                    "—"
                  )}
                </TableCell>
                <TableCell className="text-xs">{item.player_name ?? "—"}</TableCell>
                <TableCell>
                  <Badge variant="secondary" className="text-xs">
                    {item.catalog_code ?? "CUSTOM"}
                  </Badge>
                </TableCell>
                <TableCell className="text-right text-red-600 font-semibold text-sm">
                  -{item.amount_sp.toFixed(1)}
                </TableCell>
                <TableCell
                  className="text-xs max-w-[200px] truncate"
                  title={item.reason}
                >
                  {item.reason}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {item.applied_by_name ?? `#${item.applied_by}`}
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-6 px-2 text-xs"
                    onClick={() => setSelected(item)}
                  >
                    Resolver
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <AppealResolutionModal
        item={selected}
        onClose={() => setSelected(null)}
      />
    </>
  );
}
