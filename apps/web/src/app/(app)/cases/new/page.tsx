import Link from "next/link";

import { createCase, deleteCompany } from "@/app/(app)/cases/actions";
import { formatCnpj } from "@/lib/format";
import { getSessionContext } from "@/lib/supabase/server";

export default async function NewCasePage({ searchParams }: { searchParams: Promise<{ erro?: string; ok?: string }> }) {
  const { erro, ok } = await searchParams;
  const { supabase, office } = await getSessionContext();
  const { data: companies } = await supabase
    .from("companies")
    .select("id, legal_name, cnpj, tax_cases(id)")
    .eq("office_id", office!.office_id)
    .order("legal_name");

  const unused = (companies ?? []).filter((c) => !(c.tax_cases as { id: string }[] | null)?.length);

  return (
    <div className="max-w-2xl space-y-4">
      <div>
        <Link href="/cases" className="text-sm text-slate-600 hover:underline">← Dossiês</Link>
        <h1 className="mt-1">Novo dossiê</h1>
        <p className="text-sm text-slate-600">Um dossiê reúne os documentos de uma empresa em um período.</p>
      </div>
      {erro && <p role="alert" className="alert-error">{erro}</p>}
      {ok && <p role="status" className="alert-success">{ok}</p>}
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
              <label className="label" htmlFor="legalName">Razão social (opcional)</label>
              <input id="legalName" name="legalName" className="input" placeholder="Em branco: buscar na Receita pelo CNPJ" />
            </div>
          </div>
        </fieldset>
        <fieldset className="space-y-2">
          <legend className="text-sm font-semibold">Tipo do dossiê</legend>
          <label className="flex items-start gap-2 text-sm">
            <input type="radio" name="kind" value="completo" defaultChecked className="mt-1" />
            <span><b>Dossiê completo</b> — PGDAS-D, folha, DRE e balancete por competência, com conciliação.</span>
          </label>
          <label className="flex items-start gap-2 text-sm">
            <input type="radio" name="kind" value="rapido" className="mt-1" />
            <span>
              <b>Planejamento rápido (2027)</b> — faturamento dos últimos 12 meses, folha e DRE (PDF ou digitados);
              compara Simples por dentro, Simples por fora e Lucro Presumido. Informe os 12 meses no período.
            </span>
          </label>
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
      {unused.length > 0 && (
        <section className="card space-y-2" aria-labelledby="unused-title">
          <h2 id="unused-title">Empresas sem dossiê</h2>
          <ul className="space-y-1 text-sm">
            {unused.map((c) => (
              <li key={c.id} className="flex items-center justify-between gap-2">
                <span>{c.legal_name} ({formatCnpj(c.cnpj)})</span>
                <form action={deleteCompany}>
                  <input type="hidden" name="companyId" value={c.id} />
                  <button type="submit" className="text-xs text-red-700 underline">Excluir empresa</button>
                </form>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
