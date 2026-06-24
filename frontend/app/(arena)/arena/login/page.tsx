import { Suspense } from "react";
import { LoginGrid } from "@/components/arena/login-grid";

// Gateway de Arena (AC-9.1): vista pública, sin sesión previa.
export default function ArenaLoginPage() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col items-center gap-10 px-6 py-12">
      <div className="space-y-4 text-center">
        <h1 className="font-[family-name:var(--font-pixel)] text-3xl text-amber-400 arena-glow sm:text-4xl">
          FORGE ARENA
        </h1>
        <p className="font-[family-name:var(--font-pixel)] text-[10px] leading-relaxed text-zinc-400">
          SELECCIONA TU IDENTIDAD<span className="arena-blink">_</span>
        </p>
        <p className="text-sm text-zinc-500">Toca tu carta para entrar a la Arena.</p>
      </div>

      <div className="w-full">
        <Suspense
          fallback={
            <p className="text-center font-[family-name:var(--font-pixel)] text-sm text-zinc-500">
              CARGANDO<span className="arena-blink">_</span>
            </p>
          }
        >
          <LoginGrid />
        </Suspense>
      </div>
    </div>
  );
}
