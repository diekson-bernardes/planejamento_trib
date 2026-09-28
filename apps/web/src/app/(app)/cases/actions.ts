"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import type { TablesInsert } from "@/lib/database.types";
import {
  adjustValueSchema,
  cnaeSchema,
  createCaseSchema,
  MANUAL_FIELDS,
  type ManualDoc,
  manualValuesSchema,
  firstIssue,
  justifySchema,
  normalizeDecimal,
  onlyDigits,
  reclassifySchema,
  registerUploadSchema,
} from "@/lib/schemas";
import { createClient, getSessionContext, OFFICE_COOKIE } from "@/lib/supabase/server";

export type ActionResult = { ok: true; duplicate?: boolean } | { ok: false; error: string };

function fail(error: string): ActionResult {
  return { ok: false, error };
}

function withError(path: string, message: string): never {
  redirect(`${path}?erro=${encodeURIComponent(message)}`);
}

/* ------------------------------------------------------------------ sessão */
export async function selectOffice(formData: FormData) {
  const { memberships } = await getSessionContext();
  const officeId = String(formData.get("officeId") ?? "");
  if (memberships.some((m) => m.office_id === officeId)) {
    (await cookies()).set(OFFICE_COOKIE, officeId, { httpOnly: true, sameSite: "lax", path: "/" });
  }
  redirect("/cases");
}

export async function signOut() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  (await cookies()).delete(OFFICE_COOKIE);
  redirect("/login");
}

/* ------------------------------------------------------------------ empresa e dossiê */
export async function createCase(formData: FormData) {
  const { supabase, office } = await getSessionContext();
  if (!office) withError("/cases/new", "Você não pertence a nenhum escritório.");

  const parsed = createCaseSchema.safeParse({
    companyId: formData.get("companyId") || undefined,
    cnpj: formData.get("cnpj") ? onlyDigits(String(formData.get("cnpj"))) : undefined,
    legalName: formData.get("legalName") || undefined,
    periodStart: formData.get("periodStart"),
    periodEnd: formData.get("periodEnd"),
    kind: formData.get("kind") || undefined,
  });
  if (!parsed.success) withError("/cases/new", firstIssue(parsed.error));
  const input = parsed.data;

  let companyId = input.companyId;
  if (!companyId) {
    const { data, error } = await supabase
      .from("companies")
      .insert({ office_id: office.office_id, cnpj: input.cnpj!, legal_name: input.legalName! })
      .select("id")
      .single();
    if (error) {
      withError("/cases/new", error.code === "23505" ? "Empresa já cadastrada neste escritório." : error.message);
    }
    companyId = data.id;
  }

  const [ey, em] = input.periodEnd.split("-").map(Number);
  const lastDay = new Date(Date.UTC(ey, em, 0)).getUTCDate();
  const { data: created, error } = await supabase
    .from("tax_cases")
    .insert({
      office_id: office.office_id,
      company_id: companyId,
      period_start: `${input.periodStart}-01`,
      period_end: `${input.periodEnd}-${String(lastDay).padStart(2, "0")}`,
      kind: input.kind,
    })
    .select("id")
    .single();
  if (error) withError("/cases/new", error.message);
  revalidatePath("/cases");
  redirect(`/cases/${created.id}`);
}

/* ------------------------------------------------------------------ upload */
export async function registerUpload(input: unknown): Promise<ActionResult> {
  const parsed = registerUploadSchema.safeParse(input);
  if (!parsed.success) return fail(firstIssue(parsed.error));
  const v = parsed.data;

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return fail("Sessão expirada. Entre novamente.");

  const { data: tc } = await supabase.from("tax_cases").select("id, office_id, status").eq("id", v.caseId).single();
  if (!tc) return fail("Dossiê não encontrado.");
  if (tc.status === "homologated") return fail("Dossiê homologado: não aceita novos arquivos.");
  if (!v.storagePath.startsWith(`${tc.office_id}/${tc.id}/${v.fileId}`)) return fail("Caminho de arquivo inválido.");

  const { error } = await supabase.from("source_files").insert({
    id: v.fileId,
    office_id: tc.office_id,
    case_id: tc.id,
    storage_path: v.storagePath,
    original_name: v.originalName,
    sha256: v.sha256,
    size_bytes: v.sizeBytes,
    uploaded_by: user.id,
  });
  if (error) {
    if (error.code === "23505") return { ok: true, duplicate: true };
    return fail(error.message);
  }
  revalidatePath(`/cases/${tc.id}`);
  return { ok: true };
}

export async function reclassifyFile(formData: FormData) {
  const caseId = String(formData.get("caseId") ?? "");
  const parsed = reclassifySchema.safeParse({ fileId: formData.get("fileId"), docType: formData.get("docType") });
  if (!parsed.success) withError(`/cases/${caseId}`, firstIssue(parsed.error));
  const supabase = await createClient();
  const { error } = await supabase
    .from("source_files")
    .update({ doc_type: parsed.data.docType })
    .eq("id", parsed.data.fileId);
  if (error) withError(`/cases/${caseId}`, error.message);
  revalidatePath(`/cases/${caseId}`);
  redirect(`/cases/${caseId}`);
}

/** URL assinada de curta duração para abrir o PDF original na página do valor. */
export async function getFileUrl(fileId: string): Promise<{ url: string } | { error: string }> {
  const supabase = await createClient();
  const { data: file } = await supabase.from("source_files").select("storage_path").eq("id", fileId).single();
  if (!file) return { error: "Arquivo não encontrado." };
  const { data, error } = await supabase.storage.from("documents").createSignedUrl(file.storage_path, 60);
  if (error || !data) return { error: "Não foi possível gerar o link do arquivo." };
  return { url: data.signedUrl };
}

