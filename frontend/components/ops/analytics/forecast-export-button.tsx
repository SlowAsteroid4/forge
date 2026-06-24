"use client";

import { Download } from "lucide-react";

interface ForecastExportButtonProps {
  apiBase: string;
  projectCode?: string;
  epicStatus?: string;
}

export function ForecastExportButton({
  apiBase,
  projectCode,
  epicStatus,
}: ForecastExportButtonProps) {
  function handleExport() {
    const params = new URLSearchParams();
    if (projectCode) params.set("project_code", projectCode);
    if (epicStatus) params.set("epic_status", epicStatus);
    const url = `${apiBase}/forecast/epics.csv${params.size ? `?${params}` : ""}`;
    const a = document.createElement("a");
    a.href = url;
    a.download = "forecast.csv";
    a.click();
  }

  return (
    <button
      onClick={handleExport}
      className="h-8 px-3 text-xs rounded-md border border-border bg-background hover:bg-accent flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
    >
      <Download size={12} />
      Exportar CSV
    </button>
  );
}
