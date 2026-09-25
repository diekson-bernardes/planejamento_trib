import Link from "next/link";
import { notFound } from "next/navigation";

import { ComparisonTable, type SimulationResultView } from "@/components/ComparisonTable";
import { ProjectionTable, type ProjectionLine } from "@/components/ProjectionTable";
import {
  RecommendationPanel,
  type ComputedRecommendation,
  type EventRow,
  type RecommendationRow,
} from "@/components/RecommendationPanel";
import { SensitivityTable, type SensitivityRow } from "@/components/SensitivityTable";
import { formatDateTime, MONTH_ORIGIN } from "@/lib/format";
import { getSessionContext } from "@/lib/supabase/server";

type ProjectionSummary = {
  year: number;
  origins: Record<string, string>;
  base: { receita_anual: string; margem_anual: string };
  simulation: SimulationResultView;
};

export default async function ProjectionPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string; projId: string }>;
  searchParams: Promise<{ erro?: string; ok?: string }>;
}) {
  const { id, projId } = await params;
  const { erro, ok } = await searchParams;
  const { supabase, user } = await getSessionContext();

  const { data: proj } = await supabase
    .from("projections")
    .select("id, office_id, status, year, result, sensitivity, recommendation, rules_version, rules_hash, decision_version, decision_hash, threshold, snapshot_sha256, assumptions_hash, result_hash, engine_runs, duration_ms, created_at, error_message")
    .eq("id", projId)
    .eq("case_id", id)
    .maybeSingle();
  if (!proj) notFound();
  if (proj.status !== "done") {
    return (
      <div className="space-y-4">
        <Link href={`/cases/${id}/planning`} className="text-sm text-slate-600 hover:underline">← Planejamento</Link>
        <h1>Projeção de {formatDateTime(proj.created_at)}</h1>
        <p role="alert" className="alert-error">Projeção sem resultado: {proj.error_message ?? "falha no cálculo"}</p>
      </div>
    );
  }

  const [{ data: rec }, { data: isTechnical }] = await Promise.all([
    supabase.from("recommendations")
      .select("id, status, computed_status, elaborated_by, approved_by, approved_at, pdf_sha256, emitted_at")
      .eq("projection_id", projId).maybeSingle(),
    supabase.rpc("is_technical_responsible", { p_office: proj.office_id }),
  ]);
  const { data: events } = rec
    ? await supabase.from("recommendation_events").select("event, comment, created_at")
        .eq("recommendation_id", rec.id).order("created_at")
    : { data: [] };

  const lines: ProjectionLine[] = [];
  for (let from = 0; ; from += 1000) {
    const { data } = await supabase.from("projection_lines").select("regime, period, tax, kind, amount")
      .eq("projection_id", projId).order("ordinal").range(from, from + 999);
    if (!data?.length) break;
    lines.push(...(data as ProjectionLine[]));
    if (data.length < 1000) break;
  }

  const result = proj.result as unknown as ProjectionSummary;
  const computed = proj.recommendation as unknown as ComputedRecommendation;
  const sim = result.simulation;
  const counts = Object.values(result.origins).reduce<Record<string, number>>((acc, o) => ({ ...acc, [o]: (acc[o] ?? 0) + 1 }), {});

  return (
    <div className="space-y-6">
      <div>
        <Link href={`/cases/${id}/planning`} className="text-sm text-slate-600 hover:underline">← Planejamento</Link>
        <h1 className="mt-1">Projeção do exercício {result.year}</h1>
        <p className="text-sm text-slate-600">
          {Object.entries(counts).map(([o, n]) => `${n} ${n > 1 ? "meses" : "mês"} ${MONTH_ORIGIN[o]?.label.split(" (")[0].toLowerCase()}`).join(" · ")}
          {" "}· regras {proj.rules_version} · calculada em {formatDateTime(proj.created_at)}
        </p>
      </div>
      {erro && <p role="alert" className="alert-error">{erro}</p>}
      {ok && <p role="status" className="alert-success">{ok}</p>}
      <p className="alert-warning">
        Comparação do exercício de {result.year} com as regras de {result.year}. A partir de 2027 valem as regras de transição da
        Reforma Tributária, ainda não calculadas. A recomendação só vai ao cliente após aprovação do responsável técnico.
      </p>

      {rec && (
        <RecommendationPanel caseId={id} projectionId={projId} rec={rec as RecommendationRow} computed={computed}
          events={(events ?? []) as EventRow[]} userId={user.id} isTechnical={Boolean(isTechnical)} />
      )}

      <section className="space-y-3" aria-labelledby="cmp-title">
        <h2 id="cmp-title">Comparativo do exercício</h2>
        <ComparisonTable result={sim} />
      </section>

      <section className="card space-y-3" aria-labelledby="sens-title">
        <h2 id="sens-title">Sensibilidade e ponto de virada</h2>
        <SensitivityTable rows={proj.sensitivity as unknown as SensitivityRow[]} />
      </section>

      <section className="card space-y-4" aria-labelledby="month-title">
        <h2 id="month-title">Resultado mensal por regime</h2>
        <p className="text-xs text-slate-600">
          {Object.entries(MONTH_ORIGIN).map(([, o]) => `${o.short} = ${o.label}`).join(" · ")}.
          IRPJ/CSLL do Presumido e do Real são trimestrais (colunas T1–T4).
        </p>
        {["SIMPLES", "PRESUMIDO", "REAL"].filter((r) => sim.regimes[r]?.status === "calculado").map((r) => (
          <ProjectionTable key={r} regime={r} year={result.year} lines={lines} origins={result.origins} />
        ))}
      </section>

      <section className="card text-xs text-slate-600" aria-label="Rastreabilidade">
        <p>Regras: {proj.rules_version} · hash {proj.rules_hash} · política de decisão {proj.decision_version} · hash {proj.decision_hash}</p>
        <p>Snapshot homologado: {proj.snapshot_sha256} · premissas: {proj.assumptions_hash}</p>
        <p>Resultado: {proj.result_hash} · {proj.engine_runs} execuções do motor em {proj.duration_ms} ms</p>
      </section>
    </div>
  );
}
