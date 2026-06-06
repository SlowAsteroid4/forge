"use client";

import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import type { ApartadoOption } from "@/lib/types/analytics";

interface ApartadoFilterProps {
  options: ApartadoOption[];
  current: string | null;
}

/**
 * Filtro GLOBAL por apartado (sub-división de YAP: [YPAPP]/[YPNX]/[PLD]…).
 * Cambia el searchParam `apartado` → la página re-fetchea TODAS las secciones.
 * "Todos" limpia el filtro. "Sin apartado" es una categoría de primera clase.
 */
export function ApartadoFilter({ options, current }: ApartadoFilterProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function select(apartado: string | null) {
    const params = new URLSearchParams(searchParams.toString());
    if (apartado === null) params.delete("apartado");
    else params.set("apartado", apartado);
    router.push(`${pathname}?${params.toString()}`);
  }

  const total = options.reduce((s, o) => s + o.subtask_count, 0);

  return (
    <div className="flex items-center gap-1 flex-wrap p-1 rounded-lg bg-muted w-fit">
      <button
        onClick={() => select(null)}
        title={`Todas las áreas del proyecto (${total})`}
        className={cn(
          "px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
          current === null
            ? "bg-background text-foreground shadow-sm"
            : "text-muted-foreground hover:text-foreground",
        )}
      >
        Todos
      </button>
      {options.map((opt) => (
        <button
          key={opt.apartado}
          onClick={() => select(opt.apartado)}
          title={`${opt.subtask_count} subtasks`}
          className={cn(
            "px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
            current === opt.apartado
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {opt.apartado}
          <span className="ml-1 text-[10px] text-muted-foreground">{opt.subtask_count}</span>
        </button>
      ))}
    </div>
  );
}
