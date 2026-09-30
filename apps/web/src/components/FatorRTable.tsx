import type { ProjectionLine } from "@/components/ProjectionTable";
import { formatBRL, formatCompetence, formatPct } from "@/lib/format";

const FATOR_R_MINIMO = 0.28;
const TRATAMENTO: Record<string, string> = {
  media: "meses sem folha completados pela média dos meses informados",
  zero: "meses sem folha considerados com folha zero",
};

/** Fator R mês a mês (linhas informativas "fator_r" do motor): folha dos 12 meses anteriores, RBT12, % e anexo. */
export function FatorRTable({ lines, tratamento }: { lines: ProjectionLine[]; tratamento?: string | null }) {
  const seen = new Set<string>();
  const rows = lines.filter((l) => {
    if (l.tax !== "fator_r" || l.regime !== "SIMPLES" || seen.has(l.period)) return false;
    seen.add(l.period);
    return true;
  });
  if (!rows.length) return null;
  const rbt12 = new Map(lines.filter((l) => l.tax === "rbt12" && l.regime === "SIMPLES").map((l) => [l.period, l.amount]));
  return (
    <section className="card space-y-3" aria-labelledby="fator-r-title">
      <h2 id="fator-r-title">Fator R mês a mês</h2>
      <p className="text-xs text-slate-600">
        Fator R = folha dos 12 meses anteriores ÷ RBT12. Folha = salários × (1 + FGTS 8%) + pró-labore; os meses depois
        da declaração usam a folha projetada. Com 28% ou mais, o serviço vai para o Anexo III; abaixo, Anexo V.
        {tratamento && ` Folha incompleta: ${TRATAMENTO[tratamento] ?? tratamento}.`}
      </p>
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr><th>Mês</th><th className="num">Folha 12m</th><th className="num">RBT12</th><th className="num">Fator R</th><th>Anexo</th></tr>
          </thead>
          <tbody>
            {rows.map((l) => {
              const rate = Number(l.rate ?? 0);
              return (
                <tr key={l.period}>
                  <td>{formatCompetence(l.period)}</td>
                  <td className="num">{formatBRL(l.base ?? 0)}</td>
                  <td className="num">{formatBRL(rbt12.get(l.period) ?? 0)}</td>
                  <td className="num">{formatPct(rate)}</td>
                  <td className={rate >= FATOR_R_MINIMO ? "font-medium text-emerald-700" : "font-medium text-amber-700"}>
                    {rate >= FATOR_R_MINIMO ? "III" : "V"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
