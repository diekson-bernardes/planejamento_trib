import { StatusBadge } from "@/components/StatusBadge";
import { formatBRL, formatPct, REGIME_LABEL, ROBUSTNESS } from "@/lib/format";

export type SensitivityRow = {
  variavel: string;
  rotulo: string;
  tipo: "multiplicador" | "absoluto";
  base_valor: string | null;
  virada_valor: string | null;
  novo_lider: string | null;
  distancia: string | null;
  robustez: string | null;
  limite_juridico_valor: string | null;
  limite_juridico: { elegiveis_alem_do_limite: string[]; elegiveis_base: string[] } | null;
  sem_virada: boolean;
};

function value(row: SensitivityRow, v: string | null) {
  if (v === null) return "—";
  return row.tipo === "multiplicador" ? `R$ ${formatBRL(v)}` : formatPct(v);
}

/** Ponto de virada por variável: valor base, virada (ou "sem virada"), novo líder, distância, robustez e limite jurídico. */
export function SensitivityTable({ rows }: { rows: SensitivityRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="data-table">
        <thead>
          <tr>
            <th>Variável</th><th className="text-right">Cenário base</th><th className="text-right">Ponto de virada</th>
            <th>Novo líder</th><th className="text-right">Distância</th><th>Robustez</th><th>Limite jurídico</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const lost = r.limite_juridico
              ? r.limite_juridico.elegiveis_base.filter((x) => !r.limite_juridico!.elegiveis_alem_do_limite.includes(x))
              : [];
            return (
              <tr key={r.variavel}>
                <td>{r.rotulo}</td>
                <td className="text-right tabular-nums">{value(r, r.base_valor)}</td>
                <td className="text-right tabular-nums">{r.sem_virada ? "sem virada no intervalo" : value(r, r.virada_valor)}</td>
                <td>{r.novo_lider ? REGIME_LABEL[r.novo_lider] : "—"}</td>
                <td className="text-right tabular-nums">{formatPct(r.distancia, 1)}</td>
                <td>{r.robustez ? <StatusBadge status={r.robustez === "fragil" ? "fail" : r.robustez === "atencao" ? "missing_source" : "pass"} label={ROBUSTNESS[r.robustez]?.label} /> : "—"}</td>
                <td className="text-xs">
                  {r.limite_juridico_valor === null ? "—"
                    : `${value(r, r.limite_juridico_valor)}${lost.length ? ` (${lost.map((x) => REGIME_LABEL[x]).join(", ")} deixa de ser elegível/calculável)` : ""}`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-slate-600">
        Robustez pela distância do cenário base até a virada: acima de 20% robusta; de 5% a 20% atenção; abaixo de 5% frágil.
      </p>
    </div>
  );
}
