import { Suspense } from "react";
import type { AnalyticsScope } from "@/lib/types/analytics";
import type {
  ThroughputResponse,
  CpByAreaResponse,
  CpPerDayResponse,
  TimeInStatusDetailResponse,
  QualitySummaryResponse,
  QaFirstPassVsPreviousResponse,
  CanonicalTimeResponse,
  ApartadosResponse,
  DevListResponse,
} from "@/lib/types/analytics";
import { BottleneckHero, DELIVERY_AREAS } from "@/components/ops/analytics/bottleneck-hero";
import { CanonicalTimeBars } from "@/components/ops/analytics/canonical-time-bars";
import { ThroughputChart } from "@/components/ops/analytics/throughput-chart";
import { CpByAreaChart } from "@/components/ops/analytics/cp-by-area-chart";
import { CpPerDayChart } from "@/components/ops/analytics/cp-per-day-chart";
import { QualityCards } from "@/components/ops/analytics/quality-cards";
import { QaFirstPassVsPrevious } from "@/components/ops/analytics/qa-first-pass-vs-previous";
import { ScopeSelector } from "@/components/ops/analytics/scope-selector";
import { ApartadoFilter } from "@/components/ops/analytics/apartado-filter";
import { CycleLeadChart } from "@/components/ops/analytics/cycle-lead-chart";
import { DevMetricsPanel } from "@/components/ops/analytics/dev-metrics-panel";

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
  searchParams: Promise<{ scope?: string; apartado?: string }>;
}

