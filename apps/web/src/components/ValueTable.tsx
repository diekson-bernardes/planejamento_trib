"use client";

import { useMemo, useState, useTransition } from "react";

import { adjustValue, getFileUrl } from "@/app/(app)/cases/actions";
import { DOC_TYPE_LABEL, formatBRL, formatCompetence, formatDateTime } from "@/lib/format";

export type ValueRow = {
  id: string;
  file_id: string;
  file_name: string;
  doc_type: string;
  competence: string;
  section: string;
  field_key: string;
  label: string;
  account_code: string | null;
  column_name: string | null;
  value: number;
  effective_value: number;
  adjusted: boolean;
  last_reason: string | null;
  adjusted_at: string | null;
  nature: string | null;
  page: number;
  bbox: number[];
};

export function ValueTable({ rows, readOnly }: { rows: ValueRow[]; readOnly: boolean }) {
  const [docType, setDocType] = useState("");
  const [query, setQuery] = useState("");
  const [onlyAdjusted, setOnlyAdjusted] = useState(false);
  const [editing, setEditing] = useState<ValueRow | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter(
      (r) =>
        (!docType || r.doc_type === docType) &&
        (!onlyAdjusted || r.adjusted) &&
        (!q ||
          r.label.toLowerCase().includes(q) ||
          r.field_key.toLowerCase().includes(q) ||
          (r.account_code ?? "").toLowerCase().includes(q)),
    );
  }, [rows, docType, query, onlyAdjusted]);

  async function openOrigin(row: ValueRow) {
    // Abre a janela ainda dentro do clique (evita bloqueio de popup) e só depois define o endereço.
    const win = window.open("about:blank", "_blank");
    const res = await getFileUrl(row.file_id);
    if ("url" in res && win) {
      win.opener = null;
      win.location.href = `${res.url}#page=${row.page}`;
    } else {
      win?.close();
      alert("error" in res ? res.error : "Permita pop-ups para abrir o documento de origem.");
    }
  }

  function submit(form: FormData) {
    if (!editing) return;
    setError(null);
    startTransition(async () => {
      const res = await adjustValue({
        valueId: editing.id,
        newValue: String(form.get("newValue") ?? ""),
        reason: String(form.get("reason") ?? ""),
      });
      if (res.ok) setEditing(null);
      else setError(res.error);
    });
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label className="label" htmlFor="f-doc">Documento</label>
          <select id="f-doc" className="input" value={docType} onChange={(e) => setDocType(e.target.value)}>
            <option value="">Todos</option>
            {Object.entries(DOC_TYPE_LABEL).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>
        <div className="min-w-64 flex-1">
          <label className="label" htmlFor="f-q">Buscar</label>
          <input id="f-q" className="input" placeholder="Rótulo, campo ou código de conta" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <label className="flex items-center gap-2 pb-2 text-sm">
          <input type="checkbox" checked={onlyAdjusted} onChange={(e) => setOnlyAdjusted(e.target.checked)} />
          Só ajustados
        </label>
        <span className="pb-2 text-xs text-slate-500">{filtered.length} de {rows.length} valores</span>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="data-table">
          <thead>
            <tr>
              <th>Documento</th>
              <th>Competência</th>
              <th>Seção / campo</th>
              <th>Rótulo</th>
              <th>Coluna</th>
              <th className="num">Original</th>
              <th className="num">Efetivo</th>
              <th>Origem</th>
              {!readOnly && <th />}
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <tr key={r.id} className={r.adjusted ? "bg-amber-50/60" : undefined}>
                <td className="whitespace-nowrap">{DOC_TYPE_LABEL[r.doc_type] ?? r.doc_type}</td>
                <td>{formatCompetence(r.competence)}</td>
                <td className="font-mono text-xs text-slate-600">
                  {r.section}
                  <br />
                  {r.field_key}
                </td>
                <td>{r.label}</td>
                <td className="text-xs text-slate-600">{r.column_name ?? "—"}</td>
                <td className="num">{formatBRL(r.value)}{r.nature ? ` ${r.nature}` : ""}</td>
                <td className="num font-medium">
                  {formatBRL(r.effective_value)}
                  {r.adjusted && (
                    <span className="block text-xs font-normal text-amber-800" title={r.last_reason ?? ""}>
                      ajustado {formatDateTime(r.adjusted_at)}
                    </span>
                  )}
                </td>
                <td className="whitespace-nowrap text-xs">
                  <button type="button" className="text-brand-700 underline" onClick={() => openOrigin(r)}>
                    {r.file_name} · p. {r.page}
                  </button>
                  <span className="block text-slate-400">
                    x {Math.round(r.bbox[0])} · y {Math.round(r.bbox[1])}
                  </span>
                </td>
                {!readOnly && (
                  <td>
                    <button type="button" className="btn-secondary px-2 py-1 text-xs" onClick={() => { setEditing(r); setError(null); }}>
                      Ajustar
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <div role="dialog" aria-modal="true" aria-labelledby="adj-title" className="fixed inset-0 z-10 flex items-center justify-center bg-slate-900/40 p-4">
          <form action={submit} className="card w-full max-w-md space-y-3">
            <h2 id="adj-title">Ajustar valor</h2>
            <p className="text-sm text-slate-600">
              {editing.label} ({editing.field_key}{editing.column_name ? ` · ${editing.column_name}` : ""})
              <br />
              Original: <strong>{formatBRL(editing.value)}</strong> · Efetivo: <strong>{formatBRL(editing.effective_value)}</strong>
            </p>
            <div>
              <label className="label" htmlFor="newValue">Novo valor</label>
              <input id="newValue" name="newValue" className="input" inputMode="decimal" defaultValue={String(editing.effective_value)} required />
            </div>
            <div>
              <label className="label" htmlFor="reason">Motivo (obrigatório)</label>
              <textarea id="reason" name="reason" className="input" rows={3} minLength={5} required />
            </div>
            <p className="text-xs text-slate-500">O valor original é preservado; o ajuste fica registrado com autor, data e motivo.</p>
            {error && <p role="alert" className="alert-error">{error}</p>}
            <div className="flex justify-end gap-2">
              <button type="button" className="btn-secondary" onClick={() => setEditing(null)}>Cancelar</button>
              <button type="submit" className="btn-primary" disabled={pending}>{pending ? "Salvando…" : "Salvar ajuste"}</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
