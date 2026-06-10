"use client";

import { useRouter } from "next/navigation";
import { Eye } from "lucide-react";
import { useArenaSession } from "@/lib/arena-session";

// Banner de impersonación (AC-9.8). Cuando el PM entra a Arena vía "ver como"
// desde Ops, la sesión queda marcada con impersonation=true. El banner es claro
// y persistente; "Salir" limpia la sesión y vuelve a Ops (admin de players).
// NO toca el admin_id de Ops; es solo visualización de Arena.
export function ImpersonationBanner() {
  const router = useRouter();
  const { session, logout } = useArenaSession();

  if (!session?.impersonation) return null;

  async function handleExit() {
    await logout();
    router.push("/admin/players");
  }

  return (
    <div className="flex items-center justify-center gap-3 border-b-2 border-amber-500/60 bg-amber-500/15 px-4 py-1.5 text-center">
      <Eye size={14} className="text-amber-400" />
      <span className="text-xs text-amber-200">
        Viendo como <strong className="text-amber-300">{session.profile.display_name}</strong>{" "}
        (impersonación)
      </span>
      <button
        onClick={handleExit}
        className="font-[family-name:var(--font-pixel)] text-[9px] text-amber-300 underline underline-offset-2 hover:text-amber-100"
      >
        SALIR
      </button>
    </div>
  );
}
