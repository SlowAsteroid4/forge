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
import { Badge } from "@/components/ui/badge";
import { api, ApiError } from "@/lib/api";
import type {
  DebuffCatalogItem,
  ApplyPenaltyRequest,
  PenaltyActionResponse,
} from "@/lib/types/penalties";

interface Props {
  open: boolean;
  onClose: () => void;
  catalog: DebuffCatalogItem[];
}

type Mode = "catalog" | "custom";

export function ApplyPenaltyModal({ open, onClose, catalog }: Props) {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("catalog");
  const [subtaskKey, setSubtaskKey] = useState("");
  const [selectedCode, setSelectedCode] = useState<string>("");
  const [customSp, setCustomSp] = useState<string>("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Solo mostrar debuffs manuales (no auto) en el modal
  const manualDebuffs = catalog.filter((d) => !d.is_auto);

  function resetForm() {
    setSubtaskKey("");
    setSelectedCode("");
    setCustomSp("");
    setReason("");
    setError(null);
    setSuccess(null);
    setMode("catalog");
  }

  function handleClose() {
    resetForm();
    onClose();
  }

  async function handleSubmit() {
    setError(null);
    setSuccess(null);

    if (!subtaskKey.trim()) {
      setError("La clave de subtask es obligatoria.");
      return;
    }
    if (reason.trim().length < 30) {
      setError("La razón debe tener al menos 30 caracteres.");
      return;
    }
    if (mode === "catalog" && !selectedCode) {
      setError("Selecciona un debuff del catálogo.");
      return;
    }
    if (mode === "custom") {
      const sp = parseFloat(customSp);
      if (isNaN(sp) || sp <= 0) {
        setError("Ingresa un valor de SP positivo.");
        return;
      }
    }

    setLoading(true);
    try {
      const body: ApplyPenaltyRequest = {
        subtask_key: subtaskKey.trim().toUpperCase(),
        reason: reason.trim(),
      };
      if (mode === "catalog") {
        body.catalog_code = selectedCode;
      } else {
        body.custom_sp = parseFloat(customSp);
      }

      const res = await api.post<PenaltyActionResponse>("/penalties", body);
      setSuccess(
        `Penalización aplicada. SP final: ${res.sp_final?.toFixed(2) ?? "—"}`,
      );
      setTimeout(() => {
        handleClose();
        router.refresh();
      }, 1200);
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Error al aplicar la penalización.");
    } finally {
      setLoading(false);
    }
  }

  const selectedDebuff = catalog.find((d) => d.code === selectedCode);

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Aplicar penalización manual</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Subtask key */}
          <div>
            <label className="text-xs font-medium block mb-1">
              Clave de subtask
            </label>
            <input
              className="w-full border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              placeholder="YAP-123"
              value={subtaskKey}
              onChange={(e) => setSubtaskKey(e.target.value)}
            />
          </div>

          {/* Modo */}
          <div>
            <label className="text-xs font-medium block mb-2">
              Fuente de penalización
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => setMode("catalog")}
                className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                  mode === "catalog"
                    ? "bg-primary text-primary-foreground border-primary"
                    : "border-border text-muted-foreground hover:bg-accent"
                }`}
              >
                Del catálogo
              </button>
              <button
                onClick={() => setMode("custom")}
                className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                  mode === "custom"
                    ? "bg-primary text-primary-foreground border-primary"
                    : "border-border text-muted-foreground hover:bg-accent"
                }`}
              >
                Custom (SP libre)
              </button>
            </div>
          </div>

          {/* Catálogo de debuffs */}
          {mode === "catalog" && (
            <div>
              {manualDebuffs.length === 0 ? (
                <p className="text-xs text-muted-foreground italic">
                  El catálogo de debuffs manuales está vacío. Usa "Custom" por
                  ahora.
                </p>
              ) : (
                <div className="space-y-1 max-h-48 overflow-y-auto border rounded-md p-2">
                  {manualDebuffs.map((d) => (
                    <button
                      key={d.code}
                      onClick={() => setSelectedCode(d.code)}
                      className={`w-full text-left px-2 py-1.5 rounded text-xs transition-colors ${
                        selectedCode === d.code
                          ? "bg-accent text-accent-foreground"
                          : "hover:bg-accent/50"
                      }`}
                    >
                      <span className="font-mono font-medium mr-2">
                        {d.code}
                      </span>
                      <span>{d.narrative_name}</span>
                      <Badge variant="secondary" className="ml-2 text-[10px]">
                        {d.penalty_type === "percentage"
                          ? `-${d.value}%`
                          : `-${d.value} SP`}
                      </Badge>
                    </button>
                  ))}
                </div>
              )}
              {selectedDebuff && (
                <p className="text-[11px] text-muted-foreground mt-1 italic">
                  {selectedDebuff.trigger_description}
                </p>
              )}
            </div>
          )}

          {/* Custom SP */}
          {mode === "custom" && (
            <div>
              <label className="text-xs font-medium block mb-1">
                Penalización en SP (positivo)
              </label>
              <input
                type="number"
                min="0.1"
                step="0.5"
                className="w-full border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                placeholder="ej. 2.0"
                value={customSp}
                onChange={(e) => setCustomSp(e.target.value)}
              />
            </div>
          )}

          {/* Razón */}
          <div>
            <label className="text-xs font-medium block mb-1">
              Razón (mín. 30 chars)
            </label>
            <textarea
              className="w-full border rounded-md px-3 py-2 text-sm resize-none h-24 focus:outline-none focus:ring-1 focus:ring-ring"
              placeholder="Describe por qué se aplica la penalización…"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <p className="text-[10px] text-muted-foreground mt-0.5">
              {reason.trim().length} / 30 mínimo
            </p>
          </div>

          {error && <p className="text-xs text-destructive">{error}</p>}
          {success && <p className="text-xs text-green-600">{success}</p>}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Cancelar
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={loading}
            variant="destructive"
          >
            {loading ? "Aplicando…" : "Aplicar penalización"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
