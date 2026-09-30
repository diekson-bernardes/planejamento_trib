import { z } from "zod";

export const DOC_TYPES = [
  "PGDAS_D",
  "FOLHA_ALTERDATA",
  "DRE_ALTERDATA",
  "BALANCETE_ALTERDATA",
  "LIVRO_ICMS_ALTERDATA",
  "DECLARACAO_FATURAMENTO",
] as const;
/** Documentos exigidos por competência no dossiê completo; Livro de Apuração (R7) e Declaração de Faturamento
 *  (planejamento rápido) ficam fora. */
export const REQUIRED_DOC_TYPES = DOC_TYPES.filter((t) => t !== "LIVRO_ICMS_ALTERDATA" && t !== "DECLARACAO_FATURAMENTO");
export const CASE_KINDS = ["completo", "rapido"] as const;
/** Campos da digitação manual do planejamento rápido, por documento (mesmas chaves da RPC enter_manual_values). */
export const MANUAL_FIELDS = {
  FATURAMENTO: ["faturamento.mes"],
  FOLHA: ["folha.salarios", "folha.pro_labore", "folha.autonomos"],
  DRE: ["dre.receita_bruta", "dre.outras_receitas", "dre.resultado"],
} as const;
export type ManualDoc = keyof typeof MANUAL_FIELDS;
export const MAPPING_TARGETS = [
  "vendas",
  "simples_despesa",
  "simples_a_recolher",
  "inss_a_pagar",
  "fgts_a_pagar",
  "salarios_a_pagar",
  "compras_mercadorias",
] as const;
export const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;

export function onlyDigits(value: string): string {
  return value.replace(/\D/g, "");
}

export function isValidCnpj(value: string): boolean {
  const cnpj = onlyDigits(value);
  if (cnpj.length !== 14 || /^(\d)\1+$/.test(cnpj)) return false;
  const nums = cnpj.split("").map(Number);
  const weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  for (const size of [12, 13]) {
    const w = weights.slice(weights.length - size);
    const total = w.reduce((acc, weight, i) => acc + weight * nums[i], 0);
    const check = total % 11 < 2 ? 0 : 11 - (total % 11);
    if (nums[size] !== check) return false;
  }
  return true;
}

const month = z.string().regex(/^\d{4}-(0[1-9]|1[0-2])$/, "Competência inválida (use AAAA-MM)");
const reason = z.string().trim().min(5, "Informe um motivo com ao menos 5 caracteres");

export const createCaseSchema = z
  .object({
    companyId: z.uuid().optional(),
    cnpj: z.string().optional(),
    legalName: z.string().trim().optional(),
    periodStart: month,
    periodEnd: month,
    kind: z.enum(CASE_KINDS).default("completo"),
  })
  // razão social opcional: sem ela, a empresa é cadastrada pelo CNPJ e a razão social vem da consulta à Receita
  .refine((v) => v.companyId || (v.cnpj && isValidCnpj(v.cnpj)), {
    message: "Selecione uma empresa ou informe um CNPJ válido",
  })
  .refine((v) => v.periodEnd >= v.periodStart, { message: "O fim do período deve ser após o início" })
  .refine((v) => v.kind !== "rapido" || monthsSpan(v.periodStart, v.periodEnd) === 12, {
    message: "O planejamento rápido usa os últimos 12 meses (ex.: 09/2025 a 08/2026)",
  });

function monthsSpan(start: string, end: string): number {
  const [sy, sm] = start.split("-").map(Number);
  const [ey, em] = end.split("-").map(Number);
  return (ey - sy) * 12 + (em - sm) + 1;
}

/** "1.234,56", "1234.56" ou "-500,00" → número (o resultado da DRE pode ser negativo; demais campos não). */
const money = z
  .string()
  .trim()
  .transform((v) => normalizeDecimal(v))
  .pipe(z.string().regex(/^-?\d+(\.\d{1,2})?$/, "Valor inválido"));

