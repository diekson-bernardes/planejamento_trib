import { NextResponse, type NextRequest } from "next/server";

import { createClient } from "@/lib/supabase/server";

/** GET → redireciona para URL assinada (60 s) do PDF emitido da recomendação (RLS: só membros do escritório). */
export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 });

  const { data: rec } = await supabase
    .from("recommendations")
    .select("id, status, pdf_path")
    .eq("id", id)
    .maybeSingle();
  if (!rec) return NextResponse.json({ error: "Recomendação não encontrada" }, { status: 404 });
  if (rec.status !== "emitida" || !rec.pdf_path) {
    return NextResponse.json({ error: "PDF ainda não emitido" }, { status: 404 });
  }
  const { data, error } = await supabase.storage
    .from("documents")
    .createSignedUrl(rec.pdf_path, 60, { download: `recomendacao-${rec.id.slice(0, 8)}.pdf` });
  if (error || !data) return NextResponse.json({ error: "PDF indisponível" }, { status: 404 });
  return NextResponse.redirect(data.signedUrl, { headers: { "Cache-Control": "no-store" } });
}
