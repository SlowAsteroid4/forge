// Avatar placeholder pixel-art. El catálogo de avatars aún está vacío (UC-15),
// así que mostramos un monograma blocky con color por área. Cuando exista
// avatar_code real, este componente se reemplaza por el sprite.

const AREA_COLORS: Record<string, { bg: string; fg: string; ring: string }> = {
  BE: { bg: "#1e3a8a", fg: "#bfdbfe", ring: "#3b82f6" },
  FE: { bg: "#581c87", fg: "#e9d5ff", ring: "#a855f7" },
  DESIGN: { bg: "#831843", fg: "#fbcfe8", ring: "#ec4899" },
  DB: { bg: "#713f12", fg: "#fde68a", ring: "#eab308" },
  QA: { bg: "#14532d", fg: "#bbf7d0", ring: "#22c55e" },
  PO: { bg: "#374151", fg: "#e5e7eb", ring: "#9ca3af" },
  PM: { bg: "#7c2d12", fg: "#fed7aa", ring: "#f97316" },
};

export function areaColor(area: string) {
  return AREA_COLORS[area] ?? { bg: "#27272a", fg: "#d4d4d8", ring: "#52525b" };
}

export function PixelAvatar({
  name,
  area,
  size = 64,
}: {
  name: string;
  area: string;
  size?: number;
}) {
  const initial = name.trim().charAt(0).toUpperCase() || "?";
  const c = areaColor(area);
  return (
    <div
      className="arena-card-avatar grid place-items-center"
      style={{
        width: size,
        height: size,
        backgroundColor: c.bg,
        color: c.fg,
        border: `3px solid ${c.ring}`,
        imageRendering: "pixelated",
        boxShadow: `inset 0 0 0 3px rgba(0,0,0,0.35)`,
      }}
      aria-hidden
    >
      <span
        className="font-[family-name:var(--font-pixel)] leading-none"
        style={{ fontSize: size * 0.42 }}
      >
        {initial}
      </span>
    </div>
  );
}
