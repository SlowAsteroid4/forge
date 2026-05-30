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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, ApiError } from "@/lib/api";
import type { CpApprovalPendingItem } from "@/lib/types/cp-approvals";

/* ── Constantes ──────────────────────────────────────────────────────────── */

const SIZE_CP: Record<string, number> = { XS: 1, S: 2, M: 3, L: 5, XL: 8 };
const SIZES = ["XS", "S", "M", "L", "XL"] as const;
const JIRA_BASE = "https://beyapsi-org.atlassian.net";

type DialogType = "detail" | "approve" | "adjust" | "reject" | null;

/* ── Componente ──────────────────────────────────────────────────────────── */

interface Props {
  items: CpApprovalPendingItem[];
}

export function ApprovalTable({ items }: Props) {
  const router = useRouter();

  // Estado compartido de diálogos
  const [activeItem, setActiveItem] = useState<CpApprovalPendingItem | null>(null);
  const [dialogType, setDialogType] = useState<DialogType>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Estado de los formularios
  const [adjustSize, setAdjustSize] = useState("M");
  const [adjustReason, setAdjustReason] = useState("");
  const [rejectReason, setRejectReason] = useState("");

  /* helpers */
  function openDialog(item: CpApprovalPendingItem, type: DialogType) {
    setActiveItem(item);
    setDialogType(type);
    setError(null);
    setAdjustSize(item.complexity_size ?? "M");
    setAdjustReason("");
    setRejectReason("");
  }

  function closeDialog() {
    setDialogType(null);
    setActiveItem(null);
    setError(null);
  }

  function handleOpenChange(open: boolean) {
    if (!open) closeDialog();
  }

  /* acciones */
  async function handleApprove() {
    if (!activeItem) return;
    setIsLoading(true);
    setError(null);
    try {
      await api.post(`/cp-approvals/${activeItem.jira_key}/approve`, {});
      router.refresh();
      closeDialog();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Error al aprobar");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleAdjust() {
    if (!activeItem) return;
    if (adjustReason.trim().length < 10) {
      setError("La razón debe tener al menos 10 caracteres");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      await api.post(`/cp-approvals/${activeItem.jira_key}/adjust`, {
        new_size: adjustSize,
        reason: adjustReason.trim(),
      });
      router.refresh();
      closeDialog();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Error al ajustar");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleReject() {
    if (!activeItem) return;
    if (rejectReason.trim().length < 10) {
      setError("El motivo debe tener al menos 10 caracteres");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      await api.post(`/cp-approvals/${activeItem.jira_key}/reject`, {
        reason: rejectReason.trim(),
      });
      router.refresh();
      closeDialog();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Error al rechazar");
    } finally {
      setIsLoading(false);
    }
  }

  /* empty state */
  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border p-8 text-center">
        <p className="text-sm text-muted-foreground">
          No hay CPs pendientes de aprobación.
        </p>
      </div>
    );
  }

  return (
    <>
      {/* ── Tabla ──────────────────────────────────────────────────────── */}
      <div className="rounded-md border border-border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Key</TableHead>
              <TableHead>Summary</TableHead>
              <TableHead>Área</TableHead>
              <TableHead>Talla</TableHead>
              <TableHead className="text-right">CP</TableHead>
              <TableHead>Esperando</TableHead>
              <TableHead className="text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow
                key={item.jira_key}
                className="cursor-pointer"
                onClick={() => openDialog(item, "detail")}
              >
                <TableCell className="font-mono text-xs">{item.jira_key}</TableCell>
                <TableCell className="text-sm max-w-xs">
                  <span className="line-clamp-2">{item.summary}</span>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">{item.area}</TableCell>
                <TableCell>
                  <Badge variant="outline" className="font-mono">
                    {item.complexity_size ?? "—"}
                  </Badge>
                </TableCell>
                <TableCell className="text-right tabular-nums font-medium text-sm">
                  {item.cp ?? "—"}
                </TableCell>
                <TableCell>
                  <Badge variant={item.is_overdue ? "destructive" : "secondary"}>
                    {item.waiting_days}d
                  </Badge>
                </TableCell>
                <TableCell
                  className="text-right"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="flex justify-end gap-1">
                    <Button
                      size="xs"
                      onClick={() => openDialog(item, "approve")}
                    >
                      Aprobar
                    </Button>
                    <Button
                      size="xs"
                      variant="outline"
                      onClick={() => openDialog(item, "adjust")}
                    >
                      Ajustar
                    </Button>
                    <Button
                      size="xs"
                      variant="destructive"
                      onClick={() => openDialog(item, "reject")}
                    >
                      Rechazar
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* ── Diálogo: Detalle (AC-4.8) ──────────────────────────────────── */}
      <Dialog open={dialogType === "detail"} onOpenChange={handleOpenChange}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              <a
                href={`${JIRA_BASE}/browse/${activeItem?.jira_key}`}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:underline text-primary font-mono"
              >
                {activeItem?.jira_key}
              </a>
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 text-sm">
            <p className="font-medium leading-snug">{activeItem?.summary}</p>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
              <dt className="text-muted-foreground">Área</dt>
              <dd>{activeItem?.area}</dd>
              <dt className="text-muted-foreground">Proyecto</dt>
              <dd>{activeItem?.project_code ?? "—"}</dd>
              <dt className="text-muted-foreground">Talla</dt>
              <dd className="font-mono">{activeItem?.complexity_size ?? "—"}</dd>
              <dt className="text-muted-foreground">CP propuesto</dt>
              <dd className="font-mono font-medium">{activeItem?.cp ?? "—"}</dd>
              <dt className="text-muted-foreground">Esperando</dt>
              <dd>
                <Badge variant={activeItem?.is_overdue ? "destructive" : "secondary"}>
                  {activeItem?.waiting_days}d
                </Badge>
              </dd>
            </dl>
            {activeItem?.cp_rejection_reason && (
              <div className="rounded-md bg-destructive/10 p-2.5 space-y-0.5">
                <p className="text-xs font-medium text-destructive">Rechazo previo:</p>
                <p className="text-xs">{activeItem.cp_rejection_reason}</p>
              </div>
            )}
          </div>
          <DialogFooter>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={() => {
                  const item = activeItem!;
                  closeDialog();
                  setTimeout(() => openDialog(item, "approve"), 50);
                }}
              >
                Aprobar
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  const item = activeItem!;
                  closeDialog();
                  setTimeout(() => openDialog(item, "adjust"), 50);
                }}
              >
                Ajustar
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => {
                  const item = activeItem!;
                  closeDialog();
                  setTimeout(() => openDialog(item, "reject"), 50);
                }}
              >
                Rechazar
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Diálogo: Confirmar aprobación ──────────────────────────────── */}
      <Dialog open={dialogType === "approve"} onOpenChange={handleOpenChange}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Aprobar CP — {activeItem?.jira_key}</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 text-sm">
            <p className="text-muted-foreground line-clamp-2">{activeItem?.summary}</p>
            <p>
              Se aprobará talla{" "}
              <strong className="font-mono">{activeItem?.complexity_size}</strong> con{" "}
              <strong>{activeItem?.cp} CP</strong>. Esta acción es irreversible.
            </p>
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <DialogFooter>
            <Button size="sm" disabled={isLoading} onClick={handleApprove}>
              {isLoading ? "Aprobando…" : "Confirmar aprobación"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Diálogo: Ajustar y aprobar ─────────────────────────────────── */}
      <Dialog open={dialogType === "adjust"} onOpenChange={handleOpenChange}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Ajustar y aprobar — {activeItem?.jira_key}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 text-sm">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Nueva talla
              </label>
              <div className="flex items-center gap-3">
                <Select
                  value={adjustSize}
                  onValueChange={(v) => setAdjustSize(v as string)}
                >
                  <SelectTrigger size="sm" className="w-24">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SIZES.map((s) => (
                      <SelectItem key={s} value={s}>
                        {s}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <span className="text-muted-foreground">
                  →{" "}
                  <strong className="text-foreground font-mono">
                    {SIZE_CP[adjustSize] ?? "—"} CP
                  </strong>
                </span>
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Razón del ajuste <span className="text-destructive">*</span>
              </label>
              <textarea
                value={adjustReason}
                onChange={(e) => setAdjustReason(e.target.value)}
                placeholder="Explica por qué se ajusta la talla… (mín. 10 caracteres)"
                rows={3}
                className="w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none resize-none placeholder:text-muted-foreground focus:border-ring focus:ring-3 focus:ring-ring/50"
              />
              <p className="text-xs text-muted-foreground text-right">
                {adjustReason.length} / mín. 10
              </p>
            </div>
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <DialogFooter>
            <Button size="sm" disabled={isLoading} onClick={handleAdjust}>
              {isLoading ? "Guardando…" : "Ajustar y aprobar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Diálogo: Rechazar ──────────────────────────────────────────── */}
      <Dialog open={dialogType === "reject"} onOpenChange={handleOpenChange}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Rechazar CP — {activeItem?.jira_key}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 text-sm">
            <p className="text-muted-foreground line-clamp-2">{activeItem?.summary}</p>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Motivo del rechazo <span className="text-destructive">*</span>
              </label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Indica por qué se rechaza… (mín. 10 caracteres)"
                rows={3}
                className="w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none resize-none placeholder:text-muted-foreground focus:border-ring focus:ring-3 focus:ring-ring/50"
              />
              <p className="text-xs text-muted-foreground text-right">
                {rejectReason.length} / mín. 10
              </p>
            </div>
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <DialogFooter>
            <Button
              size="sm"
              variant="destructive"
              disabled={isLoading}
              onClick={handleReject}
            >
              {isLoading ? "Rechazando…" : "Confirmar rechazo"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
