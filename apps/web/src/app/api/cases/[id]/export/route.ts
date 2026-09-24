import { NextResponse, type NextRequest } from "next/server";

import { createClient } from "@/lib/supabase/server";

/** GET ?format=json → snapshot homologado; ?format=xlsx → redireciona para URL assinada do XLSX. */
export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const format = request.nextUrl.searchParams.get("format") ?? "json";
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Não autenticado" }, { status: 401 });

  // RLS: só retorna o snapshot se o usuário for membro do escritório.
  const { data: snapshot } = await supabase
    .from("snapshots")
    .select("id, office_id, case_id, sha256, content, created_at")
    .eq("case_id", id)
    .maybeSingle();
  if (!snapshot) return NextResponse.json({ error: "Dossiê não homologado ou inexistente" }, { status: 404 });

  if (format === "json") {
    const body = JSON.stringify({ sha256: snapshot.sha256, created_at: snapshot.created_at, content: snapshot.content }, null, 2);
    return new NextResponse(body, {
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Disposition": `attachment; filename="dossie-${id}-${snapshot.sha256.slice(0, 12)}.json"`,
        "Cache-Control": "no-store",
      },
    });
  }

  if (format === "xlsx") {
    const path = `${snapshot.office_id}/${snapshot.case_id}/exports/${snapshot.id}.xlsx`;
    const { data, error } = await supabase.storage.from("documents").createSignedUrl(path, 60, {
      download: `dossie-${id}-${snapshot.sha256.slice(0, 12)}.xlsx`,
    });
    if (error || !data) return NextResponse.json({ error: "XLSX ainda não gerado" }, { status: 404 });
    return NextResponse.redirect(data.signedUrl, { headers: { "Cache-Control": "no-store" } });
  }

  return NextResponse.json({ error: "Formato inválido (use json ou xlsx)" }, { status: 400 });
}
