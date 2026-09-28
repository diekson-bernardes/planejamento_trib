import type { ProjectionLine } from "@/components/ProjectionTable";
import { formatBRL, formatCompetence, formatPct } from "@/lib/format";

type BandOrigin = { anexo: string; faixa: number; rbt12: string; nominal: string; deducao: string; efetiva: string };

/** Faixa do Simples por mês (linhas informativas "faixa" do motor): anexo, faixa pelo RBT12, nominal, dedução, efetiva. */
export function SimplesBandTable({ lines }: { lines: ProjectionLine[] }) {
  const rows = lines.filter((l) => l.tax === "faixa" && l.regime === "SIMPLES" && l.origin) as (ProjectionLine & {
    origin: BandOrigin;
  })[];
  if (!rows.length) return null;
  return (
    <section className="card space-y-3" aria-labelledby="band-title">
      <h2 id="band-title">Faixa do Simples Nacional por mês</h2>
      <p className="text-xs text-slate-600">
        Alíquota efetiva = (RBT12 × alíquota nominal − parcela a deduzir) ÷ RBT12, pelo anexo da atividade.
      </p>
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr><th>Mês</th><th>Anexo</th><th>Faixa</th><th className="num">RBT12</th><th className="num">Nominal</th>
              <th className="num">Parcela a deduzir</th><th className="num">Efetiva</th></tr>
          </thead>
          <tbody>
            {rows.map((l) => (
              <tr key={`${l.period}-${l.origin.anexo}`}>
                <td>{formatCompetence(l.period)}</td>
                <td>{l.origin.anexo}</td>
                <td>{l.origin.faixa}ª</td>
                <td className="num">{formatBRL(l.origin.rbt12)}</td>
                <td className="num">{formatPct(l.origin.nominal)}</td>
                <td className="num">{formatBRL(l.origin.deducao)}</td>
                <td className="num">{formatPct(l.origin.efetiva, 4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
