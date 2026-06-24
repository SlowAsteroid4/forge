"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api, ApiError } from "@/lib/api";
import type {
  MonthlyCandidate,
  MonthCloseResponse,
} from "@/lib/types/monthly-mvp";

const AREA_COLORS: Record<string, string> = {
  BE: "bg-blue-100 text-blue-700",
  FE: "bg-purple-100 text-purple-700",
  QA: "bg-green-100 text-green-700",
  PM: "bg-orange-100 text-orange-700",
};

interface Props {
  periodLabel: string;
  candidates: MonthlyCandidate[];
  canClose: boolean;
  alreadyClosed: boolean;
}

export function MonthCloseClient({
  periodLabel,
  candidates,
  canClose,
  alreadyClosed,
}: Props) {
  const router = useRouter();

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [reason, setReason] = useState("");
  const [showConfirm, setShowConfirm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MonthCloseResponse | null>(null);

  const reasonLen = reason.trim().length;
  const reasonValid = reasonLen >= 30;
  const canSubmit = canClose && !alreadyClosed && selectedId != null && reasonValid;

  const selectedName = candidates.find((c) => c.player_id === selectedId)?.display_name;

  async function handleClose() {
    if (!selectedId) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.post<MonthCloseResponse>(`/admin/months/${periodLabel}/close`, {
        mvp_player_id: selectedId,
        reason: reason.trim(),
      });
      setResult(res);
      setShowConfirm(false);
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Error al cerrar el mes");
    } finally {
      setIsLoading(false);
    }
  }

  if (result) {
    return (
      <div className="rounded-md border border-green-500/40 bg-green-500/5 p-6 text-center space-y-2">
        <p className="text-2xl">🏆</p>
        <p className="font-semibold text-green-700">{result.message}</p>
        {result.ach04_unlocked && (
          <p className="text-xs text-muted-foreground">
            ACH04 desbloqueado por primera vez
          </p>
        )}
        <Button
          variant="outline"
          size="sm"
          className="mt-2"
          onClick={() => router.push("/operations/months/mvp-history")}
        >
          Ver historial MVP del Mes
        </Button>
      </div>
    );
  }

  return (
    <>
      {/* Candidatos */}
      <section className="space-y-2">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          MVPs semanales elegibles
        </h2>
        {candidates.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No hay MVPs semanales en este mes. Cierra los ciclos del mes con MVP antes de cerrar el mes.
          </p>
        ) : (
          <div className="space-y-2">
            {candidates.map((c) => (
              <button
                key={c.player_id}
                type="button"
                disabled={alreadyClosed}
                onClick={() =>
                  setSelectedId(selectedId === c.player_id ? null : c.player_id)
                }
                className={[
                  "w-full text-left rounded-md border p-3 transition-colors",
                  selectedId === c.player_id
                    ? "border-primary bg-primary/5 ring-1 ring-primary"
                    : "border-border hover:bg-accent/30",
                  alreadyClosed ? "opacity-50 cursor-not-allowed" : "",
                ].join(" ")}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className={[
                        "inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold shrink-0",
                        AREA_COLORS[c.area] ?? "bg-muted text-muted-foreground",
                      ].join(" ")}
                    >
                      {c.area}
                    </span>
                    <span className="font-medium text-sm">{c.display_name}</span>
                  </div>
                  <div className="flex gap-3 text-xs text-muted-foreground shrink-0">
                    <span>{c.sp_total_month.toFixed(1)} SP</span>
                    <span>{c.cp_total_month} CP</span>
                    <span>{c.subtasks_done_month} done</span>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-1 truncate">
                  {c.metric_highlight}
                </p>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* Razón */}
      <section className="space-y-1">
        <label className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Justificación <span className="normal-case font-normal">(mínimo 30 caracteres)</span>
        </label>
        <textarea
          rows={3}
          disabled={alreadyClosed}
          placeholder="Describe por qué este player fue el mejor MVP del mes…"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <p className={["text-xs", reasonValid ? "text-muted-foreground" : "text-destructive"].join(" ")}>
          {reasonLen}/30 caracteres
        </p>
      </section>

      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/5 px-3 py-2">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {/* CTA */}
      <div className="flex justify-end">
        <Button
          disabled={!canSubmit}
          onClick={() => setShowConfirm(true)}
        >
          Cerrar mes {periodLabel}
        </Button>
      </div>

      {/* Confirm dialog */}
      <Dialog open={showConfirm} onOpenChange={setShowConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>¿Confirmar cierre de {periodLabel}?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            MVP del Mes: <strong>{selectedName}</strong> recibirá{" "}
            <Badge variant="secondary">+10 SP (B17M)</Badge>. Esta acción es
            reversible solo dentro de las 72h hábiles siguientes.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowConfirm(false)}>
              Cancelar
            </Button>
            <Button onClick={handleClose} disabled={isLoading}>
              {isLoading ? "Cerrando…" : "Confirmar cierre"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
