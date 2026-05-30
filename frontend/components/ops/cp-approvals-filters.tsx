"use client";

import { useRouter, useSearchParams, usePathname } from "next/navigation";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface ApprovalFiltersProps {
  areas: string[];
  projects: string[];
}

const ALL = "_all";

export function ApprovalFilters({ areas, projects }: ApprovalFiltersProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function update(key: string, value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value && value !== ALL) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    router.push(`${pathname}?${params.toString()}`);
  }

  const areaValue = searchParams.get("area") ?? ALL;
  const projectValue = searchParams.get("project_code") ?? ALL;
  const hasFilters = areas.length > 1 || projects.length > 1;

  if (!hasFilters) return null;

  return (
    <div className="flex gap-2 flex-wrap">
      {areas.length > 1 && (
        <Select
          value={areaValue}
          onValueChange={(v) => update("area", v as string)}
        >
          <SelectTrigger size="sm" className="w-36">
            <SelectValue placeholder="Todas las áreas" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todas las áreas</SelectItem>
            {areas.map((a) => (
              <SelectItem key={a} value={a}>
                {a}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
      {projects.length > 1 && (
        <Select
          value={projectValue}
          onValueChange={(v) => update("project_code", v as string)}
        >
          <SelectTrigger size="sm" className="w-36">
            <SelectValue placeholder="Todos los proyectos" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todos los proyectos</SelectItem>
            {projects.map((p) => (
              <SelectItem key={p} value={p}>
                {p}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
    </div>
  );
}
