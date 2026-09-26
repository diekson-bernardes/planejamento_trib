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
  LIVRO_ICMS_ALTERDATA: "Livro de Apuração do ICMS (Alterdata)",
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
  // recomendação (ciclo 3)
  rascunho: { label: "Rascunho", tone: "neutral" },
  em_revisao: { label: "Em revisão", tone: "info" },
  aprovada: { label: "Aprovada", tone: "success" },
  emitida: { label: "Emitida", tone: "success" },
  recomendado: { label: "Recomendado", tone: "success" },
  inconclusivo: { label: "Resultado inconclusivo", tone: "warning" },
  bloqueado: { label: "Bloqueado (prévia incompleta)", tone: "danger" },
};

export const RULE_LABEL: Record<string, string> = {
  R1: "Receita",
  R2: "DAS",
  R3: "INSS",
  R4: "FGTS",
  R5: "Proventos",
  R6: "DAS anterior",
  R7: "Compras",
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

/** Ordem de exibição das alternativas; o Simples híbrido só existe a partir de 2027. */
export const REGIME_ORDER = ["SIMPLES", "SIMPLES_HIBRIDO", "PRESUMIDO", "REAL"];

/** Regimes presentes (chaves de um resultado ou lista de nomes), na ordem de exibição. */
export function orderedRegimes(present: Record<string, unknown> | string[] | null | undefined): string[] {
  const keys = Array.isArray(present) ? present : Object.keys(present ?? {});
  return REGIME_ORDER.filter((r) => keys.includes(r));
}

export const REGIME_LABEL: Record<string, string> = {
  SIMPLES: "Simples Nacional",
  PRESUMIDO: "Lucro Presumido",
  REAL: "Lucro Real",
  SIMPLES_HIBRIDO: "Simples híbrido (CBS/IBS por fora)",
};

export const TAX_LABEL: Record<string, string> = {
  irpj: "IRPJ",
  adicional_irpj: "Adicional IRPJ",
  csll: "CSLL",
  pis: "PIS",
  cofins: "Cofins",
  cbs: "CBS",
  ibs: "IBS",
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
  projecao: "Projeção do exercício (orçamento opcional)",
  conformidade: "Custo de conformidade (exibido à parte)",
  reforma_2027: "Reforma Tributária 2027 (só bloqueia a projeção de 2027)",
};

export const MONTH_ORIGIN: Record<string, { label: string; short: string }> = {
  realizado: { label: "Realizado (documentos homologados)", short: "R" },
  estimado: { label: "Estimado (receita do PGDAS-D, demais valores proporcionais)", short: "E" },
  projetado: { label: "Projetado (média dos meses completos)", short: "P" },
  orcamento: { label: "Orçamento informado", short: "O" },
};

export const ROBUSTNESS: Record<string, { label: string; tone: Tone }> = {
  robusta: { label: "Robusta", tone: "success" },
  atencao: { label: "Atenção", tone: "warning" },
  fragil: { label: "Frágil", tone: "danger" },
};

export const EVENT_LABEL: Record<string, string> = {
  created: "Elaborada",
  submitted: "Enviada para revisão",
  returned: "Devolvida",
  approved: "Aprovada",
  emission_requested: "Emissão solicitada",
  emitted: "Emitida",
  reset_by_assumption: "Voltou a rascunho (premissa alterada)",
};

/** "0.0591" → "5,91%" */
export function formatPct(value: number | string | null | undefined, places = 2): string {
  if (value === null || value === undefined || value === "") return "—";
  return `${(Number(value) * 100).toFixed(places).replace(".", ",")}%`;
}

/** "0.02" → "2,00%" quando é percentual; valores monetários em BRL; demais em texto. */
export function formatAssumption(value: unknown, type: string): string {
  if (value === null || value === undefined) return "—";
  if (type === "percent" || type === "ratio") return formatPct(String(value));
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
