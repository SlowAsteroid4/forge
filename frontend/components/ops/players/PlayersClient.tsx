"use client";

import { useState } from "react";
import type { PlayerAdminItem, AreaEnum, EmploymentType } from "@/lib/types/players";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Pencil } from "lucide-react";
import { PlayerEditModal } from "./PlayerEditModal";

interface Props {
  initialPlayers: PlayerAdminItem[];
  total: number;
}

const AREAS: AreaEnum[] = ["BE", "FE", "DESIGN", "DB", "QA", "PO", "PM"];

function AreaBadge({ area }: { area: string }) {
  const colors: Record<string, string> = {
    BE: "bg-blue-100 text-blue-800",
    FE: "bg-purple-100 text-purple-800",
    DESIGN: "bg-pink-100 text-pink-800",
    DB: "bg-yellow-100 text-yellow-800",
    QA: "bg-green-100 text-green-800",
    PO: "bg-gray-100 text-gray-700",
    PM: "bg-orange-100 text-orange-800",
  };
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${colors[area] ?? "bg-muted text-muted-foreground"}`}
    >
      {area}
    </span>
  );
}

function formatCost(value: number | null): string {
  if (value === null) return "—";
  return `$${value.toLocaleString("es-MX", { minimumFractionDigits: 0 })}`;
}

export function PlayersClient({ initialPlayers, total }: Props) {
  const [players, setPlayers] = useState(initialPlayers);
  const [editingPlayer, setEditingPlayer] = useState<PlayerAdminItem | null>(null);
  const [filterArea, setFilterArea] = useState<string>("all");
  const [filterType, setFilterType] = useState<string>("all");
  const [filterActive, setFilterActive] = useState<string>("all");

  const filtered = players.filter((p) => {
    if (filterArea !== "all" && p.area !== filterArea) return false;
    if (filterType !== "all" && p.employment_type !== filterType) return false;
    if (filterActive === "active" && !p.is_active) return false;
    if (filterActive === "inactive" && p.is_active) return false;
    return true;
  });

  function handleSaved(updated: PlayerAdminItem) {
    setPlayers((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
    setEditingPlayer(null);
  }

  return (
    <>
      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <Select value={filterArea} onValueChange={(v) => setFilterArea(v ?? "all")}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="Área" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas las áreas</SelectItem>
            {AREAS.map((a) => (
              <SelectItem key={a} value={a}>
                {a}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={filterType} onValueChange={(v) => setFilterType(v ?? "all")}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="Tipo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos los tipos</SelectItem>
            <SelectItem value="internal">Interno</SelectItem>
            <SelectItem value="external">Externo</SelectItem>
          </SelectContent>
        </Select>

        <Select value={filterActive} onValueChange={(v) => setFilterActive(v ?? "all")}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="Estado" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="active">Activos</SelectItem>
            <SelectItem value="inactive">Inactivos</SelectItem>
          </SelectContent>
        </Select>

        <span className="text-sm text-muted-foreground ml-auto">
          {filtered.length} de {total} players
        </span>
      </div>

      {/* Table */}
      <div className="rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-muted-foreground">
            <tr>
              <th className="text-left px-4 py-2 font-medium">Nombre</th>
              <th className="text-left px-4 py-2 font-medium">Área</th>
              <th className="text-left px-4 py-2 font-medium">Tipo</th>
              <th className="text-left px-4 py-2 font-medium">Estado</th>
              <th className="text-left px-4 py-2 font-medium">Lead</th>
              <th className="text-right px-4 py-2 font-medium">Salario/mes</th>
              <th className="text-right px-4 py-2 font-medium">Tarifa/h</th>
              <th className="w-10 px-2 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filtered.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-muted-foreground text-sm">
                  Sin resultados con los filtros actuales.
                </td>
              </tr>
            )}
            {filtered.map((p) => (
              <tr key={p.id} className="hover:bg-muted/30 transition-colors">
                <td className="px-4 py-2.5">
                  <div className="font-medium">{p.display_name}</div>
                  {p.email && (
                    <div className="text-xs text-muted-foreground">{p.email}</div>
                  )}
                </td>
                <td className="px-4 py-2.5">
                  <AreaBadge area={p.area} />
                </td>
                <td className="px-4 py-2.5">
                  <Badge variant={p.employment_type === "external" ? "outline" : "secondary"}>
                    {p.employment_type === "internal" ? "Interno" : "Externo"}
                  </Badge>
                </td>
                <td className="px-4 py-2.5">
                  <span
                    className={`inline-flex h-2 w-2 rounded-full mr-1.5 ${p.is_active ? "bg-green-500" : "bg-muted-foreground"}`}
                  />
                  <span className={p.is_active ? "" : "text-muted-foreground"}>
                    {p.is_active ? "Activo" : "Inactivo"}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-center">
                  {p.is_lead ? (
                    <Badge variant="secondary" className="text-xs">Lead</Badge>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-xs">
                  {formatCost(p.monthly_salary)}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-xs">
                  {formatCost(p.hourly_rate)}
                </td>
                <td className="px-2 py-2.5">
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7"
                    onClick={() => setEditingPlayer(p)}
                  >
                    <Pencil size={13} />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editingPlayer && (
        <PlayerEditModal
          player={editingPlayer}
          onClose={() => setEditingPlayer(null)}
          onSaved={handleSaved}
        />
      )}
    </>
  );
}
