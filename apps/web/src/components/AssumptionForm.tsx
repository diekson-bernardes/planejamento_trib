"use client";

import { useState, useTransition } from "react";

import { confirmAssumption } from "@/app/(app)/cases/[id]/planning/actions";
import { StatusBadge } from "@/components/StatusBadge";
import { formatAssumption, formatDateTime } from "@/lib/format";
import { normalizeDecimal } from "@/lib/schemas";

export type AssumptionRow = {
  id: string;
  key: string;
  scope: string;
  label: string;
  value_type: string;
  choices: unknown;
  suggested_value: unknown;
  suggested_origin: Record<string, unknown>;
  value: unknown;
  status: string;
  justification: string | null;
  confirmed_at: string | null;
};

const TAXES = ["icms", "iss", "pis", "cofins", "ipi"];
const ANEXOS = ["I", "II", "III", "IV", "V"];

function originText(origin: Record<string, unknown>): string {
  if (!origin) return "";
  const parts = [origin.note, origin.field_key, origin.doc_type, origin.page ? `p. ${origin.page}` : null,
    Array.isArray(origin.accounts) && origin.accounts.length ? `contas ${(origin.accounts as string[]).join(", ")}` : null,
    origin.rule];
  return parts.filter(Boolean).join(" · ");
}

