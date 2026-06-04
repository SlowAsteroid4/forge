"use client";

import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import type { AnalyticsScope } from "@/lib/types/analytics";

interface ScopeOption {
  value: AnalyticsScope;
  label: string;
  description: string;
}

const SCOPE_OPTIONS: ScopeOption[] = [
  {
    value: "cycle",
    label: "Ciclo activo",
    description: "Semana en curso",
  },
  {
    value: "window",
    label: "Ventana móvil",
    description: "4 ciclos cerrados",
  },
  {
    value: "historical",
    label: "Histórico",
    description: "Todo el tiempo",
  },
];

interface ScopeSelectorProps {
  currentScope: AnalyticsScope;
}

export function ScopeSelector({ currentScope }: ScopeSelectorProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function selectScope(scope: AnalyticsScope) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("scope", scope);
    router.push(`${pathname}?${params.toString()}`);
  }

  return (
    <div className="flex items-center gap-1 p-1 rounded-lg bg-muted w-fit">
      {SCOPE_OPTIONS.map((opt) => (
        <button
          key={opt.value}
          onClick={() => selectScope(opt.value)}
          title={opt.description}
          className={cn(
            "px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
            currentScope === opt.value
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
