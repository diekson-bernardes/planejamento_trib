import { z } from "zod";

export const DOC_TYPES = ["PGDAS_D", "FOLHA_ALTERDATA", "DRE_ALTERDATA", "BALANCETE_ALTERDATA"] as const;
export const MAPPING_TARGETS = [
  "vendas",
  "simples_despesa",
  "simples_a_recolher",
  "inss_a_pagar",
  "fgts_a_pagar",
  "salarios_a_pagar",
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
  })
  .refine((v) => v.companyId || (v.cnpj && isValidCnpj(v.cnpj) && v.legalName), {
    message: "Selecione uma empresa ou informe CNPJ válido e razão social",
  })
  .refine((v) => v.periodEnd >= v.periodStart, { message: "O fim do período deve ser após o início" });

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
