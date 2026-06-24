"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";
import { ApplyPenaltyModal } from "@/components/ops/penalties/ApplyPenaltyModal";
import { PenaltyTable } from "@/components/ops/penalties/PenaltyTable";
import type { PenaltyListItem, DebuffCatalogItem } from "@/lib/types/penalties";

interface Props {
  items: PenaltyListItem[];
  catalog: DebuffCatalogItem[];
  total: number;
}

export function PenaltiesClient({ items, catalog, total }: Props) {
  const [showApply, setShowApply] = useState(false);

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold flex items-center gap-2">
            <AlertTriangle size={18} className="text-orange-500" />
            Penalizaciones
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            {total} penalización{total !== 1 ? "es" : ""} registrada
            {total !== 1 ? "s" : ""}
          </p>
        </div>
        <Button
          size="sm"
          variant="destructive"
          onClick={() => setShowApply(true)}
        >
          + Aplicar penalización
        </Button>
      </div>

      <PenaltyTable items={items} />

      <ApplyPenaltyModal
        open={showApply}
        onClose={() => setShowApply(false)}
        catalog={catalog}
      />
    </>
  );
}
