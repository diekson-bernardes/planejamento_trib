import Link from "next/link";

import { createCase } from "@/app/(app)/cases/actions";
import { formatCnpj } from "@/lib/format";
import { getSessionContext } from "@/lib/supabase/server";

export default async function NewCasePage({ searchParams }: { searchParams: Promise<{ erro?: string }> }) {
  const { erro } = await searchParams;
  const { supabase, office } = await getSessionContext();
  const { data: companies } = await supabase
    .from("companies")
    .select("id, legal_name, cnpj")
    .eq("office_id", office!.office_id)
    .order("legal_name");

  return (
    <div className="max-w-2xl space-y-4">
      <div>
        <Link href="/cases" className="text-sm text-slate-600 hover:underline">← Dossiês</Link>
        <h1 className="mt-1">Novo dossiê</h1>
        <p className="text-sm text-slate-600">Um dossiê reúne os documentos de uma empresa em um período.</p>
      </div>
      {erro && <p role="alert" className="alert-error">{erro}</p>}
      <form action={createCase} className="card space-y-5">
        <fieldset className="space-y-3">
          <legend className="text-sm font-semibold">Empresa</legend>
          {companies && companies.length > 0 && (
            <div>
              <label className="label" htmlFor="companyId">Empresa já cadastrada</label>
              <select id="companyId" name="companyId" className="input" defaultValue="">
                <option value="">— Cadastrar nova empresa abaixo —</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>{c.legal_name} ({formatCnpj(c.cnpj)})</option>
                ))}
              </select>
            </div>
          )}
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="cnpj">CNPJ (nova empresa)</label>
              <input id="cnpj" name="cnpj" className="input" inputMode="numeric" placeholder="00.000.000/0000-00" />
            </div>
            <div>
              <label className="label" htmlFor="legalName">Razão social (nova empresa)</label>
              <input id="legalName" name="legalName" className="input" />
            </div>
          </div>
        </fieldset>
        <fieldset className="grid gap-3 sm:grid-cols-2">
          <legend className="mb-2 text-sm font-semibold">Período</legend>
          <div>
            <label className="label" htmlFor="periodStart">Competência inicial</label>
            <input id="periodStart" name="periodStart" type="month" className="input" required />
          </div>
          <div>
            <label className="label" htmlFor="periodEnd">Competência final</label>
            <input id="periodEnd" name="periodEnd" type="month" className="input" required />
          </div>
        </fieldset>
        <div className="flex justify-end">
          <button type="submit" className="btn-primary">Criar dossiê</button>
        </div>
      </form>
    </div>
  );
}
