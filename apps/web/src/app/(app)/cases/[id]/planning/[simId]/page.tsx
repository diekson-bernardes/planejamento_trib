import Link from "next/link";
import { notFound } from "next/navigation";

import { requestSimulationExport } from "@/app/(app)/cases/[id]/planning/actions";
import { ComparisonTable, type SimulationResultView } from "@/components/ComparisonTable";
import { SimulationLines, type LineRow } from "@/components/SimulationLines";
import { formatCompetence, formatDateTime } from "@/lib/format";
import { getSessionContext } from "@/lib/supabase/server";

export default async function SimulationPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string; simId: string }>;
  searchParams: Promise<{ erro?: string; ok?: string }>;
}) {
  const { id, simId } = await params;
  const { erro, ok } = await searchParams;
  const { supabase } = await getSessionContext();

  const { data: sim } = await supabase
    .from("simulations")
    .select("id, case_id, office_id, status, result, result_hash, snapshot_sha256, assumptions_hash, rules_version, rules_hash, duration_ms, created_at, error_message")
    .eq("id", simId)
    .eq("case_id", id)
    .maybeSingle();
  if (!sim) notFound();
  if (sim.status !== "done") {
    return (
      <div className="space-y-4">
        <Link href={`/cases/${id}/planning`} className="text-sm text-slate-600 hover:underline">← Planejamento</Link>
        <h1>Simulação de {formatDateTime(sim.created_at)}</h1>
        <p role="alert" className="alert-error">Simulação sem resultado: {sim.error_message ?? "falha no cálculo"}</p>
      </div>
    );
  }

  const pageSize = 1000;
  const lines: LineRow[] = [];
  for (let from = 0; ; from += pageSize) {
    const { data } = await supabase
      .from("simulation_lines")
      .select("regime, period, tax, kind, base, rate, amount, formula, rule_ref, origin, activity, partial, verified")
      .eq("simulation_id", simId)
      .order("ordinal")
      .range(from, from + pageSize - 1);
    if (!data?.length) break;
    lines.push(...(data as LineRow[]));
    if (data.length < pageSize) break;
  }

  const { data: objects } = await supabase.storage.from("documents").list(`${sim.office_id}/${id}/simulations`);
  const xlsxReady = (objects ?? []).some((o) => o.name === `${simId}.xlsx`);
  const result = sim.result as unknown as SimulationResultView;

  return (
    <div className="space-y-6">
      <div>
        <Link href={`/cases/${id}/planning`} className="text-sm text-slate-600 hover:underline">← Planejamento</Link>
        <h1 className="mt-1">Simulação de {formatDateTime(sim.created_at)}</h1>
        <p className="text-sm text-slate-600">
          Competências calculadas: {result.competences.map(formatCompetence).join(", ")}
          {result.excluded_competences.length > 0 && (
            <> · fora do cálculo (documentos incompletos): {result.excluded_competences.map(formatCompetence).join(", ")}</>
          )}
        </p>
      </div>
      {erro && <p role="alert" className="alert-error">{erro}</p>}
      {ok && <p role="status" className="alert-success">{ok}</p>}
      <p className="alert-warning">
        Comparativo ordenado por custo entre os regimes elegíveis. Não é recomendação: o parecer exige revisão e aprovação do
        responsável técnico.
      </p>
      {result.alerts?.length > 0 && <ul className="alert-warning list-disc pl-6">{result.alerts.map((a, i) => <li key={i}>{a}</li>)}</ul>}

      <ComparisonTable result={result} />

      <section className="card space-y-3" aria-labelledby="mem-title">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="mem-title">Memória de cálculo</h2>
          {xlsxReady ? (
            <a className="btn-secondary" href={`/api/simulations/${simId}/export`}>Baixar XLSX</a>
          ) : (
            <form action={requestSimulationExport}>
              <input type="hidden" name="caseId" value={id} />
              <input type="hidden" name="simulationId" value={simId} />
              <button type="submit" className="btn-secondary">Gerar XLSX</button>
            </form>
          )}
        </div>
        <SimulationLines lines={lines} />
      </section>

      <section className="card text-xs text-slate-600" aria-label="Rastreabilidade">
        <p>Regras: {sim.rules_version} · hash {sim.rules_hash}</p>
        <p>Snapshot homologado: {sim.snapshot_sha256}</p>
        <p>Premissas: {sim.assumptions_hash}</p>
        <p>Resultado: {sim.result_hash} · calculado em {sim.duration_ms ?? "—"} ms</p>
      </section>
    </div>
  );
}
