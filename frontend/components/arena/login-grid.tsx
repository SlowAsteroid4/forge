"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useArenaSession } from "@/lib/arena-session";
import type {
  ActivePlayerItem,
  ActivePlayersResponse,
  ArenaSessionProfile,
} from "@/lib/types/arena";
import { PixelAvatar, areaColor } from "./pixel-avatar";

/** A dónde mandar al player tras login según onboarding pendiente. */
function destinationFor(profile: ArenaSessionProfile): string {
  return profile.needs_onboarding ? "/arena/onboarding" : "/arena/home";
}

export function LoginGrid() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { session, login } = useArenaSession();

  const [players, setPlayers] = useState<ActivePlayerItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<number | null>(null);

  // Carga el roster de players activos (AC-9.7: inactivos no vienen del backend).
  useEffect(() => {
    let alive = true;
    api
      .get<ActivePlayersResponse>("/players/active")
      .then((res) => alive && setPlayers(res.players))
      .catch(() => alive && setError("No se pudo cargar el roster. ¿El backend está arriba?"));
    return () => {
      alive = false;
    };
  }, []);

  const doLogin = useCallback(
    async (playerId: number, opts?: { impersonation?: boolean }) => {
      setPendingId(playerId);
      try {
        const profile = await api.post<ArenaSessionProfile>("/arena/login", {
          player_id: playerId,
        });
        login(profile, { impersonation: opts?.impersonation });
        router.push(destinationFor(profile));
      } catch {
        setError("No se pudo iniciar sesión con esa identidad.");
        setPendingId(null);
      }
    },
    [login, router],
  );

  // Entrada de impersonación desde Ops (AC-9.8): /arena/login?as={id}
  useEffect(() => {
    const asId = searchParams.get("as");
    if (!asId) return;
    const id = Number(asId);
    if (Number.isInteger(id) && id > 0) {
      void doLogin(id, { impersonation: true });
    }
  }, [searchParams, doLogin]);

  function handleClick(player: ActivePlayerItem) {
    const current = session?.profile;
    if (!current) {
      void doLogin(player.id);
      return;
    }
    if (current.id === player.id) {
      router.push(destinationFor({ ...player, needs_onboarding: current.needs_onboarding }));
      return;
    }
    // Sesión con OTRO player → confirmar cambio (AC-9.3).
    const ok = window.confirm(
      `Ya hay sesión de ${current.display_name}. ¿Cambiar a ${player.display_name}?`,
    );
    if (ok) void doLogin(player.id);
  }

  // ── Estados de carga / error ──────────────────────────────────────────────
  if (error && !players) {
    return (
      <p className="text-center text-sm text-red-400 font-[family-name:var(--font-pixel)] leading-relaxed">
        {error}
      </p>
    );
  }
  if (!players) {
    return (
      <p className="text-center text-zinc-500 text-sm font-[family-name:var(--font-pixel)]">
        CARGANDO ROSTER<span className="arena-blink">_</span>
      </p>
    );
  }

  // Empty state (AC-9.10).
  if (players.length === 0) {
    return (
      <div className="mx-auto max-w-md text-center space-y-3 border-2 border-zinc-700 bg-black/40 px-8 py-10 arena-pixel-shadow">
        <p className="font-[family-name:var(--font-pixel)] text-amber-400 text-sm leading-relaxed">
          NO HAY PLAYERS ACTIVOS
        </p>
        <p className="text-zinc-400 text-sm">Contacta al PM para activar tu identidad.</p>
      </div>
    );
  }

  return (
    <>
      {error && (
        <p className="text-center text-xs text-red-400 mb-4">{error}</p>
      )}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {players.map((p) => {
          const isCurrent = session?.profile.id === p.id;
          const c = areaColor(p.area);
          const isPending = pendingId === p.id;
          return (
            <button
              key={p.id}
              onClick={() => handleClick(p)}
              disabled={isPending}
              className="arena-card group relative flex flex-col items-center gap-3 border-2 bg-black/40 px-4 py-5 text-center disabled:opacity-60"
              style={{ borderColor: isCurrent ? "#fbbf24" : "#3f3f46" }}
            >
              {isCurrent && (
                <span className="absolute right-1.5 top-1.5 font-[family-name:var(--font-pixel)] text-[8px] text-amber-400">
                  ● EN SESIÓN
                </span>
              )}
              <PixelAvatar name={p.display_name} area={p.area} size={64} />
              <div className="space-y-1.5">
                <p className="text-sm font-semibold leading-tight text-zinc-100">
                  {p.display_name}
                </p>
                <div className="flex items-center justify-center gap-2">
                  <span
                    className="font-[family-name:var(--font-pixel)] text-[8px] px-1.5 py-0.5"
                    style={{ backgroundColor: c.ring, color: "#0a0a0a" }}
                  >
                    {p.area}
                  </span>
                  <span className="font-[family-name:var(--font-pixel)] text-[8px] text-zinc-500">
                    {p.class_code ?? "SIN CLASE"}
                  </span>
                </div>
              </div>
              {isPending && (
                <span className="absolute inset-0 grid place-items-center bg-black/60 font-[family-name:var(--font-pixel)] text-[9px] text-amber-400">
                  ENTRANDO<span className="arena-blink">_</span>
                </span>
              )}
            </button>
          );
        })}
      </div>
    </>
  );
}
