"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { firstIssue, projectionYearSchema, returnRecommendationSchema } from "@/lib/schemas";
import { createClient } from "@/lib/supabase/server";

function to(path: string, kind: "erro" | "ok", message: string): never {
  redirect(`${path}?${kind}=${encodeURIComponent(message)}`);
}

function fields(formData: FormData) {
  const caseId = String(formData.get("caseId") ?? "");
  const projectionId = String(formData.get("projectionId") ?? "");
  const recommendationId = String(formData.get("recommendationId") ?? "");
  return { caseId, recommendationId, page: `/cases/${caseId}/planning/projection/${projectionId}` };
}

/** Pede a projeção do exercício (worker: projeção → motor → sensibilidade → recomendação em rascunho).
 *  2027 = projeção de 2026 deslocada com o crescimento informado, sob as regras da Reforma. */
export async function requestProjection(formData: FormData) {
  const caseId = String(formData.get("caseId") ?? "");
  const back = `/cases/${caseId}/planning`;
  const parsed = projectionYearSchema.safeParse({ year: formData.get("year") ?? 2026 });
  if (!parsed.success) to(back, "erro", firstIssue(parsed.error));
  const year = parsed.data.year;
  const supabase = await createClient();
  const { error } = await supabase.rpc("request_projection", { p_case_id: caseId, p_year: year });
  if (error) to(back, "erro", error.message);
  to(back, "ok", `Projeção ${year} solicitada. Ela aparece na lista de projeções em instantes.`);
}

export async function submitRecommendation(formData: FormData) {
  const { recommendationId, page } = fields(formData);
  const supabase = await createClient();
  const { error } = await supabase.rpc("submit_recommendation", { p_id: recommendationId });
  if (error) to(page, "erro", error.message);
  revalidatePath("/cases", "layout");
  to(page, "ok", "Recomendação enviada para revisão do responsável técnico.");
}

export async function approveRecommendation(formData: FormData) {
  const { recommendationId, page } = fields(formData);
  const supabase = await createClient();
  const { error } = await supabase.rpc("approve_recommendation", { p_id: recommendationId });
  if (error) to(page, "erro", error.message);
  revalidatePath("/cases", "layout");
  to(page, "ok", "Recomendação aprovada. Solicite a emissão do PDF.");
}

export async function returnRecommendation(formData: FormData) {
  const { recommendationId, page } = fields(formData);
  const parsed = returnRecommendationSchema.safeParse({ recommendationId, comment: formData.get("comment") ?? "" });
  if (!parsed.success) to(page, "erro", firstIssue(parsed.error));
  const supabase = await createClient();
  const { error } = await supabase.rpc("return_recommendation", {
    p_id: parsed.data.recommendationId,
    p_comment: parsed.data.comment,
  });
  if (error) to(page, "erro", error.message);
  revalidatePath("/cases", "layout");
  to(page, "ok", "Recomendação devolvida ao elaborador com o comentário.");
}

export async function requestReport(formData: FormData) {
  const { recommendationId, page } = fields(formData);
  const supabase = await createClient();
  const { error } = await supabase.rpc("request_report", { p_id: recommendationId });
  if (error) to(page, "erro", error.message);
  to(page, "ok", "Emissão solicitada. Atualize em instantes para baixar o PDF.");
}
