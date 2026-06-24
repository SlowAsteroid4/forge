"use client";

import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { useArenaSession } from "@/lib/arena-session";
import { PixelAvatar } from "./pixel-avatar";

// Header global de Arena (AC-9.4). Visible en todas las vistas /arena/* cuando
// hay sesión. El botón LOGOUT siempre está presente. En la pantalla de login
// (sin sesión) no se muestra, para que el gateway sea limpio.
export function ArenaHeader() {
  const router = useRouter();
  const { session, logout } = useArenaSession();

  if (!session) return null;

  async function handleLogout() {
    await logout();
    router.push("/arena/login");
  }

  const p = session.profile;

  return (
    <header className="sticky top-0 z-40 flex items-center justify-between border-b-2 border-zinc-800 bg-black/70 px-4 py-2.5 backdrop-blur">
      <button
        onClick={() => router.push("/arena/home")}
        className="font-[family-name:var(--font-pixel)] text-sm text-amber-400 arena-glow"
      >
        FORGE ARENA
      </button>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <PixelAvatar name={p.display_name} area={p.area} size={28} />
          <span className="hidden text-sm text-zinc-200 sm:inline">{p.display_name}</span>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 border-2 border-zinc-700 bg-zinc-900 px-2.5 py-1 font-[family-name:var(--font-pixel)] text-[9px] text-zinc-300 transition-colors hover:border-red-500 hover:text-red-400"
        >
          <LogOut size={12} />
          LOGOUT
        </button>
      </div>
    </header>
  );
}
