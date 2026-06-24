"use client";

export function PulseExport() {
  const handleExport = () => {
    window.print();
  };

  return (
    <button
      onClick={handleExport}
      className="text-xs px-3 py-1.5 rounded border border-border text-muted-foreground hover:border-foreground/30 hover:text-foreground transition-colors"
      title="Exportar como PDF (Ctrl+P)"
    >
      Exportar PDF
    </button>
  );
}
