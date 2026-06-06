"use client";

import { Download } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

interface Props {
  period: string;
  projectCode?: string;
}

export function CostExportButton({ period, projectCode }: Props) {
  const handleExport = () => {
    const params = new URLSearchParams({ period });
    if (projectCode) params.set("project_code", projectCode);
    window.location.href = `${API_BASE}/costs/by-area.csv?${params}`;
  };

  return (
    <button
      onClick={handleExport}
      className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-border bg-background hover:bg-muted/50 transition-colors"
    >
      <Download size={13} />
      Exportar CSV
    </button>
  );
}
