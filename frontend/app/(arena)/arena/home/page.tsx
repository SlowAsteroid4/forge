"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useArenaSession } from "@/lib/arena-session";

// Stub mínimo de Arena Home. La vista real llega en WPs posteriores (perfil,
// leaderboard, etc.). Aquí solo confirma sesión y da un punto de aterrizaje.
export default function ArenaHomePage() {
  const router = useRouter();
  const { session, loading } = useArenaSession();

  useEffect(() => {
    if (!loading && !session) router.replace("/arena/login");
  }, [loading, session, router]);

  if (loading || !session) return null;

  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center gap-4 px-6 py-20 text-center">
      <h1 className="font-[family-name:var(--font-pixel)] text-xl text-amber-400 arena-glow">
        ¡BIENVENIDO, {session.profile.display_name.split(" ")[0].toUpperCase()}!
      </h1>
      <p className="text-sm text-zinc-400">
        Arena Home — próximamente. Aquí vivirán tu perfil, leaderboard y logros.
      </p>
      <span className="font-[family-name:var(--font-pixel)] text-[9px] text-zinc-600">
        ÁREA: {session.profile.area} · CLASE: {session.profile.class_code ?? "—"}
      </span>
    </div>
  );
}
