import { clearManualValues, enterManualValues } from "@/app/(app)/cases/actions";
import { formatBRL, formatCompetence, MANUAL_FIELD_LABEL } from "@/lib/format";
import { MANUAL_FIELDS, type ManualDoc } from "@/lib/schemas";

export type ManualValueRow = { doc_type: string; competence: string; field_key: string; value: number | string };

const DOCS: { doc: ManualDoc; label: string; pdf: string }[] = [
  { doc: "FATURAMENTO", label: "Faturamento", pdf: "DECLARACAO_FATURAMENTO" },
  { doc: "FOLHA", label: "Folha", pdf: "FOLHA_ALTERDATA" },
  { doc: "DRE", label: "DRE", pdf: "DRE_ALTERDATA" },
];

/** Planejamento rápido: situação de cada mês (PDF, digitado ou ausente) e digitação do que não tem PDF. */
export function ManualValuesForm({ caseId, months, pdfMonths, manual, readOnly }: {
  caseId: string;
  months: string[];                         // AAAA-MM dos 12 meses do período
  pdfMonths: Record<string, string[]>;      // doc_type do PDF → meses com valores extraídos
  manual: ManualValueRow[];
  readOnly: boolean;
}) {
  const typed = (doc: ManualDoc, m: string) => manual.filter((v) => v.doc_type === doc && v.competence.startsWith(m));
  const cell = (doc: (typeof DOCS)[number], m: string) => {
    if (pdfMonths[doc.pdf]?.includes(m)) return <span className="text-emerald-700">PDF</span>;
    const rows = typed(doc.doc, m);
    if (!rows.length) return <span className="text-slate-400">—</span>;
    return (
      <span title={rows.map((r) => `${MANUAL_FIELD_LABEL[r.field_key]}: ${formatBRL(r.value)}`).join("\n")}>
        digitado{doc.doc === "FATURAMENTO" ? ` (${formatBRL(rows[0].value)})` : ""}
        {!readOnly && (
          <form action={clearManualValues} className="inline">
            <input type="hidden" name="caseId" value={caseId} />
            <input type="hidden" name="docType" value={doc.doc} />
            <input type="hidden" name="competence" value={m} />
            <button type="submit" className="ml-1 text-xs text-red-700 underline">remover</button>
          </form>
        )}
      </span>
    );
  };

  return (
    <section className="card space-y-4" aria-labelledby="manual-title">
      <div>
        <h2 id="manual-title">Faturamento, folha e DRE dos 12 meses</h2>
        <p className="text-sm text-slate-600">
          Envie a Declaração de Faturamento, a folha e a DRE em PDF acima, ou digite os meses sem PDF. A homologação exige
          os 12 meses de faturamento e ao menos um mês de folha e de DRE; meses com folha e DRE entram como realizados.
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead><tr><th>Mês</th>{DOCS.map((d) => <th key={d.doc}>{d.label}</th>)}</tr></thead>
          <tbody>
            {months.map((m) => (
              <tr key={m}>
                <td>{formatCompetence(m)}</td>
                {DOCS.map((d) => <td key={d.doc}>{cell(d, m)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!readOnly && (
        <div className="grid gap-4 lg:grid-cols-3">
          {DOCS.map((d) => (
            <form key={d.doc} action={enterManualValues} className="space-y-2 rounded border border-slate-200 p-3">
              <input type="hidden" name="caseId" value={caseId} />
              <input type="hidden" name="docType" value={d.doc} />
              <h3 className="text-sm font-semibold">Digitar {d.label}</h3>
              <div>
                <label className="label" htmlFor={`m-${d.doc}`}>Mês</label>
                <select id={`m-${d.doc}`} name="competence" className="input" required defaultValue="">
                  <option value="" disabled>Escolha o mês…</option>
                  {months.filter((m) => !pdfMonths[d.pdf]?.includes(m)).map((m) => (
                    <option key={m} value={m}>{formatCompetence(m)}</option>
                  ))}
                </select>
              </div>
              {MANUAL_FIELDS[d.doc].map((f) => (
                <div key={f}>
                  <label className="label" htmlFor={`${d.doc}-${f}`}>{MANUAL_FIELD_LABEL[f]} (R$)</label>
                  <input id={`${d.doc}-${f}`} name={f} className="input" inputMode="decimal" placeholder="0,00" />
                </div>
              ))}
              <button type="submit" className="btn-secondary">Gravar {d.label.toLowerCase()}</button>
            </form>
          ))}
        </div>
      )}
    </section>
  );
}
