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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, ApiError } from "@/lib/api";
import type {
  CycleCandidate,
  CycleCloseResponse,
  PlayerOption,
} from "@/lib/types/cycle-close";

interface Props {
  cycleId: number;
  cycleName: string;
  candidates: CycleCandidate[];
  allPlayers: PlayerOption[];
  canClose: boolean;
}

export function CycleCloseClient({
  cycleId,
  cycleName,
  candidates,
  allPlayers,
  canClose,
}: Props) {
  const router = useRouter();

  const [selectedPlayerId, setSelectedPlayerId] = useState<number | null>(null);
  const [useOtherPlayer, setUseOtherPlayer] = useState(false);
  const [otherPlayerId, setOtherPlayerId] = useState<string>("");
  const [reason, setReason] = useState("");
  const [showConfirm, setShowConfirm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [closeResult, setCloseResult] = useState<CycleCloseResponse | null>(null);

  const effectivePlayerId = useOtherPlayer
    ? otherPlayerId
      ? Number(otherPlayerId)
      : null
    : selectedPlayerId;

  const reasonValid = reason.trim().length >= 20;
  const canSubmit = canClose && effectivePlayerId != null && reasonValid;

  const selectedPlayerName =
    useOtherPlayer
      ? allPlayers.find((p) => p.id === Number(otherPlayerId))?.display_name
      : candidates.find((c) => c.player_id === selectedPlayerId)?.display_name;

  async function handleClose() {
    if (!effectivePlayerId) return;
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.post<CycleCloseResponse>(
        `/admin/cycles/${cycleId}/close`,
        { mvp_player_id: effectivePlayerId, mvp_reason: reason.trim() },
      );
      setCloseResult(result);
      setShowConfirm(false);
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Error al cerrar el ciclo");
    } finally {
      setIsLoading(false);
    }
  }

  /* ── Success screen ──────────────────────────────────────────────────── */
  if (closeResult) {
    return (
      <div className="rounded-lg border border-green-500/30 bg-green-500/5 p-8 text-center space-y-4">
        <div className="text-3xl">🎉</div>
        <div>
          <h2 className="text-base font-semibold text-green-700">
            {closeResult.cycle_name} cerrado exitosamente
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            {closeResult.message}
          </p>
          {selectedPlayerName && (
            <p className="text-sm font-medium mt-2">
              MVP: <span className="text-green-700">{selectedPlayerName}</span>{" "}
              <span className="text-muted-foreground">(+5 SP)</span>
            </p>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={() => router.push("/dashboard")}>
          Ver dashboard
        </Button>
      </div>
    );
  }

  return (
    <section className="space-y-6">
      {/* ── Candidatos a MVP ───────────────────────────────────────────── */}
      <div>
        <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-3">
          Candidatos a MVP semanal (+5 SP)
        </h2>

        {candidates.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-4 text-center">
            <p className="text-sm text-muted-foreground">
              No hay candidatos con work done en este ciclo.
            </p>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {candidates.map((c) => {
              const isSelected = !useOtherPlayer && selectedPlayerId === c.player_id;
              return (
                <button
                  key={c.player_id}
                  type="button"
                  onClick={() => {
                    setSelectedPlayerId(c.player_id);
                    setUseOtherPlayer(false);
                  }}
                  className={[
                    "text-left rounded-lg border p-4 transition-colors space-y-1.5",
                    isSelected
                      ? "border-primary bg-primary/5 ring-1 ring-primary"
                      : "border-border hover:border-primary/50 hover:bg-accent/30",
                  ].join(" ")}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium leading-tight">
                      {c.display_name}
                    </span>
                    {isSelected && (
                      <span className="text-xs text-primary font-semibold">✓</span>
                    )}
                  </div>
                  <Badge variant="outline" className="text-xs">
                    {c.area}
                  </Badge>
                  <p className="text-xs text-muted-foreground">
                    {c.metric_highlight}
                  </p>
                  {c.avg_m_calidad != null && (
                    <p className="text-xs text-muted-foreground">
                      Calidad ×{c.avg_m_calidad.toFixed(2)}
                    </p>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {/* Otro player */}
        <div className="mt-3">
          <button
            type="button"
            className={[
              "text-sm px-3 py-2 rounded-md border transition-colors",
              useOtherPlayer
                ? "border-primary text-primary bg-primary/5"
                : "border-border text-muted-foreground hover:border-primary/50",
            ].join(" ")}
            onClick={() => {
              setUseOtherPlayer(true);
              setSelectedPlayerId(null);
            }}
          >
            Elegir otro player…
          </button>

          {useOtherPlayer && (
            <div className="mt-2 max-w-xs">
              <Select
                value={otherPlayerId}
                onValueChange={(v) => setOtherPlayerId(v ?? "")}
              >
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
          )}
        </div>
      </div>

      {/* ── Razón del MVP ─────────────────────────────────────────────── */}
      <div className="space-y-1.5 max-w-xl">
        <label className="text-xs font-medium text-muted-foreground">
          Razón del MVP{" "}
          <span className="text-destructive">*</span>
        </label>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Explica por qué merece ser MVP este ciclo… (mín. 20 caracteres)"
          rows={4}
          className="w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none resize-none placeholder:text-muted-foreground focus:border-ring focus:ring-3 focus:ring-ring/50"
        />
        <div className="flex justify-between items-center">
          <span
            className={[
              "text-xs",
              reasonValid ? "text-green-600" : "text-muted-foreground",
            ].join(" ")}
          >
            {reasonValid ? "✓ Listo" : `${reason.length} / mín. 20`}
          </span>
        </div>
      </div>

      {/* ── Error ─────────────────────────────────────────────────────── */}
      {error && (
        <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2">
          {error}
        </p>
      )}

      {/* ── Botón de cierre ───────────────────────────────────────────── */}
      <div>
        <Button
          disabled={!canSubmit}
          onClick={() => setShowConfirm(true)}
          className="gap-2"
        >
          Cerrar ciclo
        </Button>
        {!canClose && (
          <p className="text-xs text-destructive mt-2">
            El ciclo no puede cerrarse: revisa los errores bloqueantes arriba.
          </p>
        )}
        {canClose && !canSubmit && (
          <p className="text-xs text-muted-foreground mt-2">
            {!effectivePlayerId
              ? "Elige un MVP para continuar."
              : "Escribe al menos 20 caracteres en la razón."}
          </p>
        )}
      </div>

      {/* ── Diálogo de confirmación ───────────────────────────────────── */}
      <Dialog open={showConfirm} onOpenChange={(open) => !isLoading && setShowConfirm(open)}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Confirmar cierre de ciclo</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 text-sm">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5">
              <dt className="text-muted-foreground">Ciclo</dt>
              <dd className="font-medium">{cycleName}</dd>
              <dt className="text-muted-foreground">MVP</dt>
              <dd className="font-medium">{selectedPlayerName ?? "—"}</dd>
              <dt className="text-muted-foreground">Bono MVP</dt>
              <dd className="font-medium text-green-600">+5 SP</dd>
            </dl>
            <p className="text-xs text-muted-foreground border-t border-border pt-2">
              Esta acción cambia el estado del ciclo a <strong>closed</strong> y no
              puede deshacerse (aunque el MVP puede editarse dentro de las 24 h
              hábiles siguientes).
            </p>
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              disabled={isLoading}
              onClick={() => setShowConfirm(false)}
            >
              Cancelar
            </Button>
            <Button size="sm" disabled={isLoading} onClick={handleClose}>
              {isLoading ? "Cerrando…" : "Confirmar cierre"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
