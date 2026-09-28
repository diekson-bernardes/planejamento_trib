import Link from "next/link";

import { deleteCase } from "@/app/(app)/cases/actions";
import { StatusBadge } from "@/components/StatusBadge";
import { CASE_KIND_LABEL, formatCnpj, formatCompetence, formatDateTime } from "@/lib/format";
import { getSessionContext } from "@/lib/supabase/server";

export default async function CasesPage({ searchParams }: { searchParams: Promise<{ erro?: string; ok?: string }> }) {
  const { erro, ok } = await searchParams;
  const { supabase, office } = await getSessionContext();
  const { data: cases, error } = await supabase
    .from("tax_cases")
    .select("id, period_start, period_end, status, kind, created_at, companies(legal_name, cnpj)")
    .eq("office_id", office!.office_id)
    .order("created_at", { ascending: false });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1>Dossiês</h1>
        <Link href="/cases/new" className="btn-primary">Novo dossiê</Link>
      </div>
      {erro && <p role="alert" className="alert-error">{erro}</p>}
      {ok && <p role="status" className="alert-success">{ok}</p>}
      {error && <p className="alert-error">Não foi possível carregar os dossiês.</p>}
      {!cases?.length ? (
        <div className="card text-sm text-slate-600">
          Nenhum dossiê ainda. Crie um dossiê completo (PGDAS-D e Alterdata) ou um planejamento rápido (faturamento dos
          últimos 12 meses, folha e DRE).
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="data-table">
            <thead>
              <tr>
                <th>Empresa</th>
                <th>CNPJ</th>
                <th>Tipo</th>
                <th>Período</th>
                <th>Status</th>
                <th>Criado em</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => {
                const company = c.companies as { legal_name: string; cnpj: string } | null;
                const homologated = c.status === "homologated";
                return (
                  <tr key={c.id}>
                    <td>
                      <Link href={`/cases/${c.id}`} className="font-medium text-brand-700 underline-offset-2 hover:underline">
                        {company?.legal_name}
                      </Link>
                    </td>
                    <td className="whitespace-nowrap">{company ? formatCnpj(company.cnpj) : "—"}</td>
                    <td className="whitespace-nowrap">
                      <span className={c.kind === "rapido"
                        ? "rounded-full bg-violet-50 px-2 py-0.5 text-xs font-medium text-violet-800"
                        : "rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700"}>
                        {CASE_KIND_LABEL[c.kind] ?? c.kind}
                      </span>
                    </td>
                    <td className="whitespace-nowrap">{formatCompetence(c.period_start)} a {formatCompetence(c.period_end)}</td>
                    <td><StatusBadge status={c.status} /></td>
                    <td className="whitespace-nowrap text-slate-600">{formatDateTime(c.created_at)}</td>
                    <td className="whitespace-nowrap text-sm">
                      <div className="flex items-start gap-3">
                        <Link href={`/cases/${c.id}#${homologated ? "danger-title" : "edit-title"}`}
                          className="text-brand-700 underline" title={homologated ? "Dossiê homologado: reabra para editar" : undefined}>
                          {homologated ? "Reabrir" : "Editar"}
                        </Link>
                        <details className="relative">
                          <summary className="cursor-pointer text-red-700 underline">Excluir</summary>
                          <form action={deleteCase}
                            className="absolute right-0 z-10 mt-2 w-72 space-y-2 rounded-lg border border-slate-200 bg-white p-3 shadow-lg">
                            <input type="hidden" name="caseId" value={c.id} />
                            <input type="hidden" name="back" value="/cases" />
                            <p className="whitespace-normal text-xs text-slate-600">
                              Apaga o dossiê com arquivos, premissas, projeções e PDFs. Não pode ser desfeito.
                            </p>
                            <label className="label" htmlFor={`reason-${c.id}`}>Motivo</label>
                            <input id={`reason-${c.id}`} name="reason" className="input" required minLength={5} />
                            <label className="flex items-center gap-2 whitespace-normal text-xs">
                              <input type="checkbox" name="confirm" required /> Confirmo a exclusão definitiva
                            </label>
                            <button type="submit" className="btn-danger w-full">Excluir dossiê</button>
                          </form>
                        </details>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
