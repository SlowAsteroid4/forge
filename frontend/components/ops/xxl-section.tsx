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
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import type { XxlItem } from "@/lib/types/cp-approvals";

interface Props {
  items: XxlItem[];
}

export function XxlSection({ items }: Props) {
  const router = useRouter();
  const [loadingKey, setLoadingKey] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  async function handleMarkNotified(jiraKey: string) {
    setLoadingKey(jiraKey);
    setErrors((prev) => ({ ...prev, [jiraKey]: "" }));
    try {
      await api.post(`/cp-approvals/${jiraKey}/mark-xxl-notified`, {});
      router.refresh();
    } catch (e) {
      const msg = e instanceof ApiError ? e.detail : "Error al notificar";
      setErrors((prev) => ({ ...prev, [jiraKey]: msg }));
    } finally {
      setLoadingKey(null);
    }
  }

  return (
    <div className="rounded-md border border-border overflow-hidden">
      <div className="px-4 py-2.5 border-b border-border bg-muted/30">
        <p className="text-xs text-muted-foreground">
          Estas subtasks tienen talla XXL y deben dividirse en subtasks más pequeñas
          antes de ser trabajadas. Máximo permitido es XL (8 CP).
        </p>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Key</TableHead>
            <TableHead>Summary</TableHead>
            <TableHead>Área</TableHead>
            <TableHead className="text-right">Acción</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.jira_key}>
              <TableCell className="font-mono text-xs">{item.jira_key}</TableCell>
              <TableCell className="text-sm max-w-xs">
                <span className="line-clamp-2">{item.summary}</span>
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">{item.area}</TableCell>
              <TableCell className="text-right">
                <div className="flex flex-col items-end gap-1">
                  <Button
                    size="xs"
                    variant="outline"
                    disabled={loadingKey === item.jira_key}
                    onClick={() => handleMarkNotified(item.jira_key)}
                  >
                    {loadingKey === item.jira_key ? "Guardando…" : "Marcar notificado"}
                  </Button>
                  {errors[item.jira_key] && (
                    <p className="text-xs text-destructive">{errors[item.jira_key]}</p>
                  )}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
