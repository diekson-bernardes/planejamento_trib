import Link from "next/link";
import { notFound } from "next/navigation";

import { ValueTable, type ValueRow } from "@/components/ValueTable";
import { getSessionContext } from "@/lib/supabase/server";

export default async function ReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { supabase } = await getSessionContext();

  const { data: tc } = await supabase.from("tax_cases").select("id, status").eq("id", id).maybeSingle();
  if (!tc) notFound();

  const [{ data: files }, values] = await Promise.all([
    supabase.from("source_files").select("id, original_name").eq("case_id", id),
    fetchAllValues(supabase, id),
  ]);
  const names = new Map((files ?? []).map((f) => [f.id, f.original_name ?? f.id]));
  const rows: ValueRow[] = values.map((v) => ({ ...v, file_name: names.get(v.file_id) ?? "" }));

  return (
    <div className="space-y-4">
      <div>
        <Link href={`/cases/${id}`} className="text-sm text-slate-600 hover:underline">← Dossiê</Link>
        <h1 className="mt-1">Revisão dos valores extraídos</h1>
        <p className="text-sm text-slate-600">
          Cada valor mostra o arquivo, a página e a posição de origem. Ajustes exigem motivo e preservam o valor original.
        </p>
      </div>
      {tc.status === "homologated" && <p className="alert-success">Dossiê homologado: somente leitura.</p>}
      {rows.length === 0 ? (
        <div className="card text-sm text-slate-600">Nenhum valor extraído ainda.</div>
      ) : (
        <ValueTable rows={rows} readOnly={tc.status === "homologated"} />
      )}
    </div>
  );
}

type Supabase = Awaited<ReturnType<typeof getSessionContext>>["supabase"];

/** PostgREST limita linhas por requisição: pagina até trazer tudo. */
async function fetchAllValues(supabase: Supabase, caseId: string) {
  const pageSize = 1000;
  const out: Omit<ValueRow, "file_name">[] = [];
  for (let from = 0; ; from += pageSize) {
    const { data, error } = await supabase
      .from("effective_values")
      .select(
        "id, file_id, doc_type, competence, section, field_key, label, account_code, column_name, value, effective_value, adjusted, last_reason, adjusted_at, nature, page, bbox",
      )
      .eq("case_id", caseId)
      .order("file_id")
      .order("ordinal")
      .range(from, from + pageSize - 1);
    if (error || !data?.length) break;
    out.push(...(data as Omit<ValueRow, "file_name">[]));
    if (data.length < pageSize) break;
  }
  return out;
}