export const manualValuesSchema = z
  .object({
    caseId: z.uuid(),
    docType: z.enum(["FATURAMENTO", "FOLHA", "DRE"]),
    competence: month,
    values: z.record(z.string(), money),
  })
  .refine((v) => Object.keys(v.values).length > 0, { message: "Informe ao menos um valor" })
  .refine((v) => Object.keys(v.values).every((k) => (MANUAL_FIELDS[v.docType] as readonly string[]).includes(k)), {
    message: "Campo inválido para o documento",
  })
  .refine((v) => Object.entries(v.values).every(([k, x]) => k === "dre.resultado" || !x.startsWith("-")), {
    message: "Só o resultado da DRE pode ser negativo",
  });

const reasonText = z.string().trim().min(5, "Informe o motivo (mín. 5 caracteres)").max(500);

export const reasonSchema = z.object({ caseId: z.uuid(), reason: reasonText });

export const updateCaseSchema = z
  .object({ caseId: z.uuid(), periodStart: month, periodEnd: month, kind: z.enum(CASE_KINDS) })
  .refine((v) => v.periodEnd >= v.periodStart, { message: "O fim do período deve ser após o início" })
  .refine((v) => v.kind !== "rapido" || monthsSpan(v.periodStart, v.periodEnd) === 12, {
    message: "O planejamento rápido usa os últimos 12 meses (ex.: 09/2025 a 08/2026)",
  });

export const companyNameSchema = z.object({
  companyId: z.uuid(),
  legalName: z.string().trim().min(2, "Informe a razão social").max(200),
});

export const cnaeSchema = z.object({
  companyId: z.uuid(),
  cnae: z
    .string()
    .transform((v) => onlyDigits(v))
    .pipe(z.string().length(7, "CNAE deve ter 7 dígitos (ex.: 4744-0/01)")),
  description: z.string().trim().max(200).optional(),
});

/** Percentual digitado ("60", "39,5", "40.00") → centésimos inteiros (6000), ou null se inválido. */
export function percentToCents(value: string | undefined): number | null {
  const v = normalizeDecimal(value ?? "");
  if (!/^\d{1,3}(\.\d{1,2})?$/.test(v)) return null;
  const [int, dec = ""] = v.split(".");
  return Number(int) * 100 + Number(dec.padEnd(2, "0"));
}

const activityItemSchema = z.object({
  cnae: z
    .string()
    .transform((v) => onlyDigits(v))
    .pipe(z.string().length(7, "CNAE deve ter 7 dígitos (ex.: 6201-5/01)")),
  descricao: z.string().trim().max(300, "Descrição do CNAE muito longa").default(""),
  percentual: z.string().default(""),
  origem: z.enum(["receita", "manual"]).default("manual"),
});

/** Atividades do planejamento rápido: ao menos uma; com mais de uma, percentuais > 0 somando exatamente 100,00%. */
export const activitiesSchema = z
  .object({ caseId: z.uuid(), items: z.array(activityItemSchema).min(1, "Marque ao menos uma atividade") })
  .refine((v) => new Set(v.items.map((i) => i.cnae)).size === v.items.length, { message: "CNAE repetido na lista de atividades" })
  .refine((v) => v.items.length === 1 || v.items.every((i) => (percentToCents(i.percentual) ?? 0) > 0), {
    message: "Informe o percentual de cada atividade (maior que zero, até 2 casas)",
  })
  .refine((v) => v.items.length === 1 || v.items.reduce((acc, i) => acc + (percentToCents(i.percentual) ?? 0), 0) === 10000, {
    message: "A soma dos percentuais precisa ser exatamente 100,00%",
  })
  .transform((v) => ({
    caseId: v.caseId,
    items: v.items.map((i) => ({
      cnae: i.cnae,
      descricao: i.descricao,
      origem: i.origem,
      percentual: v.items.length === 1 ? "100.00" : ((percentToCents(i.percentual) ?? 0) / 100).toFixed(2),
    })),
  }));

