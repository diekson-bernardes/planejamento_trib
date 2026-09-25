"use client";

import { useState, useTransition } from "react";

import { justifyReconciliation } from "@/app/(app)/cases/actions";
import { StatusBadge } from "@/components/StatusBadge";
import { formatBRL, formatCompetence, formatDateTime, RULE_LABEL } from "@/lib/format";

export type ReconciliationRow = {
  id: string;
  competence: string;
  rule: string;
  description: string;
  left_label: string;
  left_value: number | null;
  right_label: string;
  right_value: number | null;
  diff: number | null;
  tolerance: number;
  status: string;
  justification: string | null;
  justified_at: string | null;
};

export function ReconciliationTable({ rows, readOnly }: { rows: ReconciliationRow[]; readOnly: boolean }) {
  const [editing, setEditing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function submit(id: string, form: FormData) {
    setError(null);
    startTransition(async () => {
      const res = await justifyReconciliation({
        reconciliationId: id,
        justification: String(form.get("justification") ?? ""),
      });
      if (res.ok) setEditing(null);
      else setError(res.error);
    });
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="data-table">
        <thead>
          <tr>
            <th>Competência</th>
            <th>Regra</th>
            <th>Fonte A</th>
            <th className="num">Valor A</th>
            <th>Fonte B</th>
            <th className="num">Valor B</th>
            <th className="num">Diferença</th>
            <th>Status</th>
            <th>Justificativa</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const needsJustification = r.status === "divergent" && !r.justification;
            return (
              <tr key={r.id} className={needsJustification ? "bg-red-50/60" : undefined}>
                <td>{formatCompetence(r.competence)}</td>
                <td className="whitespace-nowrap">
                  <strong>{r.rule}</strong> {RULE_LABEL[r.rule]}
                  <span className="block text-xs text-slate-500">{r.description}</span>
                </td>
                <td className="text-xs">{r.left_label}</td>
                <td className="num">{formatBRL(r.left_value)}</td>
                <td className="text-xs">{r.right_label}</td>
                <td className="num">{formatBRL(r.right_value)}</td>
                <td className="num">
                  {formatBRL(r.diff)}
                  <span className="block text-xs text-slate-400">tol. {formatBRL(r.tolerance)}</span>
                </td>
                <td><StatusBadge status={r.status} /></td>
                <td className="min-w-64 text-sm">
                  {r.justification && (
                    <p>
                      {r.justification}
                      <span className="block text-xs text-slate-500">{formatDateTime(r.justified_at)}</span>
                    </p>
                  )}
                  {!readOnly && r.status === "divergent" && editing !== r.id && (
                    <button type="button" className="btn-secondary mt-1 px-2 py-1 text-xs" onClick={() => { setEditing(r.id); setError(null); }}>
                      {r.justification ? "Alterar justificativa" : "Justificar"}
                    </button>
                  )}
                  {editing === r.id && (
                    <form action={(fd) => submit(r.id, fd)} className="mt-1 space-y-2">
                      <label className="sr-only" htmlFor={`j-${r.id}`}>Justificativa</label>
                      <textarea id={`j-${r.id}`} name="justification" className="input" rows={3} minLength={5} required defaultValue={r.justification ?? ""} />
                      {error && <p role="alert" className="alert-error">{error}</p>}
                      <div className="flex gap-2">
                        <button type="submit" className="btn-primary px-2 py-1 text-xs" disabled={pending}>Salvar</button>
                        <button type="button" className="btn-secondary px-2 py-1 text-xs" onClick={() => setEditing(null)}>Cancelar</button>
                      </div>
                    </form>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
