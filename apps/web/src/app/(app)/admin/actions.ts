"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import {
  firstIssue,
  inviteSchema,
  mappingSchema,
  technicalResponsibleSchema,
  thresholdSchema,
  toleranceSchema,
} from "@/lib/schemas";
import { createAdminClient, listUserEmails } from "@/lib/supabase/admin";
import { getSessionContext } from "@/lib/supabase/server";

function back(kind: "erro" | "ok", message: string): never {
  redirect(`/admin?${kind}=${encodeURIComponent(message)}`);
}

/** Confirma no banco (is_admin) que o usuário administra o escritório ativo. */
async function requireAdmin() {
  const ctx = await getSessionContext();
  if (!ctx.office) back("erro", "Nenhum escritório ativo.");
  const { data: isAdmin } = await ctx.supabase.rpc("is_admin", { p_office: ctx.office.office_id });
  if (!isAdmin) back("erro", "Acesso restrito ao administrador do escritório.");
  return { ...ctx, office: ctx.office };
}

export async function inviteAnalyst(formData: FormData) {
  const { supabase, office } = await requireAdmin();
  const parsed = inviteSchema.safeParse({ email: String(formData.get("email") ?? "").trim().toLowerCase() });
  if (!parsed.success) back("erro", firstIssue(parsed.error));
  const email = parsed.data.email;

  const admin = createAdminClient();
  let userId: string | undefined;
  const { data: invited, error: inviteError } = await admin.auth.admin.inviteUserByEmail(email);
  if (invited?.user) {
    userId = invited.user.id;
  } else {
    // Usuário já existente (ex.: membro de outro escritório): localizar pelo e-mail em todas as páginas.
    const emails = await listUserEmails();
    userId = [...emails].find(([, e]) => e === email)?.[0];
    if (!userId) back("erro", inviteError?.message ?? "Não foi possível convidar o usuário.");
  }

  // Inserção com o JWT do admin: a RLS (is_admin) é a autorização final.
  const { error } = await supabase
    .from("office_members")
    .insert({ office_id: office.office_id, user_id: userId!, role: "analyst" });
  if (error && error.code !== "23505") back("erro", error.message);
  revalidatePath("/admin");
  back("ok", `Convite enviado para ${email}.`);
}

export async function updateTolerance(formData: FormData) {
  const { supabase, office } = await requireAdmin();
  const raw = String(formData.get("tolerance") ?? "").replace(",", ".");
  const parsed = toleranceSchema.safeParse({ tolerance: Number(raw) });
  if (!parsed.success || raw === "") back("erro", parsed.success ? "Informe a tolerância." : firstIssue(parsed.error));

  const { data: current } = await supabase.from("offices").select("settings").eq("id", office.office_id).single();
  const settings = { ...((current?.settings as Record<string, unknown>) ?? {}), tolerance_brl: parsed.data.tolerance };
  const { error } = await supabase.from("offices").update({ settings }).eq("id", office.office_id);
  if (error) back("erro", error.message);
  revalidatePath("/admin");
  back("ok", "Tolerância atualizada. Vale para as próximas conciliações.");
}

export async function upsertMapping(formData: FormData) {
  const { supabase, office } = await requireAdmin();
  const parsed = mappingSchema.safeParse({
    target: formData.get("target"),
    docType: formData.get("docType"),
    accountCode: formData.get("accountCode"),
  });
  if (!parsed.success) back("erro", firstIssue(parsed.error));
  const m = parsed.data;

  const { data: existing } = await supabase
    .from("account_mappings")
    .select("id")
    .eq("office_id", office.office_id)
    .is("company_id", null)
    .eq("target", m.target)
    .eq("doc_type", m.docType)
    .maybeSingle();

  const { error } = existing
    ? await supabase.from("account_mappings").update({ account_code: m.accountCode }).eq("id", existing.id)
    : await supabase
        .from("account_mappings")
        .insert({ office_id: office.office_id, target: m.target, doc_type: m.docType, account_code: m.accountCode });
  if (error) back("erro", error.message);
  revalidatePath("/admin");
  back("ok", "Mapeamento salvo.");
}

/** Limiar de "resultado inconclusivo" (percentual informado na tela → fração). */
export async function updateThreshold(formData: FormData) {
  const { supabase, office } = await requireAdmin();
  const raw = String(formData.get("threshold") ?? "").replace(",", ".").trim();
  const parsed = thresholdSchema.safeParse({ threshold: raw === "" ? NaN : Number(raw) / 100 });
  if (!parsed.success) back("erro", raw === "" ? "Informe o limiar." : firstIssue(parsed.error));
  const { error } = await supabase.rpc("set_decision_threshold", {
    p_office: office.office_id,
    p_threshold: parsed.data.threshold,
  });
  if (error) back("erro", error.message);
  revalidatePath("/admin");
  back("ok", "Limiar atualizado. Vale para as próximas projeções.");
}

/** Marca/desmarca membro como responsável técnico (nome profissional e CRC obrigatórios ao marcar). */
export async function setTechnicalResponsible(formData: FormData) {
  const { supabase, office } = await requireAdmin();
  const parsed = technicalResponsibleSchema.safeParse({
    userId: formData.get("userId"),
    flag: formData.get("flag") === "true",
    name: String(formData.get("name") ?? ""),
    crc: String(formData.get("crc") ?? ""),
  });
  if (!parsed.success) back("erro", firstIssue(parsed.error));
  const { error } = await supabase.rpc("set_technical_responsible", {
    p_office: office.office_id,
    p_user: parsed.data.userId,
    p_flag: parsed.data.flag,
    p_name: parsed.data.name ?? "",
    p_crc: parsed.data.crc ?? "",
  });
  if (error) back("erro", error.message);
  revalidatePath("/admin");
  back("ok", parsed.data.flag ? "Responsável técnico registrado." : "Marcação de responsável técnico removida.");
}
