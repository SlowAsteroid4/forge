"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, ApiError } from "@/lib/api";
import type { CycleCloseResponse, PlayerOption } from "@/lib/types/cycle-close";

interface Props {
  cycleId: number;
  cycleName: string;
  currentMvpName: string | null;
  allPlayers: PlayerOption[];
  canEdit: boolean;
}

export function MvpEditButton({
  cycleId,
  cycleName,
  currentMvpName,
  allPlayers,
  canEdit,
}: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [newPlayerId, setNewPlayerId] = useState<string>("");
  const [reason, setReason] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reasonValid = reason.trim().length >= 20;
  const canSubmit = newPlayerId !== "" && reasonValid;

  async function handleEdit() {
    setIsLoading(true);
    setError(null);
    try {
      await api.post<CycleCloseResponse>(`/admin/cycles/${cycleId}/edit-mvp`, {
        new_mvp_player_id: Number(newPlayerId),
        reason: reason.trim(),
      });
      setOpen(false);
      router.refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Error al editar MVP");
    } finally {
      setIsLoading(false);
    }
  }

  if (!canEdit) {
    return (
      <span
        title="La ventana de edición de 24 h hábiles ha expirado"
        className="text-xs text-muted-foreground/50 cursor-not-allowed"
      >
        Editar MVP (expirado)
      </span>
    );
  }

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        Editar MVP
      </Button>

      <Dialog open={open} onOpenChange={(o) => !isLoading && setOpen(o)}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Editar MVP — {cycleName}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 text-sm">
            {currentMvpName && (
              <p className="text-muted-foreground">
                MVP actual: <strong>{currentMvpName}</strong>
              </p>
            )}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Nuevo MVP <span className="text-destructive">*</span>
              </label>
              <Select value={newPlayerId} onValueChange={(v) => setNewPlayerId(v ?? "")}>
                <SelectTrigger size="sm">
                  <SelectValue placeholder="Seleccionar player…" />
                </SelectTrigger>
                <SelectContent>
                  {allPlayers.map((p) => (
                    <SelectItem key={p.id} value={String(p.id)}>
                      {p.display_name}{" "}
                      <span className="text-muted-foreground text-xs">
                        ({p.area})
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Razón del cambio <span className="text-destructive">*</span>
              </label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Explica el motivo del cambio de MVP… (mín. 20 caracteres)"
                rows={3}
                className="w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none resize-none placeholder:text-muted-foreground focus:border-ring focus:ring-3 focus:ring-ring/50"
              />
              <p className="text-xs text-muted-foreground text-right">
                {reason.length} / mín. 20
              </p>
            </div>
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              disabled={isLoading}
              onClick={() => setOpen(false)}
            >
              Cancelar
            </Button>
            <Button size="sm" disabled={!canSubmit || isLoading} onClick={handleEdit}>
              {isLoading ? "Guardando…" : "Aplicar cambio"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
