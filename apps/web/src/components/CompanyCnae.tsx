import { requestCompanyLookup, setCompanyCnae, updateCompany } from "@/app/(app)/cases/actions";
import { formatCnae, formatDateTime } from "@/lib/format";

export type CompanyCnaeRow = {
  id: string;
  legal_name: string;
  razao_social_pendente: boolean;
  cnae_principal: string | null;
  cnae_descricao: string | null;
  cnaes_secundarios: unknown;
  cnae_origem: string | null;
  cnae_atualizado_em: string | null;
  cnae_consulta_status: string | null;
  cnae_consulta_erro: string | null;
};

/** Empresa do dossiê: razão social (digitada ou vinda da consulta pelo CNPJ) e CNAE (consulta à Receita pela
 *  automação n8n, no worker, ou digitação quando a consulta falhar). O CNAE é exigido só no planejamento rápido. */
export function CompanyCnae({ caseId, company, readOnly, cnaeRequired }: {
  caseId: string;
  company: CompanyCnaeRow;
  readOnly: boolean;
  cnaeRequired: boolean;
}) {
  const secundarios = Array.isArray(company.cnaes_secundarios)
    ? (company.cnaes_secundarios as { codigo: string; descricao?: string }[])
    : [];
  const pending = company.cnae_consulta_status === "pendente";
  return (
    <section className="card space-y-3" aria-labelledby="cnae-title">
      <h2 id="cnae-title">Empresa</h2>
      {company.razao_social_pendente ? (
        <p role="status" className="alert-warning">
          Razão social pendente: {pending ? "consultando a Receita pelo CNPJ…" : "a consulta não trouxe a razão social — informe abaixo."}
        </p>
      ) : (
        <p className="text-sm"><b>{company.legal_name}</b></p>
      )}
      {!readOnly && (
        <form action={updateCompany} className="flex flex-wrap items-end gap-2">
          <input type="hidden" name="caseId" value={caseId} />
          <input type="hidden" name="companyId" value={company.id} />
          <div>
            <label className="label" htmlFor="legal-name">Razão social</label>
            <input id="legal-name" name="legalName" className="input w-80" required
              defaultValue={company.razao_social_pendente ? "" : company.legal_name} />
          </div>
          <button type="submit" className="btn-secondary">Gravar razão social</button>
        </form>
      )}
      <h3 className="text-sm font-semibold">CNAE {cnaeRequired ? "(exigido no planejamento rápido)" : "(opcional)"}</h3>
      {company.cnae_principal ? (
        <div className="text-sm">
          <p>
            <b>{formatCnae(company.cnae_principal)}</b> {company.cnae_descricao}
            <span className="ml-2 text-xs text-slate-600">
              ({company.cnae_origem === "manual" ? "digitado" : "consulta à Receita"} em {formatDateTime(company.cnae_atualizado_em)})
            </span>
          </p>
          {secundarios.length > 0 && (
            <p className="text-xs text-slate-600">
              Secundários: {secundarios.map((c) => `${formatCnae(c.codigo)} ${c.descricao ?? ""}`).join("; ")}
            </p>
          )}
          <p className="text-xs text-slate-600">O anexo do Simples é sugerido pelo CNAE de cada atividade marcada abaixo e confirmado nas premissas.</p>
        </div>
      ) : (
        <p className="text-sm text-slate-600">
          CNAE ainda não informado{cnaeRequired ? " — a homologação exige o CNAE principal" : ""}.
        </p>
      )}
      {pending && <p role="status" className="alert-warning">Consulta em andamento… atualize a página em instantes.</p>}
      {company.cnae_consulta_status === "falhou" && (
        <p role="alert" className="alert-warning">Consulta indisponível: {company.cnae_consulta_erro}. Informe o CNAE abaixo.</p>
      )}
      {!readOnly && (
        <div className="flex flex-wrap items-end gap-3">
          <form action={requestCompanyLookup}>
            <input type="hidden" name="caseId" value={caseId} />
            <input type="hidden" name="companyId" value={company.id} />
            <button type="submit" className="btn-secondary" disabled={pending}>Consultar CNAE na Receita</button>
          </form>
          <form action={setCompanyCnae} className="flex flex-wrap items-end gap-2">
            <input type="hidden" name="caseId" value={caseId} />
            <input type="hidden" name="companyId" value={company.id} />
            <div>
              <label className="label" htmlFor="cnae">CNAE principal</label>
              <input id="cnae" name="cnae" className="input w-36" placeholder="4744-0/01" required />
            </div>
            <div>
              <label className="label" htmlFor="cnae-desc">Descrição (opcional)</label>
              <input id="cnae-desc" name="description" className="input w-64" />
            </div>
            <button type="submit" className="btn-secondary">Gravar CNAE digitado</button>
          </form>
        </div>
      )}
    </section>
  );
}
