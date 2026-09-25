"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import type { Json } from "@/lib/database.types";
import { confirmAssumptionSchema, firstIssue, normalizeDecimal } from "@/lib/schemas";
import { createClient } from "@/lib/supabase/server";

export type PlanningResult = { ok: true } | { ok: false; error: string };

function back(caseId: string, kind: "erro" | "ok", message: string): never {
  redirect(`/cases/${caseId}/planning?${kind}=${encodeURIComponent(message)}`);
}

export async function startPlanning(formData: FormData) {
  const caseId = String(formData.get("caseId") ?? "");
  const supabase = await createClient();
  const { error } = await supabase.rpc("request_planning", { p_case_id: caseId });
  if (error) back(caseId, "erro", error.message);
  back(caseId, "ok", "Premissas sendo sugeridas a partir do snapshot. Atualize em instantes.");
}

/** Confirma (ou altera com justificativa) uma premissa. Valores decimais chegam em formato brasileiro. */
export async function confirmAssumption(input: unknown): Promise<PlanningResult> {
  const parsed = confirmAssumptionSchema.safeParse(input);
  if (!parsed.success) return { ok: false, error: firstIssue(parsed.error) };
  let value = parsed.data.value;
  if (typeof value === "string" && /^-?[\d.,]+$/.test(value)) value = normalizeDecimal(value);
  const supabase = await createClient();
  const { error } = await supabase.rpc("confirm_assumption", {
    p_id: parsed.data.assumptionId,
    p_value: value as Json,
    p_justification: parsed.data.justification ?? "",
  });
  if (error) return { ok: false, error: error.message };
  revalidatePath("/cases", "layout");
  return { ok: true };
}

export async function requestCalculation(formData: FormData) {
  const caseId = String(formData.get("caseId") ?? "");
  const supabase = await createClient();
  const { error } = await supabase.rpc("request_calculation", { p_case_id: caseId });
  if (error) back(caseId, "erro", error.message);
  back(caseId, "ok", "Cálculo solicitado. A simulação aparece na lista em instantes.");
}

export async function requestSimulationExport(formData: FormData) {
  const caseId = String(formData.get("caseId") ?? "");
  const simulationId = String(formData.get("simulationId") ?? "");
  const supabase = await createClient();
  const { error } = await supabase.rpc("request_simulation_export", { p_simulation_id: simulationId });
  const target = `/cases/${caseId}/planning/${simulationId}`;
  if (error) redirect(`${target}?erro=${encodeURIComponent(error.message)}`);
  redirect(`${target}?ok=${encodeURIComponent("Exportação solicitada. Atualize em instantes para baixar o XLSX.")}`);
}