export function AssumptionForm({ row, readOnly }: { row: AssumptionRow; readOnly: boolean }) {
  const initial = row.value ?? row.suggested_value;
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const presumidoChoices = (Array.isArray(row.choices) ? row.choices : [])
    .flatMap((c) => (c && typeof c === "object" && "presumido" in c ? (c as { presumido: string[] }).presumido : []));
  const declarationChoices = row.value_type === "choice" && Array.isArray(row.choices) ? (row.choices as string[]) : [];

  function send(value: unknown, justification: string) {
    setError(null);
    startTransition(async () => {
      const res = await confirmAssumption({ assumptionId: row.id, value, suggested: row.suggested_value, justification });
      if (res.ok) setEditing(false);
      else setError(res.error);
    });
  }

  function onSubmit(form: FormData) {
    const justification = String(form.get("justification") ?? "");
    let value: unknown = form.get("value");
    if (row.value_type === "decimal" || row.value_type === "percent" || row.value_type === "ratio")
      value = normalizeDecimal(String(value ?? ""));
    if (row.value_type === "boolean") value = form.get("value") === "true";
    if (row.value_type === "taxes") value = TAXES.filter((t) => form.get(`tax_${t}`) === "on");
    if (row.value_type === "profile") {
      value = {
        anexo: String(form.get("anexo")),
        presumido: String(form.get("presumido")),
        cumulativo_no_real: form.get("cumulativo_no_real") === "on",
        fator_r: form.get("fator_r") === "on",
        exportacao: form.get("exportacao") === "on",
      };
    }
    send(value, justification);
  }

  const profile = (initial ?? {}) as Record<string, unknown>;
  return (
    <li className="rounded-md border border-slate-200 bg-white p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-64 flex-1">
          <p className="text-sm font-medium">{row.label}</p>
          <p className="text-xs text-slate-500">{originText(row.suggested_origin)}</p>
        </div>
        <div className="text-right text-sm">
          <StatusBadge status={row.status === "confirmed" ? "done" : "queued"} label={row.status === "confirmed" ? "Confirmada" : "Pendente"} />
          <p className="mt-1">Sugerido: <strong>{formatAssumption(row.suggested_value, row.value_type)}</strong></p>
          {row.status === "confirmed" && (
            <p>Confirmado: <strong>{formatAssumption(row.value, row.value_type)}</strong></p>
          )}
          {row.justification && <p className="text-xs text-slate-600">“{row.justification}” · {formatDateTime(row.confirmed_at)}</p>}
        </div>
      </div>
      {!readOnly && !editing && (
        <div className="mt-2 flex gap-2">
          {row.status !== "confirmed" && row.suggested_value !== null && (
            <button type="button" className="btn-primary px-2 py-1 text-xs" disabled={pending}
              onClick={() => send(row.suggested_value, "")}>Confirmar sugerido</button>
          )}
          <button type="button" className="btn-secondary px-2 py-1 text-xs" onClick={() => setEditing(true)}>
            {row.suggested_value === null ? "Informar" : "Alterar"}
          </button>
        </div>
      )}
      {editing && (
        <form action={onSubmit} className="mt-3 space-y-2 border-t border-slate-100 pt-3">
          {(row.value_type === "decimal" || row.value_type === "percent" || row.value_type === "ratio") && (
            <div>
              <label className="label" htmlFor={`v-${row.id}`}>
                Valor {row.value_type === "percent" ? "(fração: 0,02 = 2%)"
                  : row.value_type === "ratio" ? "(fração com sinal: 0,15 = 15%; −0,05 = prejuízo de 5%)" : "(R$)"}
              </label>
              <input id={`v-${row.id}`} name="value" className="input max-w-64" inputMode="decimal"
                defaultValue={String(initial ?? "")} required />
            </div>
          )}
          {row.value_type === "boolean" && (
            <select name="value" className="input max-w-64" defaultValue={String(Boolean(initial))} aria-label="Valor">
              <option value="true">Sim</option>
              <option value="false">Não</option>
            </select>
          )}
          {row.value_type === "choice" && (
            <select name="value" className="input max-w-64" defaultValue={String(initial ?? "")} aria-label="Resposta">
              {declarationChoices.map((c) => (
                <option key={c} value={c}>{formatAssumption(c, "choice")}</option>
              ))}
            </select>
          )}
          {row.value_type === "taxes" && (
            <fieldset className="flex flex-wrap gap-3 text-sm">
              <legend className="label">Tributos zerados no Simples</legend>
              {TAXES.map((t) => (
                <label key={t} className="flex items-center gap-1">
                  <input type="checkbox" name={`tax_${t}`} defaultChecked={Array.isArray(initial) && (initial as string[]).includes(t)} />
                  {t.toUpperCase()}
                </label>
              ))}
            </fieldset>
          )}
          {row.value_type === "profile" && (
            <div className="grid gap-2 sm:grid-cols-2">
              <label className="text-sm">Anexo do Simples
                <select name="anexo" className="input" defaultValue={String(profile.anexo ?? "I")}>
                  {ANEXOS.map((a) => <option key={a} value={a}>{a}</option>)}
                </select>
              </label>
              <label className="text-sm">Presunção (Presumido)
                <select name="presumido" className="input" defaultValue={String(profile.presumido ?? presumidoChoices[0] ?? "")}>
                  {presumidoChoices.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" name="fator_r" defaultChecked={Boolean(profile.fator_r)} /> Sujeita ao Fator R (III × V)
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" name="cumulativo_no_real" defaultChecked={Boolean(profile.cumulativo_no_real)} />
                PIS/Cofins cumulativo no Real (ex.: hospitalar)
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" name="exportacao" defaultChecked={Boolean(profile.exportacao)} /> Exportação
              </label>
            </div>
          )}
          <div>
            <label className="label" htmlFor={`j-${row.id}`}>Justificativa (obrigatória se diferente do sugerido)</label>
            <textarea id={`j-${row.id}`} name="justification" className="input" rows={2} />
          </div>
          {error && <p role="alert" className="alert-error">{error}</p>}
          <div className="flex gap-2">
            <button type="submit" className="btn-primary px-2 py-1 text-xs" disabled={pending}>Salvar</button>
            <button type="button" className="btn-secondary px-2 py-1 text-xs" onClick={() => setEditing(false)}>Cancelar</button>
          </div>
        </form>
      )}
      {!editing && error && <p role="alert" className="alert-error mt-2">{error}</p>}
    </li>
  );
}
