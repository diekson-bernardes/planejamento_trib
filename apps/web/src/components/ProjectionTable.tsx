import { formatBRL, MONTH_ORIGIN, REGIME_LABEL, TAX_LABEL } from "@/lib/format";

export type ProjectionLine = { regime: string; period: string; tax: string; kind: string; amount: string | number };

const MONTHS = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"];
const TAX_ORDER = ["irpj", "adicional_irpj", "csll", "cofins", "pis", "cpp", "rat", "terceiros", "icms", "iss", "ipi"];

/** Resultado mensal por regime no formato do SPTE: tributos × jan–dez (+ trimestres do IRPJ/CSLL) e origem do mês. */
export function ProjectionTable({ regime, year, lines, origins }: {
  regime: string;
  year: number;
  lines: ProjectionLine[];
  origins: Record<string, string>;
}) {
  const months = MONTHS.map((_, i) => `${year}-${String(i + 1).padStart(2, "0")}`);
  const quarters = regime === "SIMPLES" ? [] : [1, 2, 3, 4].map((q) => `${year}-T${q}`);
  const periods = [...months, ...quarters];
  const grid = new Map<string, Map<string, number>>();
  for (const l of lines) {
    if (l.regime !== regime || l.kind !== "tributo") continue;
    const row = grid.get(l.tax) ?? new Map<string, number>();
    row.set(l.period, (row.get(l.period) ?? 0) + Number(l.amount));
    grid.set(l.tax, row);
  }
  const taxes = [...TAX_ORDER.filter((t) => grid.has(t)), ...[...grid.keys()].filter((t) => !TAX_ORDER.includes(t)).sort()];
  const colTotal = (p: string) => taxes.reduce((s, t) => s + (grid.get(t)?.get(p) ?? 0), 0);
  const rowTotal = (t: string) => periods.reduce((s, p) => s + (grid.get(t)?.get(p) ?? 0), 0);

  return (
    <div className="overflow-x-auto">
      <table className="data-table text-xs">
        <caption className="mb-1 text-left text-sm font-semibold">Resultado: {REGIME_LABEL[regime]}</caption>
        <thead>
          <tr>
            <th>Tributo</th>
            {MONTHS.map((m) => <th key={m} className="text-right">{m}</th>)}
            {quarters.map((q) => <th key={q} className="text-right">{q.slice(5)}</th>)}
            <th className="text-right">Total</th>
          </tr>
          <tr>
            <th className="font-normal text-slate-500">Origem</th>
            {months.map((m) => (
              <th key={m} className="text-right font-normal text-slate-500" title={MONTH_ORIGIN[origins[m]]?.label}>
                {MONTH_ORIGIN[origins[m]]?.short ?? "—"}
              </th>
            ))}
            {quarters.map((q) => <th key={q} />)}
            <th />
          </tr>
        </thead>
        <tbody>
          {taxes.map((t) => (
            <tr key={t}>
              <td>{TAX_LABEL[t] ?? t.toUpperCase()}</td>
              {periods.map((p) => <td key={p} className="text-right tabular-nums">{formatBRL(grid.get(t)?.get(p) ?? 0)}</td>)}
              <td className="text-right font-medium tabular-nums">{formatBRL(rowTotal(t))}</td>
            </tr>
          ))}
          <tr className="font-semibold">
            <td>Total</td>
            {periods.map((p) => <td key={p} className="text-right tabular-nums">{formatBRL(colTotal(p))}</td>)}
            <td className="text-right tabular-nums">{formatBRL(periods.reduce((s, p) => s + colTotal(p), 0))}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
