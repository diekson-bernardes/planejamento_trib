import { inviteAnalyst, updateTolerance, upsertMapping } from "@/app/(app)/admin/actions";
import { DOC_TYPE_LABEL, formatBRL } from "@/lib/format";
import { MAPPING_TARGETS } from "@/lib/schemas";
import { listUserEmails } from "@/lib/supabase/admin";
import { getSessionContext } from "@/lib/supabase/server";

const TARGET_LABEL: Record<string, string> = {
  vendas: "Vendas (R1)",
  simples_despesa: "Despesa Simples Nacional (R2)",
  simples_a_recolher: "Simples Nacional a Recolher (R6)",
  inss_a_pagar: "INSS a Pagar (R3)",
  fgts_a_pagar: "FGTS a Pagar (R4)",
  salarios_a_pagar: "Salários a Pagar (R5)",
};

export default async function AdminPage({ searchParams }: { searchParams: Promise<{ erro?: string; ok?: string }> }) {
  const { erro, ok } = await searchParams;
  const { supabase, office } = await getSessionContext();
  const { data: isAdmin } = await supabase.rpc("is_admin", { p_office: office!.office_id });
  if (!isAdmin) return <p className="alert-error">Acesso restrito ao administrador do escritório.</p>;

  const [{ data: members }, { data: officeRow }, { data: mappings }] = await Promise.all([
    supabase.from("office_members").select("user_id, role, created_at").eq("office_id", office!.office_id),
    supabase.from("offices").select("name, settings").eq("id", office!.office_id).single(),
    supabase
      .from("account_mappings")
      .select("target, doc_type, account_code")
      .eq("office_id", office!.office_id)
      .is("company_id", null),
  ]);

  // E-mails ficam em auth.users (fora da RLS): leitura via chave de serviço, somente para o admin.
  const emails = await listUserEmails();
  const tolerance = (officeRow?.settings as { tolerance_brl?: number } | null)?.tolerance_brl ?? 1;
  const code = (target: string, docType: string) =>
    mappings?.find((m) => m.target === target && m.doc_type === docType)?.account_code ?? "";

  return (
    <div className="space-y-6">
      <div>
        <h1>Administração — {officeRow?.name}</h1>
        <p className="text-sm text-slate-600">Membros, tolerância de conciliação e contas-alvo do plano de contas Alterdata.</p>
      </div>
      {erro && <p role="alert" className="alert-error">{erro}</p>}
      {ok && <p role="status" className="alert-success">{ok}</p>}

      <section className="card space-y-3" aria-labelledby="members-title">
        <h2 id="members-title">Membros</h2>
        <table className="data-table">
          <thead><tr><th>E-mail</th><th>Papel</th></tr></thead>
          <tbody>
            {(members ?? []).map((m) => (
              <tr key={m.user_id}>
                <td>{emails.get(m.user_id) ?? m.user_id}</td>
                <td>{m.role === "admin" ? "Administrador" : "Analista"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <form action={inviteAnalyst} className="flex flex-wrap items-end gap-2">
          <div className="min-w-64 flex-1">
            <label className="label" htmlFor="email">Convidar analista (e-mail)</label>
            <input id="email" name="email" type="email" className="input" required />
          </div>
          <button type="submit" className="btn-primary">Enviar convite</button>
        </form>
      </section>

      <section className="card space-y-3" aria-labelledby="tol-title">
        <h2 id="tol-title">Tolerância de conciliação</h2>
        <p className="text-sm text-slate-600">
          Diferença máxima aceita entre fontes. Atual: <strong>R$ {formatBRL(tolerance)}</strong>. Acima dela, a homologação
          fica bloqueada até correção ou justificativa.
        </p>
        <form action={updateTolerance} className="flex items-end gap-2">
          <div>
            <label className="label" htmlFor="tolerance">Nova tolerância (R$)</label>
            <input id="tolerance" name="tolerance" className="input" inputMode="decimal" defaultValue={String(tolerance)} required />
          </div>
          <button type="submit" className="btn-primary">Salvar</button>
        </form>
      </section>

      <section className="card space-y-3" aria-labelledby="map-title">
        <h2 id="map-title">Contas-alvo da conciliação (padrão do escritório)</h2>
        <p className="text-sm text-slate-600">
          Balancete: código reduzido (ex.: 40101). DRE: classificação (ex.: 4.1.1.01.001).
        </p>
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead><tr><th>Conta-alvo</th><th>Documento</th><th>Código</th><th /></tr></thead>
            <tbody>
              {MAPPING_TARGETS.flatMap((target) =>
                (["BALANCETE_ALTERDATA", "DRE_ALTERDATA"] as const)
                  .filter((d) => d === "BALANCETE_ALTERDATA" || target === "vendas" || target === "simples_despesa")
                  .map((docType) => (
                    <tr key={`${target}-${docType}`}>
                      <td>{TARGET_LABEL[target]}</td>
                      <td>{DOC_TYPE_LABEL[docType]}</td>
                      <td colSpan={2}>
                        <form action={upsertMapping} className="flex items-center gap-2">
                          <input type="hidden" name="target" value={target} />
                          <input type="hidden" name="docType" value={docType} />
                          <label className="sr-only" htmlFor={`c-${target}-${docType}`}>Código</label>
                          <input id={`c-${target}-${docType}`} name="accountCode" className="input max-w-48 py-1" defaultValue={code(target, docType)} required />
                          <button type="submit" className="btn-secondary px-2 py-1 text-xs">Salvar</button>
                        </form>
                      </td>
                    </tr>
                  )),
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
