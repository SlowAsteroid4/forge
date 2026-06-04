import { Suspense } from "react";
import type { AnalyticsScope } from "@/lib/types/analytics";
import type {
  ThroughputResponse,
  CpByAreaResponse,
  CpPerDayResponse,
  QaFirstPassResponse,
  TimeInStatusResponse,
  TimeInStatusDetailResponse,
} from "@/lib/types/analytics";
import { BottleneckHero } from "@/components/ops/analytics/bottleneck-hero";
import { TimeInStatusChart } from "@/components/ops/analytics/time-in-status-chart";
import { ThroughputChart } from "@/components/ops/analytics/throughput-chart";
import { CpByAreaChart } from "@/components/ops/analytics/cp-by-area-chart";
import { CpPerDayChart } from "@/components/ops/analytics/cp-per-day-chart";
import { QaFirstPassChart } from "@/components/ops/analytics/qa-first-pass-chart";
import { ScopeSelector } from "@/components/ops/analytics/scope-selector";

export const dynamic = "force-dynamic";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json() as Promise<T>;
  } catch {
    return null;
  }
}

interface PageProps {
  searchParams: Promise<{ scope?: string }>;
}

export default async function AnalyticsFlowPage({ searchParams }: PageProps) {
  const { scope: rawScope } = await searchParams;
  const scope: AnalyticsScope =
    rawScope === "cycle" || rawScope === "window" || rawScope === "historical"
      ? rawScope
      : "window";

  // Endpoints 2+3 don't support historical — fall back to window
  const partialScope = scope === "historical" ? "window" : scope;
  const usesWindowFallback = scope === "historical";

  // Throughput: last_n based on scope
  const lastN = scope === "historical" ? 20 : scope === "window" ? 8 : 4;

  // Fetch all endpoints in parallel — each fails independently
  const [throughput, cpByArea, cpPerDay, qaFirstPass, timeInStatus, timeInStatusDetail] =
    await Promise.all([
      fetchJson<ThroughputResponse>(`${API_BASE}/analytics/throughput?last_n=${lastN}`),
      fetchJson<CpByAreaResponse>(`${API_BASE}/analytics/cp-by-area?scope=${partialScope}`),
      fetchJson<CpPerDayResponse>(`${API_BASE}/analytics/cp-per-day-by-dev?scope=${partialScope}`),
      fetchJson<QaFirstPassResponse>(`${API_BASE}/analytics/qa-first-pass-by-dev?scope=${scope}`),
      fetchJson<TimeInStatusResponse>(
        `${API_BASE}/analytics/time-in-status?scope=${scope}&group_by=area`,
      ),
      fetchJson<TimeInStatusDetailResponse>(
        `${API_BASE}/analytics/time-in-status-detail?scope=${scope}&group_by=area`,
      ),
    ]);

  const scopeLabel =
    scope === "cycle" ? "Ciclo activo" : scope === "window" ? "Ventana móvil (4 ciclos)" : "Histórico";

  return (
    <div className="flex flex-col flex-1 overflow-auto">
      {/* Header */}
      <div className="border-b border-border px-6 py-4 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-base font-semibold">Métricas de flujo</h1>
          <p className="text-xs text-muted-foreground">
            {scopeLabel} — cuellos de botella, throughput, calidad
          </p>
        </div>
        <Suspense>
          <ScopeSelector currentScope={scope} />
        </Suspense>
      </div>

      <div className="flex-1 p-6 space-y-6">
        {/* HERO — Cuello de botella */}
        <section>
          {timeInStatusDetail ? (
            <BottleneckHero rows={timeInStatusDetail.rows} />
          ) : (
            <ErrorCard title="Cuello de botella" />
          )}
        </section>

        {/* Time-in-status stacked chart */}
        <section>
          <SectionHeader
            title="Tiempo por estado y área"
            subtitle="Horas acumuladas por bucket de estado (barras apiladas). ¿Dónde se atasca el trabajo?"
          />
          {timeInStatus ? (
            <div className="rounded-lg border border-border bg-card p-4">
              <TimeInStatusChart rows={timeInStatus.rows} />
            </div>
          ) : (
            <ErrorCard title="Time-in-status" />
          )}
        </section>

        {/* Throughput + CP per day side by side */}
        <div className="grid grid-cols-2 gap-4">
          <section>
            <SectionHeader
              title="Throughput por ciclo"
              subtitle="¿Cuánto entregamos por semana? (subtasks Done + CP)"
            />
            {throughput ? (
              <div className="rounded-lg border border-border bg-card p-4">
                <ThroughputChart cycles={throughput.cycles} />
              </div>
            ) : (
              <ErrorCard title="Throughput" />
            )}
          </section>

          <section>
            <SectionHeader
              title="Velocity CP/día"
              subtitle="¿A qué ritmo de CP avanza cada dev? (normalizado por días hábiles)"
            />
            {cpPerDay ? (
              <div className="rounded-lg border border-border bg-card p-4">
                <CpPerDayChart
                  devs={cpPerDay.devs}
                  bizDays={cpPerDay.biz_days}
                  usesWindowFallback={usesWindowFallback}
                />
              </div>
            ) : (
              <ErrorCard title="CP/día" />
            )}
          </section>
        </div>

        {/* CP by area */}
        <section>
          <SectionHeader
            title="CP por área"
            subtitle="¿Dónde se concentra el esfuerzo? (CP totales Done)"
          />
          {cpByArea ? (
            <div className="rounded-lg border border-border bg-card p-4">
              <CpByAreaChart areas={cpByArea.areas} usesWindowFallback={usesWindowFallback} />
            </div>
          ) : (
            <ErrorCard title="CP por área" />
          )}
        </section>

        {/* QA first-pass — full width */}
        <section>
          <SectionHeader
            title="QA first-pass por dev"
            subtitle="¿Qué % de subtasks pasan QA al primer intento? Verde ≥80%, amarillo 50–79%, rojo <50%"
          />
          {qaFirstPass ? (
            <div className="rounded-lg border border-border bg-card p-4">
              <QaFirstPassChart devs={qaFirstPass.devs} />
            </div>
          ) : (
            <ErrorCard title="QA first-pass" />
          )}
        </section>
      </div>
    </div>
  );
}

function SectionHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="mb-2">
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="text-[11px] text-muted-foreground">{subtitle}</p>
    </div>
  );
}

function ErrorCard({ title }: { title: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border p-6 text-center">
      <p className="text-sm text-muted-foreground">No se pudo cargar: {title}</p>
    </div>
  );
}
