import Link from "next/link";
import { notFound } from "next/navigation";

import { requestCalculation, startPlanning } from "@/app/(app)/cases/[id]/planning/actions";
import { requestProjection } from "@/app/(app)/cases/[id]/planning/projection/actions";
import { AssumptionForm, type AssumptionRow } from "@/components/AssumptionForm";
import { StatusBadge } from "@/components/StatusBadge";
import { ASSUMPTION_GROUP_LABEL, formatBRL, formatCompetence, formatDateTime, formatPct, REGIME_LABEL } from "@/lib/format";
import { getSessionContext } from "@/lib/supabase/server";

const GROUP_ORDER = ["atividades", "elegibilidade", "icms_iss", "receitas", "pis_cofins", "real", "folha", "projecao", "conformidade", "reforma_2027"];

type SimulationSummary = {
  competences?: string[];
  excluded_competences?: string[];
  ranking?: string[];
  regimes?: Record<string, { total: string; status: string }>;
};

export default async function PlanningPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ erro?: string; ok?: string }>;
}) {
  const { id } = await params;
  const { erro, ok } = await searchParams;
  const { supabase } = await getSessionContext();

  const { data: tc } = await supabase
    .from("tax_cases")
    .select("id, status, period_start, period_end, companies(legal_name)")
    .eq("id", id)
    .maybeSingle();
  if (!tc) notFound();
  const company = tc.companies as { legal_name: string } | null;

  const [{ data: rows }, { data: sims }, { data: jobs }, { data: projections }] = await Promise.all([
    supabase
      .from("assumptions")
      .select("id, key, scope, grp, label, value_type, choices, suggested_value, suggested_origin, value, status, justification, confirmed_at")
      .eq("case_id", id)
      .order("key")
      .order("scope"),
    supabase
      .from("simulations")
      .select("id, status, result, rules_version, error_message, duration_ms, created_at")
      .eq("case_id", id)
      .order("created_at", { ascending: false }),
    supabase
      .from("jobs")
      .select("kind, status, last_error, created_at")
      .in("kind", ["suggest_assumptions", "calculate", "project"])
      .contains("payload", { case_id: id })
      .order("created_at", { ascending: false }),
    supabase
      .from("projections")
      .select("id, status, year, recommendation, error_message, created_at, recommendations(status)")
      .eq("case_id", id)
      .order("created_at", { ascending: false }),
  ]);

  const homologated = tc.status === "homologated";
  const running = (jobs ?? []).some((j) => j.status === "queued" || j.status === "running");
  // o worker encerra o cálculo sem simulação quando algo mudou após o pedido (ex.: premissa voltou a pendente)
  const lastCalc = (jobs ?? []).find((j) => j.kind === "calculate" || j.kind === "project");
  const calcNote = lastCalc && lastCalc.status !== "queued" && lastCalc.status !== "running" ? lastCalc.last_error : null;
  const assumptions = (rows ?? []) as (AssumptionRow & { grp: string })[];
  // o grupo reforma_2027 (alíquotas de CBS/IBS, crescimento, base de créditos) só bloqueia o exercício de 2027
  const pending = assumptions.filter((a) => a.status !== "confirmed" && a.grp !== "reforma_2027").length;
  const pending2027 = assumptions.filter((a) => a.status !== "confirmed" && a.grp === "reforma_2027").length;
  const hasReform = assumptions.some((a) => a.grp === "reforma_2027");
  const groups = GROUP_ORDER.map((g) => [g, assumptions.filter((a) => a.grp === g)] as const).filter(([, list]) => list.length);

  return (
    <div className="space-y-6">
      <div>
        <Link href={`/cases/${id}`} className="text-sm text-slate-600 hover:underline">← Dossiê</Link>
        <h1 className="mt-1">Planejamento tributário — {company?.legal_name}</h1>
        <p className="text-sm text-slate-600">
          Elegibilidade e cálculo de Simples, Presumido e Real sobre o snapshot homologado ({formatCompetence(tc.period_start)} a{" "}
          {formatCompetence(tc.period_end)}). O comparativo não é recomendação: o parecer exige revisão do responsável técnico.
        </p>
      </div>
      {erro && <p role="alert" className="alert-error">{erro}</p>}
      {ok && <p role="status" className="alert-success">{ok}</p>}
      {!homologated && <p className="alert-warning">Planejamento exige dossiê homologado. Homologue o dossiê primeiro.</p>}
      {running && <p className="alert-warning">Processando sugestões ou cálculo… atualize a página em instantes.</p>}
      {calcNote && <p role="status" className="alert-warning">Último pedido de cálculo: {calcNote}.</p>}

      {homologated && assumptions.length === 0 && (
        <form action={startPlanning} className="card space-y-2">
          <input type="hidden" name="caseId" value={id} />
          <p className="text-sm text-slate-700">
            O sistema sugere as premissas que os documentos não trazem (perfil das atividades, ICMS/ISS no regime normal,
            créditos de PIS/Cofins, ajustes do Real, encargos da folha e declarações de elegibilidade), cada uma com a origem.
          </p>
          <button type="submit" className="btn-primary" disabled={running}>Gerar premissas sugeridas</button>
        </form>
      )}

      {assumptions.length > 0 && (
        <section className="space-y-4" aria-labelledby="prem-title">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 id="prem-title">
              Premissas ({assumptions.length - pending - pending2027}/{assumptions.length} confirmadas
              {pending2027 > 0 ? ` · ${pending2027} de 2027 pendente${pending2027 > 1 ? "s" : ""}` : ""})
            </h2>
            <div className="flex gap-2">
              {homologated && (
                <form action={startPlanning}>
                  <input type="hidden" name="caseId" value={id} />
                  <button type="submit" className="btn-secondary" disabled={running}
                    title="Refaz as sugestões (após troca de regras ou de perfil); confirmadas só voltam a pendente se a sugestão mudar">
                    Regenerar premissas
                  </button>
                </form>
              )}
              <form action={requestCalculation}>
                <input type="hidden" name="caseId" value={id} />
                <button type="submit" className="btn-primary" disabled={pending > 0 || running}>
                  {pending > 0 ? `Calcular (${pending} pendente${pending > 1 ? "s" : ""})` : "Calcular simulação"}
                </button>
              </form>
            </div>
          </div>
          {groups.map(([group, list]) => (
            <div key={group} className="card space-y-2">
              <h3 className="text-sm font-semibold">{ASSUMPTION_GROUP_LABEL[group] ?? group}</h3>
              <ul className="space-y-2">
                {list.map((row) => (
                  <AssumptionForm key={row.id} row={row} readOnly={!homologated} />
                ))}
              </ul>
            </div>
          ))}
        </section>
      )}

      {assumptions.length > 0 && (
        <section className="card space-y-3" aria-labelledby="proj-title">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 id="proj-title">Projeção do exercício e recomendação</h2>
              <p className="text-sm text-slate-600">
                Exercício completo pelo motor (meses realizados, estimados pelo PGDAS-D e projetados pela média ou pelo
                orçamento), sensibilidade com ponto de virada e recomendação para aprovação do responsável técnico.
                Premissas pendentes geram uma prévia bloqueada. 2027: projeção de 2026 deslocada com o crescimento
                informado, com CBS/IBS no lugar de PIS/Cofins e o Simples híbrido como quarta alternativa.
              </p>
            </div>
            <div className="flex gap-2">
              <form action={requestProjection}>
                <input type="hidden" name="caseId" value={id} />
                <input type="hidden" name="year" value="2026" />
                <button type="submit" className="btn-primary" disabled={!homologated || running}>Projetar 2026</button>
              </form>
              {hasReform && (
                <form action={requestProjection}>
                  <input type="hidden" name="caseId" value={id} />
                  <input type="hidden" name="year" value="2027" />
                  <button type="submit" className="btn-secondary" disabled={!homologated || running}
                    title={pending2027 > 0 ? "Premissas de 2027 pendentes: a projeção sai como prévia bloqueada" : undefined}>
                    {pending2027 > 0 ? `Projetar 2027 (${pending2027} pendente${pending2027 > 1 ? "s" : ""})` : "Projetar 2027"}
                  </button>
                </form>
              )}
            </div>
          </div>
          {!!projections?.length && (
            <table className="data-table">
              <thead><tr><th>Data</th><th>Exercício</th><th>Resultado</th><th>Recomendação</th><th>Fluxo</th><th /></tr></thead>
              <tbody>
                {projections.map((p) => {
                  const rec = (p.recommendation ?? {}) as { status?: string; regime?: string; economia_vs_segundo_pct?: string };
                  const flow = (p.recommendations as { status: string }[] | { status: string } | null);
                  const flowStatus = Array.isArray(flow) ? flow[0]?.status : flow?.status;
                  return (
                    <tr key={p.id}>
                      <td className="whitespace-nowrap">{formatDateTime(p.created_at)}</td>
                      <td>{p.year || "—"}</td>
                      <td>{p.status === "done" ? <StatusBadge status={rec.status ?? "done"} /> : <StatusBadge status="failed" label="Falhou" />}</td>
                      <td>{p.status === "done"
                        ? (rec.regime ? `${REGIME_LABEL[rec.regime]}${rec.economia_vs_segundo_pct ? ` (${formatPct(rec.economia_vs_segundo_pct)} abaixo do 2º)` : ""}` : "—")
                        : p.error_message}</td>
                      <td>{flowStatus ? <StatusBadge status={flowStatus} /> : "—"}</td>
                      <td>{p.status === "done" && <Link className="text-brand-700 underline" href={`/cases/${id}/planning/projection/${p.id}`}>Abrir</Link>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>
      )}

      <section className="card space-y-3" aria-labelledby="sims-title">
        <h2 id="sims-title">Simulações</h2>
        {!sims?.length ? (
          <p className="text-sm text-slate-600">Nenhuma simulação ainda.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr><th>Data</th><th>Status</th><th>Competências</th><th>Ordenação (elegíveis)</th><th>Regras</th><th /></tr>
            </thead>
            <tbody>
              {sims.map((s) => {
                const r = (s.result ?? {}) as SimulationSummary;
                return (
                  <tr key={s.id}>
                    <td className="whitespace-nowrap">{formatDateTime(s.created_at)}</td>
                    <td><StatusBadge status={s.status} label={s.status === "done" ? "Concluída" : "Falhou"} /></td>
                    <td>{(r.competences ?? []).map(formatCompetence).join(", ") || "—"}</td>
                    <td>
                      {(r.ranking ?? []).length
                        ? (r.ranking ?? []).map((reg) => `${REGIME_LABEL[reg]} (${formatBRL(r.regimes?.[reg]?.total)})`).join(" < ")
                        : s.error_message ?? "nenhum regime elegível e calculado"}
                    </td>
                    <td className="text-xs">{s.rules_version}</td>
                    <td>{s.status === "done" && <Link className="text-brand-700 underline" href={`/cases/${id}/planning/${s.id}`}>Abrir</Link>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