/* ------------------------------------------------------------------ revisão e conciliação */
export async function adjustValue(input: unknown): Promise<ActionResult> {
  const parsed = adjustValueSchema.safeParse(input);
  if (!parsed.success) return fail(firstIssue(parsed.error));

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return fail("Sessão expirada. Entre novamente.");

  // office_id, case_id e old_value são preenchidos pelo trigger a partir do valor ajustado.
  const row = {
    value_id: parsed.data.valueId,
    new_value: Number(normalizeDecimal(parsed.data.newValue)),
    reason: parsed.data.reason,
    author: user.id,
  } as unknown as TablesInsert<"value_adjustments">;
  const { error } = await supabase.from("value_adjustments").insert(row);
  if (error) return fail(error.message.includes("homologado") ? "Dossiê homologado: somente leitura." : error.message);
  revalidatePath("/cases", "layout");
  return { ok: true };
}

export async function justifyReconciliation(input: unknown): Promise<ActionResult> {
  const parsed = justifySchema.safeParse(input);
  if (!parsed.success) return fail(firstIssue(parsed.error));
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("reconciliations")
    .update({ justification: parsed.data.justification })
    .eq("id", parsed.data.reconciliationId)
    .select("id");
  if (error) return fail(error.message.includes("homologado") ? "Dossiê homologado: somente leitura." : error.message);
  if (!data?.length) return fail("Conciliação não encontrada.");
  revalidatePath("/cases", "layout");
  return { ok: true };
}

/* ------------------------------------------------------------------ homologação e exportação */
export async function homologateCase(formData: FormData) {
  const caseId = String(formData.get("caseId") ?? "");
  const supabase = await createClient();
  const { error } = await supabase.rpc("homologate_case", { p_case_id: caseId });
  if (error) withError(`/cases/${caseId}`, error.message);
  revalidatePath(`/cases/${caseId}`);
  redirect(`/cases/${caseId}?ok=${encodeURIComponent("Dossiê homologado.")}`);
}

export async function requestXlsx(formData: FormData) {
  const caseId = String(formData.get("caseId") ?? "");
  const supabase = await createClient();
  const { error } = await supabase.rpc("request_xlsx_export", { p_case_id: caseId });
  if (error) withError(`/cases/${caseId}`, error.message);
  redirect(`/cases/${caseId}?ok=${encodeURIComponent("Exportação XLSX solicitada. Atualize em instantes.")}`);
}

/* ------------------------------------------------------------------ planejamento rápido (ciclo 5) */
/** Digitação de faturamento, folha ou DRE de um mês sem PDF (a RPC recusa mês com PDF extraído). */
export async function enterManualValues(formData: FormData) {
  const caseId = String(formData.get("caseId") ?? "");
  const docType = String(formData.get("docType") ?? "") as ManualDoc;
  const back = `/cases/${caseId}`;
  const values: Record<string, string> = {};
  for (const key of MANUAL_FIELDS[docType] ?? []) {
    const raw = String(formData.get(key) ?? "").trim();
    if (raw) values[key] = raw;
  }
  const parsed = manualValuesSchema.safeParse({ caseId, docType, competence: formData.get("competence"), values });
  if (!parsed.success) withError(back, firstIssue(parsed.error));
  const v = parsed.data;
  const supabase = await createClient();
  const { error } = await supabase.rpc("enter_manual_values", {
    p_case_id: v.caseId,
    p_doc_type: v.docType,
    p_competence: `${v.competence}-01`,
    p_values: v.values,
  });
  if (error) withError(back, error.message);
  revalidatePath(back);
  redirect(`${back}?ok=${encodeURIComponent("Valores digitados gravados.")}`);
}

export async function clearManualValues(formData: FormData) {
  const caseId = String(formData.get("caseId") ?? "");
  const supabase = await createClient();
  const { error } = await supabase.rpc("clear_manual_values", {
    p_case_id: caseId,
    p_doc_type: String(formData.get("docType") ?? ""),
    p_competence: `${String(formData.get("competence") ?? "")}-01`,
  });
  if (error) withError(`/cases/${caseId}`, error.message);
  revalidatePath(`/cases/${caseId}`);
  redirect(`/cases/${caseId}?ok=${encodeURIComponent("Valores digitados removidos.")}`);
}

/** Consulta o CNAE na Receita pela automação (job do worker). */
export async function requestCompanyLookup(formData: FormData) {
  const caseId = String(formData.get("caseId") ?? "");
  const supabase = await createClient();
  const { error } = await supabase.rpc("request_company_lookup", { p_company_id: String(formData.get("companyId") ?? "") });
  if (error) withError(`/cases/${caseId}`, error.message);
  redirect(`/cases/${caseId}?ok=${encodeURIComponent("Consulta do CNAE solicitada. Atualize em instantes.")}`);
}

export async function setCompanyCnae(formData: FormData) {
  const caseId = String(formData.get("caseId") ?? "");
  const parsed = cnaeSchema.safeParse({
    companyId: formData.get("companyId"),
    cnae: String(formData.get("cnae") ?? ""),
    description: formData.get("description") || undefined,
  });
  if (!parsed.success) withError(`/cases/${caseId}`, firstIssue(parsed.error));
  const supabase = await createClient();
  const { error } = await supabase.rpc("set_company_cnae", {
    p_company_id: parsed.data.companyId,
    p_cnae: parsed.data.cnae,
    p_descricao: parsed.data.description ?? "",
  });
  if (error) withError(`/cases/${caseId}`, error.message);
  revalidatePath(`/cases/${caseId}`);
  redirect(`/cases/${caseId}?ok=${encodeURIComponent("CNAE gravado.")}`);
}
