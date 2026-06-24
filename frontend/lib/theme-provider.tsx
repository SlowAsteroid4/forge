"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export type Theme = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "forge-theme";

interface ThemeContextValue {
  /** User preference: light | dark | system */
  theme: Theme;
  /** Actual theme applied to the DOM (system resolved to light/dark) */
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
  /** Cycles light → dark → system → light */
  cycleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function getSystemTheme(): ResolvedTheme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function resolve(theme: Theme): ResolvedTheme {
  return theme === "system" ? getSystemTheme() : theme;
}

/**
 * Applies the resolved theme to <html> and animates the transition.
 * The `.theme-transition` class enables CSS color transitions only during
 * the switch, so it never interferes with hover/route transitions.
 */
function applyTheme(resolved: ResolvedTheme, animate: boolean) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;

  if (animate) {
    root.classList.add("theme-transition");
    window.clearTimeout((applyTheme as { _t?: number })._t);
    (applyTheme as { _t?: number })._t = window.setTimeout(() => {
      root.classList.remove("theme-transition");
    }, 450);
  }

  root.classList.toggle("dark", resolved === "dark");
  root.style.colorScheme = resolved;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  // Initial value is resolved on the client; the inline head script in
  // layout.tsx already applied the correct class before paint (no FOUC).
  const [theme, setThemeState] = useState<Theme>("system");
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>("light");

  // Hydrate preference from storage on mount.
  useEffect(() => {
    const stored = (localStorage.getItem(THEME_STORAGE_KEY) as Theme | null) ?? "system";
    setThemeState(stored);
    setResolvedTheme(resolve(stored));
  }, []);

  // React to OS theme changes while in "system" mode.
  useEffect(() => {
    if (theme !== "system") return;
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      const next = getSystemTheme();
      setResolvedTheme(next);
      applyTheme(next, true);
    };
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [theme]);

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
    localStorage.setItem(THEME_STORAGE_KEY, next);
    const resolved = resolve(next);
    setResolvedTheme(resolved);
    applyTheme(resolved, true);
  }, []);

  const cycleTheme = useCallback(() => {
    setThemeState((current) => {
      const order: Theme[] = ["light", "dark", "system"];
      const next = order[(order.indexOf(current) + 1) % order.length];
      localStorage.setItem(THEME_STORAGE_KEY, next);
      const resolved = resolve(next);
      setResolvedTheme(resolved);
      applyTheme(resolved, true);
      return next;
    });
  }, []);

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, resolvedTheme, setTheme, cycleTheme }),
    [theme, resolvedTheme, setTheme, cycleTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}