export default async function AnalyticsFlowPage({ searchParams }: PageProps) {
  const { scope: rawScope, apartado: rawApartado } = await searchParams;
  const scope: AnalyticsScope =
    rawScope === "cycle" || rawScope === "window" || rawScope === "historical"
      ? rawScope
      : "window";

  // Filtro GLOBAL por apartado (sub-división de YAP). null = todos.
  const apartado = rawApartado && rawApartado.trim() ? rawApartado : null;
  const apQ = apartado ? `&apartado=${encodeURIComponent(apartado)}` : "";

  // Endpoints CP no soportan historical — fallback a window
  const partialScope = scope === "historical" ? "window" : scope;
  const usesWindowFallback = scope === "historical";

  const lastN = scope === "historical" ? 20 : scope === "window" ? 8 : 4;

  const [
    throughput,
    cpByArea,
    cpPerDay,
    bottleneckDetail,
    quality,
    qaVsPrev,
    canonByArea,
    canonDesign,
    apartados,
    devList,
  ] = await Promise.all([
    fetchJson<ThroughputResponse>(`${API_BASE}/analytics/throughput?last_n=${lastN}${apQ}`),
    fetchJson<CpByAreaResponse>(`${API_BASE}/analytics/cp-by-area?scope=${partialScope}${apQ}`),
    fetchJson<CpPerDayResponse>(
      `${API_BASE}/analytics/cp-per-day-by-dev?scope=${partialScope}${apQ}`,
    ),
    fetchJson<TimeInStatusDetailResponse>(
      `${API_BASE}/analytics/time-in-status-detail?scope=${scope}&group_by=area${apQ}`,
    ),
    fetchJson<QualitySummaryResponse>(`${API_BASE}/analytics/quality?${apQ.slice(1)}`),
    fetchJson<QaFirstPassVsPreviousResponse>(
      `${API_BASE}/analytics/qa-first-pass-vs-previous?${apQ.slice(1)}`,
    ),
    fetchJson<CanonicalTimeResponse>(
      `${API_BASE}/analytics/time-canonical?scope=${scope}&group_by=area${apQ}`,
    ),
    fetchJson<CanonicalTimeResponse>(
      `${API_BASE}/analytics/time-canonical?scope=${scope}&group_by=player&area=DESIGN${apQ}`,
    ),
    fetchJson<ApartadosResponse>(`${API_BASE}/analytics/apartados`),
    fetchJson<DevListResponse>(`${API_BASE}/analytics/dev-list?scope=${scope}${apQ}`),
  ]);

  const scopeLabel =
    scope === "cycle" ? "Ciclo activo" : scope === "window" ? "Ventana móvil (4 ciclos)" : "Histórico";

  return (
    <div className="flex flex-col flex-1 overflow-auto">
      {/* Header */}
      <div className="border-b border-border px-6 py-4 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-base font-semibold">Métricas de flujo</h1>
          <p className="text-xs text-muted-foreground">
            {scopeLabel}
            {apartado ? ` · ${apartado}` : ""} — calidad, cuellos de botella, tiempos
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {apartados && apartados.apartados.length > 0 && (
            <Suspense>
              <ApartadoFilter options={apartados.apartados} current={apartado} />
            </Suspense>
          )}
          <Suspense>
            <ScopeSelector currentScope={scope} />
          </Suspense>
        </div>
      </div>

      <div className="flex-1 p-6 space-y-8">
        {/* ───────── QUALITY (sección propia) ───────── */}
        <section className="space-y-4">
          <SectionHeader
            title="Calidad (QA)"
            subtitle="Tarjetas probadas, en cola y tiempo en QA — comparado contra el ciclo anterior."
          />
          {quality ? <QualityCards data={quality} /> : <ErrorCard title="Quality" />}

          <div>
            <SectionHeader
              title="QA first-pass por dev — vs ciclo anterior"
              subtitle="¿Qué % pasa QA al primer intento? La línea punteada marca el ciclo anterior."
            />
            <div className="rounded-lg border border-border bg-card p-4">
              {qaVsPrev ? (
                <QaFirstPassVsPrevious data={qaVsPrev} />
              ) : (
                <ErrorCard title="QA first-pass vs anterior" />
              )}
            </div>
          </div>
        </section>

        {/* ───────── FLUJO / CUELLOS DE BOTELLA ───────── */}
        <section className="space-y-4">
          {bottleneckDetail ? (
            <BottleneckHero rows={bottleneckDetail.rows} />
          ) : (
            <ErrorCard title="Cuello de botella" />
          )}

          <div>
            <SectionHeader
              title="Tiempo por estado y área"
              subtitle="Horas hábiles por estado canónico (Manifiesto JPDS). Pasa el mouse para ver horas y % por estado."
            />
            <div className="rounded-lg border border-border bg-card p-4">
              {canonByArea ? (
                <CanonicalTimeBars rows={canonByArea.rows} includeKeys={DELIVERY_AREAS} />
              ) : (
                <ErrorCard title="Tiempo por estado" />
              )}
            </div>
          </div>
        </section>

        {/* ───────── DISEÑO (tiempos por estado) ───────── */}
        <section>
          <SectionHeader
            title="Tiempos de Diseño"
            subtitle="Fase de diseño del flujo (Adán → historias → Jesús → diseño → devs), por estado canónico."
          />
          <div className="rounded-lg border border-border bg-card p-4">
            {canonDesign ? (
              <CanonicalTimeBars
                rows={canonDesign.rows}
                emptyLabel="Sin tiempos de diseño en este horizonte."
              />
            ) : (
              <ErrorCard title="Tiempos de Diseño" />
            )}
          </div>
        </section>

        {/* ───────── CYCLE / LEAD TIME ───────── */}
        <section>
          <SectionHeader
            title="Cycle time & Lead time"
            subtitle="Cycle (In Progress→Done) y Lead (Backlog→Done) en horas hábiles. Cycle recalculado canónicamente desde el changelog; lead desde la creación real."
          />
          <div className="rounded-lg border border-border bg-card p-4">
            <CycleLeadChart apartado={apartado} />
          </div>
        </section>

        {/* ───────── MÉTRICAS POR DEV ───────── */}
        <section>
          <SectionHeader
            title="Métricas por dev"
            subtitle="Selecciona un dev: cycle/lead/QA + tiempo promedio por estado crudo (Jira) y canónico (los 9 del Manifiesto)."
          />
          <div className="rounded-lg border border-border bg-card p-4">
            {devList ? (
              <DevMetricsPanel devs={devList.devs} scope={scope} apartado={apartado} />
            ) : (
              <ErrorCard title="Métricas por dev" />
            )}
          </div>
        </section>

        {/* ───────── THROUGHPUT + VELOCITY ───────── */}
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

        {/* ───────── CP POR ÁREA ───────── */}
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
