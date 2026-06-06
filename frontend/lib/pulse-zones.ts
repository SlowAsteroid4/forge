import type { PulseZone } from "@/lib/types/pulse";

/**
 * Estilos por zona de color JPDS (paleta WP-07b time-in-status, por zona):
 *   dev #60A5FA · review #C7D2FE · qa #FCA5A5 · blocked #F87171 · neutral #E5E7EB
 *
 * Cada fila de tarea se colorea según el estado mediante una franja izquierda
 * (border-l) + fondo tenue. Reemplaza el semáforo de WIP del diseño anterior.
 */
export const ZONE_ROW: Record<PulseZone, string> = {
  dev: "border-l-blue-400 bg-blue-400/5",
  review: "border-l-indigo-300 bg-indigo-300/5",
  qa: "border-l-rose-300 bg-rose-300/5",
  blocked: "border-l-red-500 bg-red-500/10",
  neutral: "border-l-slate-300 bg-slate-300/5",
  done: "border-l-emerald-400 bg-emerald-400/5",
};

/** Punto/chip de color sólido por zona (para la franja de contadores). */
export const ZONE_DOT: Record<PulseZone, string> = {
  dev: "bg-blue-400",
  review: "bg-indigo-300",
  qa: "bg-rose-300",
  blocked: "bg-red-500",
  neutral: "bg-slate-300",
  done: "bg-emerald-400",
};

/** Texto de color por zona (para el número del contador). */
export const ZONE_TEXT: Record<PulseZone, string> = {
  dev: "text-blue-500",
  review: "text-indigo-400",
  qa: "text-rose-400",
  blocked: "text-red-500",
  neutral: "text-slate-500",
  done: "text-emerald-500",
};
