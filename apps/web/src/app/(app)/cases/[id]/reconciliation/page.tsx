import Link from "next/link";
import { notFound } from "next/navigation";

import { ReconciliationTable, type ReconciliationRow } from "@/components/ReconciliationTable";
import { getSessionContext } from "@/lib/supabase/server";

export default async function ReconciliationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { supabase } = await getSessionContext();

  const { data: tc } = await supabase.from("tax_cases").select("id, status").eq("id", id).maybeSingle();
  if (!tc) notFound();

  const { data } = await supabase
    .from("reconciliations")
    .select(
      "id, competence, rule, description, left_label, left_value, right_label, right_value, diff, tolerance, status, justification, justified_at",
    )
    .eq("case_id", id)
    .order("competence")
    .order("rule");
  const rows = (data ?? []) as ReconciliationRow[];
  const divergent = rows.filter((r) => r.status === "divergent" && !r.justification).length;

  return (
    <div className="space-y-4">
      <div>
        <Link href={`/cases/${id}`} className="text-sm text-slate-600 hover:underline">← Dossiê</Link>
        <h1 className="mt-1">Conciliação entre fontes</h1>
        <p className="text-sm text-slate-600">
          PGDAS-D × DRE/balancete × folha, por competência. Diferença acima da tolerância bloqueia a homologação até
          ser corrigida (ajuste de valor) ou justificada. Fonte ausente é apenas alerta.
        </p>
      </div>
      {divergent > 0 && <p className="alert-error">{divergent} divergência(s) aguardando correção ou justificativa.</p>}
      {rows.length === 0 ? (
        <div className="card text-sm text-slate-600">A conciliação aparece depois que os documentos forem extraídos.</div>
      ) : (
        <ReconciliationTable rows={rows} readOnly={tc.status === "homologated"} />
      )}
    </div>
  );
}
