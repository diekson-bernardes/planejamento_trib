import type { ProjectionLine } from "@/components/ProjectionTable";
import { formatBRL, formatCompetence } from "@/lib/format";

type Month = Partial<Record<"folha_ideal_economia" | "folha_ideal_prolabore" | "folha_ideal_salario", ProjectionLine>>;

/** Folha ideal (informativa, fora dos totais): quanto de folha falta por mês para 28% e o custo de completá-la por
 *  pró-labore ou por salário, ao lado da economia de Simples do Anexo III em relação ao V. */
export function FolhaIdealTable({ lines }: { lines: ProjectionLine[] }) {
  const byMonth = new Map<string, Month>();
  for (const l of lines) {
    if (l.regime !== "SIMPLES" || !l.tax.startsWith("folha_ideal_")) continue;
    byMonth.set(l.period, { ...(byMonth.get(l.period) ?? {}), [l.tax]: l });
  }
  if (!byMonth.size) return null;
  const n = (v: string | number | undefined | null) => Number(v ?? 0);
  return (
    <section className="card space-y-3" aria-labelledby="folha-ideal-title">
      <h2 id="folha-ideal-title">Folha ideal para o Anexo III</h2>
      <p className="text-xs text-slate-600">
        Informativo, fora dos totais. Meses em que o serviço fica no Anexo V: folha mensal que falta para chegar a 28%,
        economia de Simples se a atividade fosse para o Anexo III e o custo de completar a folha. Pró-labore: INSS do
        sócio (11%). Salário: salário + FGTS + provisões de 13º e férias. Parâmetros ainda não verificados na fonte.
      </p>
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>Mês</th><th className="num">Folha faltante/mês</th><th className="num">Economia III × V</th>
              <th className="num">Custo via pró-labore</th><th className="num">Líquido</th>
              <th className="num">Custo via salário</th><th className="num">Líquido</th>
            </tr>
          </thead>
          <tbody>
            {[...byMonth.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([period, m]) => {
              const eco = n(m.folha_ideal_economia?.amount);
              const pl = n(m.folha_ideal_prolabore?.amount);
              const sal = n(m.folha_ideal_salario?.amount);
              return (
                <tr key={period}>
                  <td>{formatCompetence(period)}</td>
                  <td className="num">{formatBRL(m.folha_ideal_economia?.base ?? 0)}</td>
                  <td className="num">{formatBRL(eco)}</td>
                  <td className="num">{formatBRL(pl)}</td>
                  <td className={`num ${eco - pl >= 0 ? "text-emerald-700" : "text-red-700"}`}>{formatBRL(eco - pl)}</td>
                  <td className="num">{formatBRL(sal)}</td>
                  <td className={`num ${eco - sal >= 0 ? "text-emerald-700" : "text-red-700"}`}>{formatBRL(eco - sal)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
