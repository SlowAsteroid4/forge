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
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api, ApiError } from "@/lib/api";
import type {
  PenaltyListItem,
  PenaltyActionResponse,
  ReversePenaltyRequest,
} from "@/lib/types/penalties";

const JIRA_BASE = "https://beyapsi-org.atlassian.net";

function appealBadge(item: PenaltyListItem) {
  if (!item.is_appealed) return null;
  if (item.appeal_resolution === null)
    return <Badge variant="outline" className="text-yellow-600 border-yellow-500">Apelado</Badge>;
  if (item.appeal_resolution === "upheld")
    return <Badge variant="outline" className="text-red-600 border-red-500">Rechazada</Badge>;
  if (item.appeal_resolution === "reversed")
    return <Badge variant="outline" className="text-green-600 border-green-500">Revertida</Badge>;
  if (item.appeal_resolution === "reduced")
    return <Badge variant="outline" className="text-blue-600 border-blue-500">Reducida</Badge>;
  return null;
}

interface Props {
  items: PenaltyListItem[];
}

export function PenaltyTable({ items }: Props) {
  const router = useRouter();
  const [selected, setSelected] = useState<PenaltyListItem | null>(null);
  const [showReverse, setShowReverse] = useState(false);
  const [reason, setReason] = useState("");
  const [partialValue, setPartialValue] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function openReverse(item: PenaltyListItem) {
    setSelected(item);
    setShowReverse(true);
    setReason("");
    setPartialValue("");
    setError(null);
  }

  function closeReverse() {
    setShowReverse(false);
    setSelected(null);
    setError(null);
  }

  async function handleReverse() {
    if (!selected) return;
    if (reason.trim().length < 30) {
      setError("La razón debe tener al menos 30 caracteres.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const body: ReversePenaltyRequest = { reason: reason.trim() };
      const pv = parseFloat(partialValue);
      if (partialValue.trim() !== "" && !isNaN(pv)) {
        body.partial_new_value = pv;
      }
      await api.post<PenaltyActionResponse>(
        `/penalties/${selected.id}/reverse`,
        body,
      );
      closeReverse();
      router.refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Error al revertir.");
    } finally {
      setLoading(false);
    }
  }

  async function handleMarkAppealed(item: PenaltyListItem) {
    try {
      await api.post<PenaltyActionResponse>(
        `/penalties/${item.id}/mark-appealed`,
        {},
      );
      router.refresh();
    } catch (e) {
      alert(e instanceof ApiError ? e.detail : "Error al marcar apelación.");
    }
  }

  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        No hay penalizaciones para mostrar.
      </p>
    );
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Subtask</TableHead>
            <TableHead>Player</TableHead>
            <TableHead>Tipo</TableHead>
            <TableHead className="text-right">SP</TableHead>
            <TableHead>Razón</TableHead>
            <TableHead>Aplicado por</TableHead>
            <TableHead>Estado</TableHead>
            <TableHead className="text-right">Acciones</TableHead>
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
                  {item.catalog_code ?? item.adjustment_type}
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
              <TableCell>{appealBadge(item)}</TableCell>
              <TableCell className="text-right">
                <div className="flex gap-1 justify-end">
                  {item.adjustment_type === "debuff_manual" &&
                    !item.appeal_resolution && (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-6 px-2 text-xs"
                          onClick={() => openReverse(item)}
                        >
                          Revertir
                        </Button>
                        {!item.is_appealed && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 px-2 text-xs text-yellow-600"
                            onClick={() => handleMarkAppealed(item)}
                          >
                            Apelar
                          </Button>
                        )}
                      </>
                    )}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {/* Modal Revertir */}
      <Dialog open={showReverse} onOpenChange={(o) => !o && closeReverse()}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Revertir penalización</DialogTitle>
          </DialogHeader>

          {selected && (
            <div className="space-y-4 py-2">
              <div className="text-xs text-muted-foreground space-y-1">
                <p>
                  <span className="font-medium">Subtask:</span>{" "}
                  {selected.subtask_key}
                </p>
                <p>
                  <span className="font-medium">Penalización original:</span>{" "}
                  -{selected.amount_sp.toFixed(1)} SP
                </p>
              </div>

              <div>
                <label className="text-xs font-medium block mb-1">
                  Razón (mín. 30 chars)
                </label>
                <textarea
                  className="w-full border rounded-md px-3 py-2 text-sm resize-none h-20 focus:outline-none focus:ring-1 focus:ring-ring"
                  placeholder="Explica por qué se revierte la penalización…"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  {reason.trim().length}/30 chars mínimos
                </p>
              </div>

              <div>
                <label className="text-xs font-medium block mb-1">
                  Nuevo valor neto (opcional — vacío = reversión total)
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.1"
                  className="w-full border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                  placeholder={`Vacío = revertir ${selected.amount_sp.toFixed(1)} SP completos`}
                  value={partialValue}
                  onChange={(e) => setPartialValue(e.target.value)}
                />
                {partialValue.trim() !== "" && !isNaN(parseFloat(partialValue)) && (
                  <p className="text-[10px] text-muted-foreground mt-0.5">
                    Se revertirán{" "}
                    {(selected.amount_sp - parseFloat(partialValue)).toFixed(1)} SP
                    (neto final: {parseFloat(partialValue).toFixed(1)} SP)
                  </p>
                )}
              </div>

              {error && (
                <p className="text-xs text-destructive">{error}</p>
              )}
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={closeReverse} disabled={loading}>
              Cancelar
            </Button>
            <Button onClick={handleReverse} disabled={loading}>
              {loading ? "Revirtiendo…" : "Confirmar reversal"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
