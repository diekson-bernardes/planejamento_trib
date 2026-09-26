"use client";

import { Fragment, useMemo, useState } from "react";

import { formatBRL, orderedRegimes, REGIME_LABEL, TAX_LABEL } from "@/lib/format";

export type LineRow = {
  regime: string;
  period: string;
  tax: string;
  kind: string;
  base: number;
  rate: number;
  amount: number;
  formula: string;
  rule_ref: string;
  origin: Record<string, unknown>;
  activity: string | null;
  partial: boolean;
  verified: boolean;
};

function originSummary(origin: Record<string, unknown>): string {
  if (!origin || !Object.keys(origin).length) return "—";
  if (origin.source === "assumption") return `premissa ${origin.key} (${origin.scope})`;
  if (origin.source === "snapshot") return [origin.doc_type, origin.field_key, origin.page ? `p. ${origin.page}` : null].filter(Boolean).join(" · ");
  return String(origin.source ?? "cálculo");
}

export function SimulationLines({ lines }: { lines: LineRow[] }) {
  const [regime, setRegime] = useState("SIMPLES");
  const [onlyTaxes, setOnlyTaxes] = useState(false);
  const [open, setOpen] = useState<number | null>(null);
  const filtered = useMemo(
    () => lines.map((l, i) => ({ ...l, i })).filter((l) => l.regime === regime && (!onlyTaxes || l.kind === "tributo")),
    [lines, regime, onlyTaxes],
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2" role="tablist" aria-label="Regime">
        {orderedRegimes(Array.from(new Set(lines.map((l) => l.regime)))).map((r) => (
          <button key={r} type="button" role="tab" aria-selected={regime === r}
            className={regime === r ? "btn-primary px-3 py-1" : "btn-secondary px-3 py-1"} onClick={() => setRegime(r)}>
            {REGIME_LABEL[r]}
          </button>
        ))}
        <label className="ml-2 flex items-center gap-2 text-sm">
          <input type="checkbox" checked={onlyTaxes} onChange={(e) => setOnlyTaxes(e.target.checked)} /> Só tributos
        </label>
      </div>
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="data-table">
          <thead>
            <tr><th>Período</th><th>Tributo</th><th>Tipo</th><th className="num">Base</th><th className="num">Valor</th><th>Fórmula</th><th /></tr>
          </thead>
          <tbody>
            {filtered.map((l) => (
              <Fragment key={l.i}>
                <tr className={l.kind !== "tributo" ? "bg-slate-50 text-slate-600" : undefined}>
                  <td className="whitespace-nowrap">{l.period}{l.partial ? " (parcial)" : ""}</td>
                  <td>{TAX_LABEL[l.tax] ?? l.tax}</td>
                  <td className="text-xs">{l.kind}</td>
                  <td className="num">{formatBRL(l.base)}</td>
                  <td className="num font-medium">{formatBRL(l.amount)}</td>
                  <td className="max-w-xl text-xs">{l.formula}</td>
                  <td>
                    <button type="button" className="text-xs text-brand-700 underline" aria-expanded={open === l.i}
                      onClick={() => setOpen(open === l.i ? null : l.i)}>
                      origem
                    </button>
                  </td>
                </tr>
                {open === l.i && (
                  <tr>
                    <td colSpan={7} className="bg-slate-50 text-xs">
                      <p><strong>Regra:</strong> {l.rule_ref} {l.verified ? "" : "· ⚠ não conferida na fonte primária"}</p>
                      <p><strong>Origem:</strong> {originSummary(l.origin)}</p>
                      {l.activity && <p><strong>Atividade:</strong> {l.activity}</p>}
                      <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap text-[11px] text-slate-500">{JSON.stringify(l.origin, null, 2)}</pre>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
