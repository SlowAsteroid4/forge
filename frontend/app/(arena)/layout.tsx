import type { Metadata } from "next";
import { Press_Start_2P } from "next/font/google";
import { ArenaSessionProvider } from "@/lib/arena-session";
import { ArenaHeader } from "@/components/arena/arena-header";
import { ImpersonationBanner } from "@/components/arena/impersonation-banner";

// Tipografía pixel-art arcade, expuesta como --font-pixel y usada vía
// `font-[var(--font-pixel)]` en títulos y etiquetas de Arena.
const pixel = Press_Start_2P({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-pixel",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Forge Arena",
};

export default function ArenaLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className={`${pixel.variable} arena-scene arena-scanlines flex min-h-full flex-col`}>
      <ArenaSessionProvider>
        <ImpersonationBanner />
        <ArenaHeader />
        <main className="flex-1">{children}</main>
      </ArenaSessionProvider>
    </div>
  );
}
