"use client";

// Sesión de Arena en el cliente (UC-09 / AC-9.4).
//
// No hay sesión de servidor ni passwords: el "login" es selección de identidad.
// El perfil se persiste en localStorage, así que cerrar el navegador NO cierra
// sesión. localStorage está confirmado en este Next.js real (lo usa también
// lib/theme-provider.tsx).

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { api } from "@/lib/api";
import type { ArenaSession, ArenaSessionProfile } from "@/lib/types/arena";

const STORAGE_KEY = "forge-arena-session";

interface ArenaSessionContextValue {
  session: ArenaSession | null;
  /** True hasta que se hidrata desde localStorage (evita parpadeo en SSR/mount). */
  loading: boolean;
  /** Inicia sesión con un perfil ya validado por el backend. */
  login: (profile: ArenaSessionProfile, opts?: { impersonation?: boolean }) => void;
  /** Cierra sesión: limpia el cliente + registra trazabilidad en el backend. */
  logout: () => Promise<void>;
}

const ArenaSessionContext = createContext<ArenaSessionContextValue | null>(null);

function readStored(): ArenaSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ArenaSession;
    if (!parsed?.profile?.id) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function ArenaSessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<ArenaSession | null>(null);
  const [loading, setLoading] = useState(true);

  // Hidrata desde localStorage en el mount (cliente).
  useEffect(() => {
    setSession(readStored());
    setLoading(false);
  }, []);

  const login = useCallback(
    (profile: ArenaSessionProfile, opts?: { impersonation?: boolean }) => {
      const next: ArenaSession = { profile, impersonation: opts?.impersonation ?? false };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // si localStorage falla, la sesión vive solo en memoria de esta pestaña
      }
      setSession(next);
    },
    [],
  );

  const logout = useCallback(async () => {
    const playerId = session?.profile.id ?? null;
    setSession(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* noop */
    }
    // Trazabilidad: registra el logout en audit_log (no hay sesión de servidor).
    try {
      await api.post("/arena/logout", { player_id: playerId });
    } catch {
      // el logout del cliente ya ocurrió; el backend es solo trazabilidad
    }
  }, [session]);

  const value = useMemo<ArenaSessionContextValue>(
    () => ({ session, loading, login, logout }),
    [session, loading, login, logout],
  );

  return (
    <ArenaSessionContext.Provider value={value}>{children}</ArenaSessionContext.Provider>
  );
}

export function useArenaSession(): ArenaSessionContextValue {
  const ctx = useContext(ArenaSessionContext);
  if (!ctx) throw new Error("useArenaSession debe usarse dentro de <ArenaSessionProvider>");
  return ctx;
}
