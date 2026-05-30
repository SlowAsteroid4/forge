import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { PlayerStatus, DevStatus } from "@/lib/types/dashboard";

const STATUS_CONFIG: Record<DevStatus, { label: string; emoji: string }> = {
  productive: { label: "Productivo", emoji: "🟢" },
  wip_high: { label: "WIP alto", emoji: "🟡" },
  blocked: { label: "Bloqueado", emoji: "🔴" },
  inactive: { label: "Inactivo", emoji: "⚪" },
};

const AREA_LABELS: Record<string, string> = {
  BE: "Backend",
  FE: "Frontend",
  DESIGN: "Design",
  DB: "Database",
  QA: "Quality",
  PO: "Product Owner",
  PM: "PM",
};

interface DevTableProps {
  players: PlayerStatus[];
}

export function DevTable({ players }: DevTableProps) {
  if (players.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4 text-center">
        No hay devs activos en este sprint.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Dev</TableHead>
          <TableHead>Área</TableHead>
          <TableHead className="text-center">Activas</TableHead>
          <TableHead className="text-center">Done</TableHead>
          <TableHead className="text-right">SP</TableHead>
          <TableHead>Estado</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {players.map((p) => {
          const statusCfg = STATUS_CONFIG[p.status] ?? { label: p.status, emoji: "⚪" };
          return (
            <TableRow key={p.player_id}>
              <TableCell className="font-medium text-sm">{p.display_name}</TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {AREA_LABELS[p.area] ?? p.area}
              </TableCell>
              <TableCell className="text-center tabular-nums text-sm">{p.active_subtasks}</TableCell>
              <TableCell className="text-center tabular-nums text-sm">{p.done_subtasks}</TableCell>
              <TableCell className="text-right tabular-nums text-sm font-medium">
                {p.sp_sprint.toFixed(1)}
              </TableCell>
              <TableCell>
                <span className="text-xs">
                  {statusCfg.emoji} {statusCfg.label}
                </span>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
