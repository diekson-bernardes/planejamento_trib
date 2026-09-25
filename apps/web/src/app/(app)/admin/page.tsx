import {
  inviteAnalyst,
  setTechnicalResponsible,
  updateThreshold,
  updateTolerance,
  upsertMapping,
} from "@/app/(app)/admin/actions";
import { DOC_TYPE_LABEL, formatBRL, formatPct } from "@/lib/format";
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
    supabase
      .from("office_members")
      .select("user_id, role, created_at, is_technical_responsible, professional_name, crc")
      .eq("office_id", office!.office_id),
    supabase.from("offices").select("name, settings").eq("id", office!.office_id).single(),
    supabase
      .from("account_mappings")
      .select("target, doc_type, account_code")
      .eq("office_id", office!.office_id)
      .is("company_id", null),
  ]);

  // E-mails ficam em auth.users (fora da RLS): leitura via chave de serviço, somente para o admin.
  const emails = await listUserEmails();
  const settings = (officeRow?.settings ?? {}) as { tolerance_brl?: number; decision_threshold?: number };
  const tolerance = settings.tolerance_brl ?? 1;
  const threshold = settings.decision_threshold ?? 0.05;
  const code = (target: string, docType: string) =>
    mappings?.find((m) => m.target === target && m.doc_type === docType)?.account_code ?? "";

  return (
    <div className="space-y-6">
      <div>
        <h1>Administração — {officeRow?.name}</h1>
        <p className="text-sm text-slate-600">
          Membros e responsáveis técnicos, tolerância de conciliação, limiar da recomendação e contas-alvo do plano Alterdata.
        </p>
      </div>
      {erro && <p role="alert" className="alert-error">{erro}</p>}
      {ok && <p role="status" className="alert-success">{ok}</p>}

      <section className="card space-y-3" aria-labelledby="members-title">
        <h2 id="members-title">Membros</h2>
        <table className="data-table">
          <thead><tr><th>E-mail</th><th>Papel</th><th>Responsável técnico (aprova recomendações)</th></tr></thead>
          <tbody>
            {(members ?? []).map((m) => (
              <tr key={m.user_id}>
                <td>{emails.get(m.user_id) ?? m.user_id}</td>
                <td>{m.role === "admin" ? "Administrador" : "Analista"}</td>
                <td>
                  <form action={setTechnicalResponsible} className="flex flex-wrap items-center gap-2">
                    <input type="hidden" name="userId" value={m.user_id} />
                    <input type="hidden" name="flag" value={m.is_technical_responsible ? "false" : "true"} />
                    {m.is_technical_responsible ? (
                      <>
                        <span className="text-sm">{m.professional_name} · CRC {m.crc}</span>
                        <button type="submit" className="btn-secondary px-2 py-1 text-xs">Remover</button>
                      </>
                    ) : (
                      <>
                        <label className="sr-only" htmlFor={`n-${m.user_id}`}>Nome profissional</label>
                        <input id={`n-${m.user_id}`} name="name" className="input max-w-48 py-1" placeholder="Nome profissional" defaultValue={m.professional_name ?? ""} />
                        <label className="sr-only" htmlFor={`c-${m.user_id}`}>CRC</label>
                        <input id={`c-${m.user_id}`} name="crc" className="input max-w-36 py-1" placeholder="CRC (ex.: SP-123456/O-7)" defaultValue={m.crc ?? ""} />
                        <button type="submit" className="btn-secondary px-2 py-1 text-xs">Marcar</button>
                      </>
                    )}
                  </form>
                </td>
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

      <section className="card space-y-3" aria-labelledby="thr-title">
        <h2 id="thr-title">Limiar da recomendação</h2>
        <p className="text-sm text-slate-600">
          Se a diferença entre os dois regimes mais baratos for menor que este percentual do custo do vencedor, a recomendação
          sai como <strong>resultado inconclusivo</strong>. Atual: <strong>{formatPct(threshold)}</strong>.
        </p>
        <form action={updateThreshold} className="flex items-end gap-2">
          <div>
            <label className="label" htmlFor="threshold">Novo limiar (%)</label>
            <input id="threshold" name="threshold" className="input" inputMode="decimal"
              defaultValue={String(Number(threshold) * 100).replace(".", ",")} required />
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
