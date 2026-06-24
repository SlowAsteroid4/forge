"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import type {
  BlockingError,
  CycleRecalcResponse,
} from "@/lib/types/cycle-close";

interface Props {
  cycleId: number;
  errors: BlockingError[];
  jiraBaseUrl: string | null;
}

const SP_FINAL_BLOCK = "done_without_sp_final";

export function CycleBlockingErrors({ cycleId, errors, jiraBaseUrl }: Props) {
  const router = useRouter();
  const [isRecalcing, setIsRecalcing] = useState(false);
  const [recalcError, setRecalcError] = useState<string | null>(null);

  if (errors.length === 0) return null;

  const hasSpFinalBlock = errors.some((e) => e.type === SP_FINAL_BLOCK);

  async function handleRecalc() {
    setIsRecalcing(true);
    setRecalcError(null);
    try {
      await api.post<CycleRecalcResponse>(
        `/admin/cycles/${cycleId}/recalc`,
        {},
      );
      // Re-fetch the Server Component: refreshes blocking errors, top players
      // and the close form's can_close without a manual reload.
      router.refresh();
    } catch (e) {
      setRecalcError(
        e instanceof ApiError ? e.detail : "Error al recalcular el SP del ciclo",
      );
      setIsRecalcing(false);
    }
    // On success we intentionally keep isRecalcing=true until refresh remounts.
  }

  return (
    <div className="rounded-md border border-destructive/50 bg-destructive/5 p-4 space-y-3">
      <p className="text-xs font-semibold text-destructive uppercase tracking-wide">
        Errores bloqueantes
      </p>
      <ul className="space-y-2.5">
        {errors.map((err, i) => (
          <li key={i} className="text-sm text-destructive space-y-1.5">
            <div className="flex gap-2">
              <span>•</span>
              <span>{err.message}</span>
            </div>
            {err.issue_keys.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pl-4">
                {err.issue_keys.map((key) =>
                  jiraBaseUrl ? (
                    <a
                      key={key}
                      href={`${jiraBaseUrl}/browse/${key}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-xs px-1.5 py-0.5 rounded border border-destructive/40 text-destructive hover:bg-destructive/10 transition-colors"
                    >
                      {key} ↗
                    </a>
                  ) : (
                    <code
                      key={key}
                      className="font-mono text-xs px-1.5 py-0.5 rounded border border-destructive/40 text-destructive select-all"
                    >
                      {key}
                    </code>
                  ),
                )}
              </div>
            )}
          </li>
        ))}
      </ul>

      {hasSpFinalBlock && (
        <div className="flex items-center gap-3 pt-1">
          <Button
            variant="outline"
            size="sm"
            disabled={isRecalcing}
            onClick={handleRecalc}
          >
            {isRecalcing ? "Recalculando…" : "Recalcular SP"}
          </Button>
          <span className="text-xs text-muted-foreground">
            Calcula el <code className="font-mono">sp_final</code> de las
            subtasks Done pendientes para desbloquear el cierre.
          </span>
        </div>
      )}

      {recalcError && (
        <p className="text-xs text-destructive">{recalcError}</p>
      )}
    </div>
  );
}