export const registerUploadSchema = z.object({
  caseId: z.uuid(),
  fileId: z.uuid(),
  storagePath: z.string().min(10),
  sha256: z.string().regex(/^[0-9a-f]{64}$/, "Hash inválido"),
  originalName: z.string().min(1).max(255),
  sizeBytes: z.number().int().positive().max(MAX_UPLOAD_BYTES, "Arquivo acima do limite de 20 MB"),
});

export const adjustValueSchema = z.object({
  valueId: z.uuid(),
  newValue: z.string().trim().regex(/^-?\d{1,16}([.,]\d{1,2})?$/, "Valor inválido"),
  reason,
});

export const justifySchema = z.object({
  reconciliationId: z.uuid(),
  justification: reason,
});

export const reclassifySchema = z.object({
  fileId: z.uuid(),
  docType: z.enum(DOC_TYPES),
});

export const toleranceSchema = z.object({
  tolerance: z.number().min(0, "A tolerância não pode ser negativa").max(1_000_000),
});

export const inviteSchema = z.object({
  email: z.email("E-mail inválido"),
});

export const mappingSchema = z.object({
  target: z.enum(MAPPING_TARGETS),
  docType: z.enum(["DRE_ALTERDATA", "BALANCETE_ALTERDATA"]),
  accountCode: z.string().trim().min(1, "Informe o código da conta").max(40),
});

/** Primeira mensagem de erro legível de uma validação zod. */
export function firstIssue(error: z.ZodError): string {
  return error.issues[0]?.message ?? "Dados inválidos";
}

/** "1.234,56" ou "1234.56" → "1234.56" */
export function normalizeDecimal(value: string): string {
  const v = value.trim();
  return v.includes(",") ? v.replace(/\./g, "").replace(",", ".") : v;
}

/** Confirmação de premissa: valor JSON (texto, número como texto, booleano, lista ou perfil) + justificativa. */
export const confirmAssumptionSchema = z
  .object({
    assumptionId: z.uuid(),
    value: z.union([z.string().trim().min(1), z.boolean(), z.array(z.string()), z.record(z.string(), z.unknown())]),
    suggested: z.unknown().optional(),
    justification: z.string().trim().optional(),
  })
  .refine(
    (v) => JSON.stringify(v.value) === JSON.stringify(v.suggested) || (v.justification ?? "").length >= 5,
    { message: "Justifique (mín. 5 caracteres) ao alterar o valor sugerido" },
  );

// ------------------------------------------------------------------ ciclo 3: decisão
/** Devolução ao elaborador: comentário obrigatório (o banco revalida). */
export const returnRecommendationSchema = z.object({
  recommendationId: z.uuid(),
  comment: z.string().trim().min(5, "Comentário obrigatório (mín. 5 caracteres) ao devolver"),
});

/** Marcação de responsável técnico pelo admin: nome profissional e CRC obrigatórios quando marcado. */
export const technicalResponsibleSchema = z
  .object({
    userId: z.uuid(),
    flag: z.boolean(),
    name: z.string().trim().optional(),
    crc: z.string().trim().optional(),
  })
  .refine((v) => !v.flag || ((v.name ?? "").length >= 3 && (v.crc ?? "").length >= 4), {
    message: "Informe nome profissional (mín. 3) e CRC (mín. 4) do responsável técnico",
  });

/** Limiar de "resultado inconclusivo": fração do custo do regime vencedor, entre 0 e 1 (exclusive). */
/** Exercícios com regras parametrizadas no worker (2027: Reforma — CBS/IBS). */
export const PROJECTION_YEARS = [2026, 2027] as const;

export const projectionYearSchema = z.object({
  year: z.coerce
    .number()
    .int()
    .refine((y) => (PROJECTION_YEARS as readonly number[]).includes(y), "Exercício sem regras parametrizadas"),
});

export const thresholdSchema = z.object({
  threshold: z.number().gt(0, "O limiar deve ser maior que 0").lt(1, "O limiar deve ser menor que 1 (100%)"),
});
