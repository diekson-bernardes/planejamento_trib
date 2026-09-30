"use client";

import { useMemo, useState } from "react";

import { saveActivities } from "@/app/(app)/cases/actions";
import { formatCnae } from "@/lib/format";
import { onlyDigits, percentToCents } from "@/lib/schemas";

export type ActivityRow = { cnae: string; descricao: string | null; percentual: number | string; origem: string };
type Option = { cnae: string; descricao: string; origem: "receita" | "manual" };
type Item = Option & { on: boolean; percentual: string };

/** Atividades do planejamento rápido: CNAEs da Receita (principal e secundários) ou digitados, com o percentual do
 *  faturamento de cada um. Com mais de uma atividade, a soma precisa ser exatamente 100,00% (conferida também no banco). */
export function CaseActivities({ caseId, principal, secundarios, saved, readOnly }: {
  caseId: string;
  principal: { cnae: string | null; descricao: string | null };
  secundarios: { codigo: string; descricao?: string }[];
  saved: ActivityRow[];
  readOnly: boolean;
}) {
  const initial = useMemo(() => {
    const opts: Option[] = [];
    if (principal.cnae) opts.push({ cnae: principal.cnae, descricao: principal.descricao ?? "", origem: "receita" });
    for (const s of secundarios) opts.push({ cnae: onlyDigits(s.codigo), descricao: s.descricao ?? "", origem: "receita" });
    for (const r of saved) {
      if (!opts.some((o) => o.cnae === r.cnae)) {
        opts.push({ cnae: r.cnae, descricao: r.descricao ?? "", origem: r.origem === "receita" ? "receita" : "manual" });
      }
    }
    const byCnae = new Map(saved.map((r) => [r.cnae, r]));
    return opts.map<Item>((o, i) => {
      const s = byCnae.get(o.cnae);
      const on = saved.length ? Boolean(s) : i === 0;
      const pct = s ? Number(s.percentual).toFixed(2).replace(".", ",") : on ? "100,00" : "";
      return { ...o, on, percentual: pct };
    });
  }, [principal.cnae, principal.descricao, secundarios, saved]);

  const [items, setItems] = useState<Item[]>(initial);
  const [newCnae, setNewCnae] = useState("");
  const [newDesc, setNewDesc] = useState("");

  const marked = items.filter((i) => i.on);
  const totalCents = marked.reduce((acc, i) => acc + (percentToCents(i.percentual) ?? 0), 0);
  const sumOk = marked.length === 1 || totalCents === 10000;
  const payload = JSON.stringify(marked.map((i) => ({ cnae: i.cnae, descricao: i.descricao, percentual: i.percentual, origem: i.origem })));

  function update(cnae: string, patch: Partial<Item>) {
    setItems((prev) => prev.map((i) => (i.cnae === cnae ? { ...i, ...patch } : i)));
  }

  function addManual() {
    const cnae = onlyDigits(newCnae);
    if (cnae.length !== 7 || items.some((i) => i.cnae === cnae)) return;
    setItems((prev) => [...prev, { cnae, descricao: newDesc.trim(), origem: "manual", on: true, percentual: "" }]);
    setNewCnae("");
    setNewDesc("");
  }

  if (readOnly) {
    const rows = saved.length ? saved : principal.cnae ? [{ cnae: principal.cnae, descricao: principal.descricao, percentual: 100, origem: "receita" }] : [];
    return (
      <section className="card space-y-3" aria-labelledby="activities-title">
        <h2 id="activities-title">Atividades da empresa</h2>
        <table className="data-table">
          <thead><tr><th>CNAE</th><th>Descrição</th><th className="text-right">% do faturamento</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.cnae}>
                <td className="whitespace-nowrap">{formatCnae(r.cnae)}</td>
                <td>{r.descricao}</td>
                <td className="text-right">{Number(r.percentual).toFixed(2).replace(".", ",")}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    );
  }

  return (
    <section className="card space-y-3" aria-labelledby="activities-title">
      <h2 id="activities-title">Atividades da empresa</h2>
      <p className="text-sm text-slate-600">
        Marque as atividades que a empresa exerce e informe a parte do faturamento de cada uma. Com mais de uma, a soma
        precisa ser exatamente 100,00%. O anexo de cada atividade é sugerido pelo CNAE e confirmado nas premissas.
      </p>
      {items.length === 0 ? (
        <p className="alert-warning">Informe o CNAE principal acima ou inclua uma atividade abaixo.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr><th>Exerce</th><th>CNAE</th><th>Descrição</th><th>Origem</th><th className="text-right">% do faturamento</th></tr>
          </thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.cnae}>
                <td>
                  <input type="checkbox" aria-label={`Exerce a atividade ${formatCnae(i.cnae)}`} checked={i.on}
                    onChange={(e) => update(i.cnae, { on: e.target.checked })} />
                </td>
                <td className="whitespace-nowrap">{formatCnae(i.cnae)}</td>
                <td>{i.descricao || "—"}</td>
                <td className="text-xs text-slate-600">{i.origem === "receita" ? "Receita" : "digitado"}</td>
                <td className="text-right">
                  <input className="input w-24 text-right" inputMode="decimal" aria-label={`Percentual de ${formatCnae(i.cnae)}`}
                    disabled={!i.on || marked.length === 1} value={marked.length === 1 && i.on ? "100,00" : i.percentual}
                    onChange={(e) => update(i.cnae, { percentual: e.target.value })} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p role="status" aria-live="polite" className={sumOk ? "text-sm text-slate-700" : "text-sm font-medium text-red-700"}>
        {marked.length === 0
          ? "Nenhuma atividade marcada."
          : marked.length === 1
            ? "Uma atividade marcada: recebe 100% do faturamento."
            : `Soma: ${(totalCents / 100).toFixed(2).replace(".", ",")}%${sumOk ? "" : " — precisa ser exatamente 100,00%"}`}
      </p>
      <div className="flex flex-wrap items-end gap-2">
        <div>
          <label className="label" htmlFor="new-cnae">Incluir CNAE</label>
          <input id="new-cnae" className="input w-36" placeholder="0000-0/00" value={newCnae} onChange={(e) => setNewCnae(e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="new-cnae-desc">Descrição</label>
          <input id="new-cnae-desc" className="input w-80" maxLength={300} value={newDesc} onChange={(e) => setNewDesc(e.target.value)} />
        </div>
        <button type="button" className="btn-secondary" onClick={addManual} disabled={onlyDigits(newCnae).length !== 7}>
          Incluir
        </button>
      </div>
      <form action={saveActivities}>
        <input type="hidden" name="caseId" value={caseId} />
        <input type="hidden" name="items" value={payload} />
        <button type="submit" className="btn-primary" disabled={marked.length === 0 || !sumOk}>Gravar atividades</button>
      </form>
    </section>
  );
}
