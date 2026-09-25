const brl = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function formatBRL(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  return brl.format(Number(value));
}

/** "2026-08-01" ou "2026-08" → "08/2026" */
export function formatCompetence(value: string | null | undefined): string {
  if (!value) return "—";
  const [year, month] = value.split("-");
  return `${month}/${year}`;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("pt-BR");
}

export function formatCnpj(value: string): string {
  const d = value.replace(/\D/g, "");
  return d.length === 14 ? `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}` : value;
}

export const DOC_TYPE_LABEL: Record<string, string> = {
  PGDAS_D: "PGDAS-D",
  FOLHA_ALTERDATA: "Folha (Alterdata)",
  DRE_ALTERDATA: "DRE (Alterdata)",
  BALANCETE_ALTERDATA: "Balancete (Alterdata)",
};

export type Tone = "neutral" | "info" | "success" | "warning" | "danger";

export const STATUS: Record<string, { label: string; tone: Tone }> = {
  // arquivos
  uploaded: { label: "Na fila", tone: "neutral" },
  processing: { label: "Processando", tone: "info" },
  extracted: { label: "Extraído", tone: "success" },
  failed: { label: "Falha na extração", tone: "danger" },
  rejected: { label: "Rejeitado", tone: "danger" },
  unclassified: { label: "Não classificado", tone: "warning" },
  cnpj_mismatch: { label: "CNPJ divergente", tone: "danger" },
  // dossiês
  draft: { label: "Rascunho", tone: "neutral" },
  review: { label: "Em revisão", tone: "info" },
  homologated: { label: "Homologado", tone: "success" },
  // conciliações e validações
  ok: { label: "Conciliado", tone: "success" },
  divergent: { label: "Divergente", tone: "danger" },
  missing_source: { label: "Fonte ausente", tone: "warning" },
  pass: { label: "OK", tone: "success" },
  fail: { label: "Falhou", tone: "danger" },
  // jobs
  queued: { label: "Na fila", tone: "neutral" },
  running: { label: "Executando", tone: "info" },
  done: { label: "Concluído", tone: "success" },
};

export const RULE_LABEL: Record<string, string> = {
  R1: "Receita",
  R2: "DAS",
  R3: "INSS",
  R4: "FGTS",
  R5: "Proventos",
  R6: "DAS anterior",
};

/** Meses (AAAA-MM) entre duas datas inclusive. */
export function monthsBetween(start: string, end: string): string[] {
  const out: string[] = [];
  let [y, m] = start.slice(0, 7).split("-").map(Number);
  const [ey, em] = end.slice(0, 7).split("-").map(Number);
  while (y < ey || (y === ey && m <= em)) {
    out.push(`${y}-${String(m).padStart(2, "0")}`);
    m += 1;
    if (m > 12) {
      m = 1;
      y += 1;
    }
  }
  return out;
}

export const REGIME_LABEL: Record<string, string> = {
  SIMPLES: "Simples Nacional",
  PRESUMIDO: "Lucro Presumido",
  REAL: "Lucro Real",
};

export const TAX_LABEL: Record<string, string> = {
  irpj: "IRPJ",
  adicional_irpj: "Adicional IRPJ",
  csll: "CSLL",
  pis: "PIS",
  cofins: "Cofins",
  cpp: "CPP",
  rat: "RAT",
  terceiros: "Terceiros",
  icms: "ICMS",
  iss: "ISS",
  ipi: "IPI",
};

export const ELIGIBILITY: Record<string, { label: string; tone: Tone }> = {
  elegivel: { label: "Elegível", tone: "success" },
  elegivel_com_alerta: { label: "Elegível com alerta", tone: "warning" },
  indeterminado: { label: "Indeterminado", tone: "warning" },
  inelegivel: { label: "Inelegível", tone: "danger" },
};

export const ASSUMPTION_GROUP_LABEL: Record<string, string> = {
  atividades: "Atividades (perfil por receita)",
  icms_iss: "ICMS e ISS no regime normal",
  receitas: "Outras receitas",
  pis_cofins: "PIS/Cofins",
  real: "Lucro Real",
  folha: "Encargos da folha",
  elegibilidade: "Elegibilidade",
};

/** "0.02" → "2,00%" quando é percentual; valores monetários em BRL; demais em texto. */
export function formatAssumption(value: unknown, type: string): string {
  if (value === null || value === undefined) return "—";
  if (type === "percent") return `${(Number(value) * 100).toFixed(2).replace(".", ",")}%`;
  if (type === "decimal") return formatBRL(String(value));
  if (type === "boolean") return value ? "Sim" : "Não";
  if (type === "taxes") return (value as string[]).length ? (value as string[]).map((t) => t.toUpperCase()).join(", ") : "nenhum";
  if (type === "profile") {
    const p = value as Record<string, unknown>;
    return `Anexo ${p.anexo} · ${p.presumido}${p.cumulativo_no_real ? " · cumulativo no Real" : ""}${p.fator_r ? " · Fator R" : ""}`;
  }
  if (value === "nao_informado") return "Não informado";
  if (value === "sim") return "Sim";
  if (value === "nao") return "Não";
  return String(value);
}
