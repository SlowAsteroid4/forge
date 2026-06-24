"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useArenaSession } from "@/lib/arena-session";

// STUB de onboarding (UC-15, WP aparte). El login redirige aquí cuando falta
// clase o avatar (needs_onboarding=true). La pantalla real — selección de clase
// y avatar — se construye después; por ahora no rompe el flujo.
export default function ArenaOnboardingPage() {
  const router = useRouter();
  const { session, loading } = useArenaSession();

  useEffect(() => {
    if (!loading && !session) router.replace("/arena/login");
  }, [loading, session, router]);

  if (loading || !session) return null;

  return (
    <div className="mx-auto flex max-w-xl flex-col items-center gap-5 px-6 py-20 text-center">
      <h1 className="font-[family-name:var(--font-pixel)] text-lg text-amber-400 arena-glow">
        ONBOARDING
      </h1>
      <div className="border-2 border-zinc-700 bg-black/40 px-8 py-8 arena-pixel-shadow">
        <p className="font-[family-name:var(--font-pixel)] text-[10px] leading-relaxed text-zinc-300">
          ELIGE TU CLASE Y AVATAR
        </p>
        <p className="mt-3 text-sm text-zinc-500">Próximamente — UC-15.</p>
      </div>
      <button
        onClick={() => router.push("/arena/home")}
        className="font-[family-name:var(--font-pixel)] text-[9px] text-zinc-400 underline underline-offset-2 hover:text-amber-400"
      >
        SALTAR POR AHORA →
      </button>
    </div>
  );
}
