import {
  approveRecommendation,
  requestReport,
  returnRecommendation,
  submitRecommendation,
} from "@/app/(app)/cases/[id]/planning/projection/actions";
import { StatusBadge } from "@/components/StatusBadge";
import { EVENT_LABEL, formatBRL, formatDateTime, formatPct, REGIME_LABEL } from "@/lib/format";

export type ComputedRecommendation = {
  status: string;
  regime: string | null;
  segundo: string | null;
  texto: string;
  fatores: { tributo: string; diferenca: string; texto: string }[];
  economia_vs_segundo: string | null;
  economia_vs_segundo_pct: string | null;
  regime_atual: string | null;
  economia_vs_atual: string | null;
  carga: Record<string, { consumo: string; renda: string; folha: string }>;
  aliquota_efetiva: Record<string, string>;
  conformidade: Record<string, string>;
  excluidos: { regime: string; motivo: string; detalhe: string[] }[];
  bloqueios: string[];
  ressalvas: string[];
  limiar: string;
};

export type RecommendationRow = {
  id: string;
  status: string;
  computed_status: string;
  elaborated_by: string | null;
  approved_by: string | null;
  approved_at: string | null;
  pdf_sha256: string | null;
  emitted_at: string | null;
};

export type EventRow = { event: string; comment: string | null; created_at: string };

export function RecommendationPanel({ caseId, projectionId, rec, computed, events, userId, isTechnical }: {
  caseId: string;
  projectionId: string;
  rec: RecommendationRow;
  computed: ComputedRecommendation;
  events: EventRow[];
  userId: string;
  isTechnical: boolean;
}) {
  const hidden = (
    <>
      <input type="hidden" name="caseId" value={caseId} />
      <input type="hidden" name="projectionId" value={projectionId} />
      <input type="hidden" name="recommendationId" value={rec.id} />
    </>
  );
  const canApprove = isTechnical && rec.elaborated_by !== userId;
  const regimes = ["SIMPLES", "PRESUMIDO", "REAL"].filter((r) => computed.carga?.[r]);

  return (
    <section className="card space-y-4" aria-labelledby="rec-title">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="rec-title">Recomendação</h2>
        <div className="flex gap-2">
          <StatusBadge status={computed.status} />
          <StatusBadge status={rec.status} />
        </div>
      </div>
      <p className={computed.status === "bloqueado" ? "alert-error" : computed.status === "inconclusivo" ? "alert-warning" : "alert-success"}>
        {computed.texto}
      </p>
      {computed.fatores?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold">Principais fatores econômicos</h3>
          <ul className="list-disc pl-5 text-sm">{computed.fatores.map((f) => <li key={f.tributo}>{f.texto}</li>)}</ul>
        </div>
      )}
      <dl className="grid gap-2 text-sm sm:grid-cols-3">
        <div><dt className="text-slate-500">Economia vs. segundo colocado</dt>
          <dd className="font-semibold">{computed.economia_vs_segundo ? `R$ ${formatBRL(computed.economia_vs_segundo)} (${formatPct(computed.economia_vs_segundo_pct)})` : "—"}</dd></div>
        <div><dt className="text-slate-500">Economia vs. regime atual ({computed.regime_atual ? REGIME_LABEL[computed.regime_atual] : "—"})</dt>
          <dd className="font-semibold">{computed.economia_vs_atual ? `R$ ${formatBRL(computed.economia_vs_atual)}` : "—"}</dd></div>
        <div><dt className="text-slate-500">Limiar de inconclusivo do escritório</dt>
          <dd className="font-semibold">{formatPct(computed.limiar)}</dd></div>
      </dl>
      {regimes.length > 0 && (
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr><th>Regime</th><th className="text-right">Consumo</th><th className="text-right">Renda</th><th className="text-right">Folha</th>
                <th className="text-right">Alíquota efetiva</th><th className="text-right">Conformidade*</th></tr>
            </thead>
            <tbody>
              {regimes.map((r) => (
                <tr key={r}>
                  <td>{REGIME_LABEL[r]}</td>
                  <td className="text-right tabular-nums">{formatBRL(computed.carga[r].consumo)}</td>
                  <td className="text-right tabular-nums">{formatBRL(computed.carga[r].renda)}</td>
                  <td className="text-right tabular-nums">{formatBRL(computed.carga[r].folha)}</td>
                  <td className="text-right tabular-nums">{formatPct(computed.aliquota_efetiva?.[r])}</td>
                  <td className="text-right tabular-nums">{computed.conformidade?.[r] !== undefined ? formatBRL(computed.conformidade[r]) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-1 text-xs text-slate-600">* Custo de conformidade informado pelo escritório; exibido à parte, não altera a ordem dos regimes.</p>
        </div>
      )}
      {computed.excluidos?.length > 0 && (
        <ul className="alert-warning list-disc pl-6 text-sm">
          {computed.excluidos.map((e) => <li key={e.regime}>{REGIME_LABEL[e.regime]} fora do ranking ({e.motivo}): {e.detalhe?.join("; ")}</li>)}
        </ul>
      )}
      <details className="text-sm">
        <summary className="cursor-pointer font-semibold">Ressalvas ({computed.ressalvas?.length ?? 0})</summary>
        <ul className="mt-2 list-disc pl-5 text-slate-700">{computed.ressalvas?.map((r, i) => <li key={i}>{r}</li>)}</ul>
      </details>

      <div className="space-y-2 border-t border-slate-100 pt-3">
        <h3 className="text-sm font-semibold">Fluxo: elaborar → revisar → aprovar → emitir</h3>
        <ol className="space-y-1 text-xs text-slate-600">
          {events.map((e, i) => (
            <li key={i}>{formatDateTime(e.created_at)} — {EVENT_LABEL[e.event] ?? e.event}{e.comment ? `: “${e.comment}”` : ""}</li>
          ))}
        </ol>
        <div className="flex flex-wrap items-start gap-2">
          {rec.status === "rascunho" && computed.status !== "bloqueado" && (
            <form action={submitRecommendation}>{hidden}<button type="submit" className="btn-primary">Enviar para revisão</button></form>
          )}
          {rec.status === "em_revisao" && canApprove && (
            <form action={approveRecommendation}>{hidden}<button type="submit" className="btn-primary">Aprovar</button></form>
          )}
          {(rec.status === "em_revisao" || rec.status === "aprovada") && isTechnical && (
            <form action={returnRecommendation} className="flex flex-wrap items-end gap-2">
              {hidden}
              <div>
                <label className="label" htmlFor="comment">Comentário da devolução</label>
                <input id="comment" name="comment" className="input min-w-72" minLength={5} required />
              </div>
              <button type="submit" className="btn-secondary">Devolver</button>
            </form>
          )}
          {rec.status === "aprovada" && (
            <form action={requestReport}>{hidden}<button type="submit" className="btn-primary">Emitir PDF</button></form>
          )}
          {rec.status === "emitida" && (
            <a className="btn-primary" href={`/api/reports/${rec.id}`}>Baixar PDF emitido</a>
          )}
        </div>
        {rec.status === "em_revisao" && !canApprove && (
          <p className="text-xs text-slate-600">
            {isTechnical ? "Você elaborou esta recomendação: outro responsável técnico precisa aprovar." : "Aguardando o responsável técnico."}
          </p>
        )}
        {rec.pdf_sha256 && <p className="text-xs text-slate-500">PDF emitido em {formatDateTime(rec.emitted_at)} · SHA-256 {rec.pdf_sha256}</p>}
      </div>
    </section>
  );
}
