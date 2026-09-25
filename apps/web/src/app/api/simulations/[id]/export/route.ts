import { NextResponse, type NextRequest } from "next/server";

import { createClient } from "@/lib/supabase/server";

/** GET → redireciona para URL assinada (60 s) do XLSX da memória de cálculo da simulação. */
export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 });

  // RLS: só retorna a simulação se o usuário for membro do escritório.
  const { data: sim } = await supabase.from("simulations").select("id, office_id, case_id").eq("id", id).maybeSingle();
  if (!sim) return NextResponse.json({ error: "Simulação não encontrada" }, { status: 404 });

  const path = `${sim.office_id}/${sim.case_id}/simulations/${sim.id}.xlsx`;
  const { data, error } = await supabase.storage
    .from("documents")
    .createSignedUrl(path, 60, { download: `simulacao-${sim.id.slice(0, 8)}.xlsx` });
  if (error || !data) return NextResponse.json({ error: "XLSX ainda não gerado" }, { status: 404 });
  return NextResponse.redirect(data.signedUrl, { headers: { "Cache-Control": "no-store" } });
}
