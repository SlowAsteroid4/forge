"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { useTheme, type Theme } from "@/lib/theme-provider";

const OPTIONS: { value: Theme; label: string; icon: React.ReactNode }[] = [
  { value: "light", label: "Claro", icon: <Sun size={15} /> },
  { value: "dark", label: "Oscuro", icon: <Moon size={15} /> },
  { value: "system", label: "Sistema", icon: <Monitor size={15} /> },
];

export function ThemeToggle() {
  const { theme, resolvedTheme, setTheme } = useTheme();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            size="sm"
            variant="outline"
            className="h-8 w-8 p-0"
            aria-label="Cambiar tema"
          />
        }
      >
        {/* Sun/Moon cross-fade based on the actually applied theme */}
        <span className="relative inline-flex h-[15px] w-[15px] items-center justify-center">
          <Sun
            size={15}
            className={cn(
              "absolute transition-all duration-300",
              resolvedTheme === "dark"
                ? "scale-0 -rotate-90 opacity-0"
                : "scale-100 rotate-0 opacity-100",
            )}
          />
          <Moon
            size={15}
            className={cn(
              "absolute transition-all duration-300",
              resolvedTheme === "dark"
                ? "scale-100 rotate-0 opacity-100"
                : "scale-0 rotate-90 opacity-0",
            )}
          />
        </span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-36">
        {OPTIONS.map((opt) => (
          <DropdownMenuItem
            key={opt.value}
            onClick={() => setTheme(opt.value)}
            className={cn(
              "gap-2",
              theme === opt.value && "bg-accent text-accent-foreground",
            )}
          >
            {opt.icon}
            <span className="flex-1">{opt.label}</span>
            {theme === opt.value && (
              <span className="size-1.5 rounded-full bg-foreground/60" />
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
