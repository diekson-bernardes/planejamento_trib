import Link from "next/link";
import { notFound } from "next/navigation";

import { homologateCase, reclassifyFile, requestXlsx } from "@/app/(app)/cases/actions";
import { CompanyCnae, type CompanyCnaeRow } from "@/components/CompanyCnae";
import { ManualValuesForm, type ManualValueRow } from "@/components/ManualValuesForm";
import { StatusBadge } from "@/components/StatusBadge";
import { UploadDropzone } from "@/components/UploadDropzone";
import { CASE_KIND_LABEL, DOC_TYPE_LABEL, formatCnpj, formatCompetence, formatDateTime, monthsBetween } from "@/lib/format";
import { DOC_TYPES, REQUIRED_DOC_TYPES } from "@/lib/schemas";
import { getSessionContext } from "@/lib/supabase/server";

const BLOCKING_FILE_STATUS = ["uploaded", "processing", "failed", "rejected", "unclassified", "cnpj_mismatch"];

export default async function CasePage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ erro?: string; ok?: string }>;
}) {
  const { id } = await params;
  const { erro, ok } = await searchParams;
  const { supabase } = await getSessionContext();

  const { data: tc } = await supabase
    .from("tax_cases")
    .select("id, office_id, period_start, period_end, status, kind, companies(id, legal_name, cnpj, cnae_principal, cnae_descricao, cnaes_secundarios, cnae_origem, cnae_atualizado_em, cnae_consulta_status, cnae_consulta_erro)")
    .eq("id", id)
    .maybeSingle();
  if (!tc) notFound();
  const company = tc.companies as ({ legal_name: string; cnpj: string } & CompanyCnaeRow) | null;
  const rapido = tc.kind === "rapido";

  const [{ data: files }, { data: failing }, { data: recs }, { data: snapshot }, { data: exportJobs }] = await Promise.all([
    supabase
      .from("source_files")
      .select("id, original_name, doc_type, competence, status, error_code, error_message, parser_version, pages, created_at")
      .eq("case_id", id)
      .order("created_at"),
    supabase.from("validations").select("file_id, rule, detail").eq("case_id", id).eq("status", "fail"),
    supabase.from("reconciliations").select("status, justification").eq("case_id", id),
    supabase.from("snapshots").select("id, sha256, created_at").eq("case_id", id).maybeSingle(),
    supabase.from("jobs").select("status").eq("kind", "export_xlsx").contains("payload", { case_id: id }),
  ]);

  const homologated = tc.status === "homologated";
  const processing = (files ?? []).some((f) => f.status === "uploaded" || f.status === "processing");
  const blockingFiles = (files ?? []).filter((f) => BLOCKING_FILE_STATUS.includes(f.status));
  const unjustified = (recs ?? []).filter((r) => r.status === "divergent" && !r.justification).length;
  const missingSource = (recs ?? []).filter((r) => r.status === "missing_source").length;

  const extracted = (files ?? []).filter((f) => f.status === "extracted");
  const months = monthsBetween(tc.period_start, tc.period_end);
  // planejamento rápido: meses com PDF por documento, valores digitados e bloqueios da homologação
  let manual: ManualValueRow[] = [];
  let rapidoBlockers: string[] = [];
  const pdfMonths: Record<string, string[]> = {};
  if (rapido) {
    const [{ data: mv }, { data: decl }, blockers] = await Promise.all([
      supabase.from("manual_values").select("doc_type, competence, field_key, value").eq("case_id", id),
      supabase.from("extracted_values").select("competence").eq("case_id", id)
        .eq("doc_type", "DECLARACAO_FATURAMENTO").eq("field_key", "faturamento.mes"),
      homologated ? Promise.resolve({ data: [] as string[] }) : supabase.rpc("rapido_blockers", { p_case_id: id }),
    ]);
    manual = (mv ?? []) as ManualValueRow[];
    rapidoBlockers = (blockers.data ?? []) as string[];
    pdfMonths.DECLARACAO_FATURAMENTO = (decl ?? []).map((d) => d.competence.slice(0, 7));
    for (const doc of ["FOLHA_ALTERDATA", "DRE_ALTERDATA"]) {
      pdfMonths[doc] = extracted.filter((f) => f.doc_type === doc && f.competence).map((f) => f.competence!.slice(0, 7));
    }
  }
  const missingCompetences = rapido ? [] : months.flatMap((m) =>
    REQUIRED_DOC_TYPES.filter((t) => !extracted.some((f) => f.doc_type === t && f.competence?.startsWith(m))).map(
      (t) => `${DOC_TYPE_LABEL[t]} ${formatCompetence(m)}`,
    ),
  );

  const canHomologate = !homologated && ((files?.length ?? 0) > 0 || manual.length > 0) && blockingFiles.length === 0
    && unjustified === 0 && rapidoBlockers.length === 0;

  let xlsxReady = false;
  if (snapshot) {
    const { data: objects } = await supabase.storage.from("documents").list(`${tc.office_id}/${id}/exports`);
    xlsxReady = (objects ?? []).some((o) => o.name === `${snapshot.id}.xlsx`);
  }
  const xlsxPending = (exportJobs ?? []).some((j) => j.status === "queued" || j.status === "running");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link href="/cases" className="text-sm text-slate-600 hover:underline">← Dossiês</Link>
          <h1 className="mt-1">{company?.legal_name}</h1>
          <p className="text-sm text-slate-600">
            {company ? formatCnpj(company.cnpj) : ""} · {formatCompetence(tc.period_start)} a {formatCompetence(tc.period_end)}
            {" "}· {CASE_KIND_LABEL[tc.kind] ?? tc.kind}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={tc.status} />
          <Link href={`/cases/${id}/review`} className="btn-secondary">Revisar valores</Link>
          {!rapido && <Link href={`/cases/${id}/reconciliation`} className="btn-secondary">Conciliação</Link>}
          {homologated && (
            <Link href={`/cases/${id}/planning`} className="btn-primary">Planejamento</Link>
          )}
        </div>
      </div>

      {erro && <p role="alert" className="alert-error">{erro}</p>}
      {ok && <p role="status" className="alert-success">{ok}</p>}

      <section className="card space-y-3" aria-labelledby="upload-title">
        <h2 id="upload-title">Documentos</h2>
        <UploadDropzone caseId={id} officeId={tc.office_id} disabled={homologated} processing={processing} />
        {files && files.length > 0 && (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Arquivo</th>
                  <th>Tipo</th>
                  <th>Competência</th>
                  <th>Status</th>
                  <th>Detalhe</th>
                </tr>
              </thead>
              <tbody>
                {files.map((f) => {
                  const fileFails = (failing ?? []).filter((v) => v.file_id === f.id);
                  return (
                    <tr key={f.id}>
                      <td className="max-w-64 truncate" title={f.original_name ?? ""}>{f.original_name}</td>
                      <td>{f.doc_type ? DOC_TYPE_LABEL[f.doc_type] : "—"}</td>
                      <td>{formatCompetence(f.competence)}</td>
                      <td><StatusBadge status={f.status} /></td>
                      <td className="text-xs text-slate-600">
                        {f.error_message && <span className="block text-red-700">{f.error_message}</span>}
                        {f.parser_version && <span className="block">parser {f.parser_version}</span>}
                        {fileFails.length > 0 && (
                          <span className="block text-amber-800">{fileFails.length} validação(ões) interna(s) falharam</span>
                        )}
                        {f.status === "unclassified" && !homologated && (
                          <form action={reclassifyFile} className="mt-1 flex items-center gap-2">
                            <input type="hidden" name="caseId" value={id} />
                            <input type="hidden" name="fileId" value={f.id} />
                            <label className="sr-only" htmlFor={`dt-${f.id}`}>Classificar como</label>
                            <select id={`dt-${f.id}`} name="docType" className="input py-1 text-xs" required defaultValue="">
                              <option value="" disabled>Classificar como…</option>
                              {DOC_TYPES.map((t) => (
                                <option key={t} value={t}>{DOC_TYPE_LABEL[t]}</option>
                              ))}
                            </select>
                            <button type="submit" className="btn-secondary px-2 py-1 text-xs">Reprocessar</button>
                          </form>
                        )}
                        <span className="block text-slate-400">{formatDateTime(f.created_at)}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {rapido && company && <CompanyCnae caseId={id} company={company} readOnly={homologated} />}
      {rapido && (
        <ManualValuesForm caseId={id} months={months} pdfMonths={pdfMonths} manual={manual} readOnly={homologated} />
      )}

      <section className="card space-y-3" aria-labelledby="pend-title">
        <h2 id="pend-title">Pendências</h2>
        <ul className="space-y-2 text-sm">
          {rapidoBlockers.map((b) => (
            <li key={b} className="alert-error">{b} — bloqueia a homologação.</li>
          ))}
          {blockingFiles.length > 0 && (
            <li className="alert-error">{blockingFiles.length} arquivo(s) ainda não extraído(s) com sucesso — bloqueia a homologação.</li>
          )}
          {unjustified > 0 && (
            <li className="alert-error">
              {unjustified} divergência(s) de conciliação sem justificativa — bloqueia a homologação.{" "}
              <Link className="underline" href={`/cases/${id}/reconciliation`}>Ver conciliação</Link>
            </li>
          )}
          {(failing?.length ?? 0) > 0 && (
            <li className="alert-warning">
              {failing!.length} validação(ões) interna(s) falharam — revise e ajuste os valores com motivo.
            </li>
          )}
          {missingCompetences.length > 0 && (
            <li className="alert-warning">
              Competências sem documento (não bloqueia): {missingCompetences.join(", ")}.
            </li>
          )}
          {missingSource > 0 && (
            <li className="alert-warning">{missingSource} regra(s) de conciliação sem fonte suficiente (não bloqueia).</li>
          )}
          {!processing && blockingFiles.length === 0 && unjustified === 0 && (failing?.length ?? 0) === 0 && missingCompetences.length === 0
            && rapidoBlockers.length === 0 && (
            <li className="alert-success">Nenhuma pendência.</li>
          )}
        </ul>
      </section>

      <section className="card space-y-3" aria-labelledby="hom-title">
        <h2 id="hom-title">Homologação e exportação</h2>
        {snapshot ? (
          <div className="space-y-3 text-sm">
            <p>
              Homologado em {formatDateTime(snapshot.created_at)}. Hash do snapshot:{" "}
              <code className="break-all rounded bg-slate-100 px-1">{snapshot.sha256}</code>
            </p>
            <div className="flex flex-wrap gap-2">
              <a className="btn-secondary" href={`/api/cases/${id}/export?format=json`}>Baixar JSON</a>
              {xlsxReady ? (
                <a className="btn-secondary" href={`/api/cases/${id}/export?format=xlsx`}>Baixar XLSX</a>
              ) : (
                <form action={requestXlsx}>
                  <input type="hidden" name="caseId" value={id} />
                  <button className="btn-secondary" type="submit" disabled={xlsxPending}>
                    {xlsxPending ? "XLSX em geração…" : "Gerar XLSX"}
                  </button>
                </form>
              )}
            </div>
          </div>
        ) : (
          <form action={homologateCase} className="space-y-2">
            <input type="hidden" name="caseId" value={id} />
            <p className="text-sm text-slate-600">
              A homologação congela os dados (valores efetivos, ajustes, validações e conciliações) num snapshot com hash
              SHA-256. Depois dela o dossiê fica somente leitura.
            </p>
            <button className="btn-primary" type="submit" disabled={!canHomologate}>Homologar dossiê</button>
          </form>
        )}
      </section>
    </div>
  );
}
