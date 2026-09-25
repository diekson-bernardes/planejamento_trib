import { StatusBadge } from "@/components/StatusBadge";
import { ELIGIBILITY, formatBRL, formatCompetence, REGIME_LABEL, TAX_LABEL } from "@/lib/format";

type RegimeResult = {
  status: string;
  total: string;
  by_tax: Record<string, string>;
  by_period: Record<string, string>;
  pending: string[];
  partial_periods: string[];
  unverified_rules: number;
};
type Eligibility = { status: string; reasons: { status: string; motivo: string; regra: string }[] };

export type SimulationResultView = {
  competences: string[];
  excluded_competences: string[];
  ranking: string[];
  alerts: string[];
  regimes: Record<string, RegimeResult>;
  eligibility: Record<string, Eligibility>;
};

const REGIMES = ["SIMPLES", "PRESUMIDO", "REAL"];

function periodLabel(p: string) {
  return p.includes("-T") ? `${p.slice(5)}/${p.slice(0, 4)}` : formatCompetence(p);
}

export function ComparisonTable({ result }: { result: SimulationResultView }) {
  const taxes = Array.from(new Set(REGIMES.flatMap((r) => Object.keys(result.regimes[r]?.by_tax ?? {})))).sort();
  const periods = Array.from(new Set(REGIMES.flatMap((r) => Object.keys(result.regimes[r]?.by_period ?? {})))).sort();
  const ranked = new Map(result.ranking.map((r, i) => [r, i + 1]));

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        {REGIMES.map((regime) => {
          const r = result.regimes[regime];
          const e = result.eligibility[regime];
          const info = ELIGIBILITY[e?.status] ?? { label: e?.status, tone: "neutral" as const };
          return (
            <div key={regime} className="card space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">{REGIME_LABEL[regime]}</h3>
                {ranked.has(regime) && <span className="text-xs font-semibold text-brand-700">{ranked.get(regime)}º menor custo</span>}
              </div>
              <p className="text-2xl font-semibold tabular-nums">
                {r?.status === "calculado" ? `R$ ${formatBRL(r.total)}` : "Não calculado"}
              </p>
              <StatusBadge status={e?.status === "inelegivel" ? "fail" : "pass"} label={info.label} />
              {e?.reasons?.length > 0 && (
                <ul className="list-disc pl-4 text-xs text-slate-600">
                  {e.reasons.map((x, i) => <li key={i}>{x.motivo}</li>)}
                </ul>
              )}
              {r?.pending?.length > 0 && <p className="alert-warning text-xs">{r.pending.join("; ")}</p>}
              {r?.partial_periods?.length > 0 && (
                <p className="text-xs text-amber-800">Trimestre(s) parcial(is): {r.partial_periods.map(periodLabel).join(", ")}</p>
              )}
              {r?.unverified_rules > 0 && (
                <p className="text-xs text-slate-500">{r.unverified_rules} valor(es) com regra ainda não conferida na fonte primária</p>
              )}
            </div>
          );
        })}
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="data-table">
          <thead>
            <tr><th>Tributo</th>{REGIMES.map((r) => <th key={r} className="num">{REGIME_LABEL[r]}</th>)}</tr>
          </thead>
          <tbody>
            {taxes.map((t) => (
              <tr key={t}>
                <td>{TAX_LABEL[t] ?? t}</td>
                {REGIMES.map((r) => <td key={r} className="num">{result.regimes[r]?.by_tax?.[t] ? formatBRL(result.regimes[r].by_tax[t]) : "—"}</td>)}
              </tr>
            ))}
            <tr className="font-semibold">
              <td>Total</td>
              {REGIMES.map((r) => <td key={r} className="num">{result.regimes[r]?.status === "calculado" ? formatBRL(result.regimes[r].total) : "—"}</td>)}
            </tr>
          </tbody>
        </table>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="data-table">
          <thead>
            <tr><th>Período</th>{REGIMES.map((r) => <th key={r} className="num">{REGIME_LABEL[r]}</th>)}</tr>
          </thead>
          <tbody>
            {periods.map((p) => (
              <tr key={p}>
                <td>{periodLabel(p)}{p.includes("-T") ? " (IRPJ/CSLL trimestrais)" : ""}</td>
                {REGIMES.map((r) => <td key={r} className="num">{result.regimes[r]?.by_period?.[p] ? formatBRL(result.regimes[r].by_period[p]) : "—"}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
