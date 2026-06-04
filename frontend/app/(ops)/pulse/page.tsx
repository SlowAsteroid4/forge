import type { PulseSnapshot } from "@/lib/types/pulse";
import { PulseClient } from "@/components/ops/pulse/pulse-client";

export const dynamic = "force-dynamic";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

interface PageProps {
  searchParams: Promise<{
    area?: string | string[];
    project_code?: string;
    player_id?: string;
  }>;
}

async function fetchPulse(
  areas: string[],
  projectCode?: string,
  playerId?: string,
): Promise<PulseSnapshot | null> {
  try {
    const params = new URLSearchParams();
    for (const a of areas) params.append("area", a);
    if (projectCode) params.set("project_code", projectCode);
    if (playerId) params.set("player_id", playerId);
    const query = params.toString() ? `?${params}` : "";
    const res = await fetch(`${API_BASE}/pulse/now${query}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json() as Promise<PulseSnapshot>;
  } catch {
    return null;
  }
}

export default async function PulsePage({ searchParams }: PageProps) {
  const sp = await searchParams;
  const rawAreas = sp.area;
  const areas = rawAreas ? (Array.isArray(rawAreas) ? rawAreas : [rawAreas]) : [];
  const projectCode = sp.project_code;
  const playerId = sp.player_id;

  const pulse = await fetchPulse(areas, projectCode, playerId);

  return (
    <PulseClient
      initialPulse={pulse}
      initialFilters={{ areas, projectCode: projectCode ?? null, playerId: playerId ?? null }}
    />
  );
}
