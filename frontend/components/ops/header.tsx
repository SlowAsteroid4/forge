"use client";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useTransition } from "react";
import { toast } from "sonner";
import type { AvailableProject } from "@/lib/types/dashboard";

interface OpsHeaderProps {
  projects: AvailableProject[];
  lastSyncAt: string | null;
}

function formatRelativeTime(isoDate: string | null): string {
  if (!isoDate) return "Nunca sincronizado";
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "hace menos de 1 min";
  if (mins < 60) return `hace ${mins} min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `hace ${hours}h`;
  return `hace ${Math.floor(hours / 24)}d`;
}

export function OpsHeader({ projects, lastSyncAt }: OpsHeaderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const currentProject = searchParams.get("project") ?? "";

  function handleProjectChange(value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (!value) {
      params.delete("project");
    } else {
      params.set("project", value);
    }
    startTransition(() => {
      router.push(`${pathname}?${params.toString()}`);
    });
  }

  async function handleSync() {
    const toastId = toast.loading("Sincronizando con Jira…");
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api"}/integrations/jira/sync`, {
        method: "POST",
      });
      toast.success("Sincronización completada", { id: toastId });
      startTransition(() => router.refresh());
    } catch {
      toast.error("Error al sincronizar con Jira", { id: toastId });
    }
  }

  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-border bg-background">
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">Proyecto:</span>
        <Select value={currentProject} onValueChange={handleProjectChange}>
          <SelectTrigger className="h-8 w-56 text-sm">
            <SelectValue placeholder="Todos" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Todos</SelectItem>
            {projects.map((p) => (
              <SelectItem key={p.code} value={p.code}>
                {p.code} — {p.internal_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {isPending && (
          <span className="text-xs text-muted-foreground animate-pulse">Cargando...</span>
        )}
      </div>

      <div className="flex items-center gap-3">
        {lastSyncAt && (
          <span className="text-xs text-muted-foreground">
            Última sync: {formatRelativeTime(lastSyncAt)}
          </span>
        )}
        <Button
          size="sm"
          variant="outline"
          onClick={handleSync}
          className="h-8 gap-1.5 text-xs"
        >
          <RefreshCw size={13} />
          Sincronizar
        </Button>
      </div>
    </header>
  );
}
