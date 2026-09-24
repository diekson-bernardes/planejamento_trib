import Link from "next/link";

import { StatusBadge } from "@/components/StatusBadge";
import { formatCnpj, formatCompetence, formatDateTime } from "@/lib/format";
import { getSessionContext } from "@/lib/supabase/server";

export default async function CasesPage() {
  const { supabase, office } = await getSessionContext();
  const { data: cases, error } = await supabase
    .from("tax_cases")
    .select("id, period_start, period_end, status, created_at, companies(legal_name, cnpj)")
    .eq("office_id", office!.office_id)
    .order("created_at", { ascending: false });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1>Dossiês</h1>
        <Link href="/cases/new" className="btn-primary">Novo dossiê</Link>
      </div>
      {error && <p className="alert-error">Não foi possível carregar os dossiês.</p>}
      {!cases?.length ? (
        <div className="card text-sm text-slate-600">
          Nenhum dossiê ainda. Crie um dossiê para a empresa e o período e envie os PDFs do PGDAS-D e da Alterdata.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="data-table">
            <thead>
              <tr>
                <th>Empresa</th>
                <th>CNPJ</th>
                <th>Período</th>
                <th>Status</th>
                <th>Criado em</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => {
                const company = c.companies as { legal_name: string; cnpj: string } | null;
                return (
                  <tr key={c.id}>
                    <td>
                      <Link href={`/cases/${c.id}`} className="font-medium text-brand-700 underline-offset-2 hover:underline">
                        {company?.legal_name}
                      </Link>
                    </td>
                    <td className="whitespace-nowrap">{company ? formatCnpj(company.cnpj) : "—"}</td>
                    <td className="whitespace-nowrap">{formatCompetence(c.period_start)} a {formatCompetence(c.period_end)}</td>
                    <td><StatusBadge status={c.status} /></td>
                    <td className="whitespace-nowrap text-slate-600">{formatDateTime(c.created_at)}</td>
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
