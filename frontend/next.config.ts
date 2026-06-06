import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Oculta el indicador de desarrollo de Next.js (el botón "N" abajo a la izquierda).
  // Los errores de build/runtime se siguen mostrando. Solo aplica en `next dev`.
  devIndicators: false,
};

export default nextConfig;
