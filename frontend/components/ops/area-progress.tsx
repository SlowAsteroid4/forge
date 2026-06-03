import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle } from "lucide-react";
import type { AreaProgress } from "@/lib/types/dashboard";

const AREA_LABELS: Record<string, string> = {
  BE: "Backend",
  FE: "Frontend",
  DESIGN: "Design",
  DB: "Database",
  QA: "Quality",
};

interface AreaProgressGridProps {
  areas: AreaProgress[];
}

export function AreaProgressGrid({ areas }: AreaProgressGridProps) {
  return (
    <div className="grid grid-cols-5 gap-3">
      {areas.map((area) => (
        <Card key={area.area} className="relative">
          {area.has_wip_bottleneck && (
            <div className="absolute top-2 right-2">
              <AlertTriangle size={13} className="text-amber-500" />
            </div>
          )}
          <CardContent className="p-3">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-semibold">{AREA_LABELS[area.area] ?? area.area}</span>
              <Badge variant="outline" className="text-[10px] h-4 px-1">
                {area.active_devs} dev{area.active_devs !== 1 ? "s" : ""}
              </Badge>
            </div>
            <p className="text-2xl font-bold tabular-nums">{area.cp_done}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">CP esta semana</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
