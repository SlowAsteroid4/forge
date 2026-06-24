"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import type {
  PenaltyListItem,
  ResolveAppealRequest,
  PenaltyActionResponse,
} from "@/lib/types/penalties";

interface Props {
  item: PenaltyListItem | null;
  onClose: () => void;
}

type Resolution = "upheld" | "reversed" | "reduced";

const RESOLUTION_LABELS: Record<Resolution, string> = {
  upheld: "Rechazar apelación (mantener penalización)",
  reversed: "Aceptar apelación (revertir penalización)",
  reduced: "Aceptar parcialmente (reducir penalización)",
};

export function AppealResolutionModal({ item, onClose }: Props) {
  const router = useRouter();
  const [resolution, setResolution] = useState<Resolution>("upheld");
  const [notes, setNotes] = useState("");
  const [reducedValue, setReducedValue] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleClose() {
    setResolution("upheld");
    setNotes("");
    setReducedValue("");
    setError(null);
    onClose();
  }

  async function handleSubmit() {
    if (!item) return;
    setError(null);

    if (notes.trim().length < 30) {
      setError("Las notas deben tener al menos 30 caracteres.");
      return;
    }
    if (resolution === "reduced") {
      const rv = parseFloat(reducedValue);
      if (isNaN(rv) || rv < 0) {
        setError("Ingresa el nuevo valor neto de penalización (>= 0).");
        return;
      }
      if (rv >= item.amount_sp) {
        setError(
          `El valor reducido (${rv}) debe ser menor que la penalización original (${item.amount_sp}).`,
        );
        return;
      }
    }

    setLoading(true);
    try {
      const body: ResolveAppealRequest = {
        resolution,
        notes: notes.trim(),
      };
      if (resolution === "reduced") {
        body.reduced_value = parseFloat(reducedValue);
      }
      await api.post<PenaltyActionResponse>(
        `/penalties/${item.id}/resolve-appeal`,
        body,
      );
      handleClose();
      router.refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Error al resolver apelación.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={item !== null} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Resolver apelación</DialogTitle>
        </DialogHeader>

        {item && (
          <div className="space-y-4 py-2">
            <div className="text-xs text-muted-foreground space-y-1 border rounded-md p-3 bg-muted/30">
              <p>
                <span className="font-medium">Subtask:</span>{" "}
                {item.subtask_key}
              </p>
              <p>
                <span className="font-medium">Player:</span>{" "}
                {item.player_name ?? "—"}
              </p>
              <p>
                <span className="font-medium">Penalización:</span> -
                {item.amount_sp.toFixed(1)} SP
              </p>
              <p className="italic">{item.reason}</p>
            </div>

            <div>
              <label className="text-xs font-medium block mb-2">Resolución</label>
              <div className="space-y-1.5">
                {(["upheld", "reversed", "reduced"] as Resolution[]).map((r) => (
                  <label
                    key={r}
                    className={`flex items-center gap-2 cursor-pointer px-3 py-2 rounded-md border text-xs transition-colors ${
                      resolution === r
                        ? "border-primary bg-accent"
                        : "border-border hover:bg-accent/40"
                    }`}
                  >
                    <input
                      type="radio"
                      name="resolution"
                      value={r}
                      checked={resolution === r}
                      onChange={() => setResolution(r)}
                      className="accent-primary"
                    />
                    {RESOLUTION_LABELS[r]}
                  </label>
                ))}
              </div>
            </div>

            {resolution === "reduced" && (
              <div>
                <label className="text-xs font-medium block mb-1">
                  Nuevo valor neto de penalización (SP)
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.1"
                  className="w-full border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                  placeholder={`Valor entre 0 y ${item.amount_sp.toFixed(1)}`}
                  value={reducedValue}
                  onChange={(e) => setReducedValue(e.target.value)}
                />
                {reducedValue && !isNaN(parseFloat(reducedValue)) && (
                  <p className="text-[10px] text-muted-foreground mt-0.5">
                    Se revertirán{" "}
                    {(item.amount_sp - parseFloat(reducedValue)).toFixed(1)} SP
                  </p>
                )}
              </div>
            )}

            <div>
              <label className="text-xs font-medium block mb-1">
                Notas de resolución (mín. 30 chars)
              </label>
              <textarea
                className="w-full border rounded-md px-3 py-2 text-sm resize-none h-20 focus:outline-none focus:ring-1 focus:ring-ring"
                placeholder="Explica la decisión…"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
              <p className="text-[10px] text-muted-foreground mt-0.5">
                {notes.trim().length} / 30 mínimo
              </p>
            </div>

            {error && <p className="text-xs text-destructive">{error}</p>}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading ? "Guardando…" : "Confirmar resolución"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
