import { describe, expect, it } from "vitest";

import {
  adjustValueSchema,
  createCaseSchema,
  isValidCnpj,
  justifySchema,
  normalizeDecimal,
  registerUploadSchema,
  toleranceSchema,
} from "@/lib/schemas";

const uuid = "a2222222-2222-4222-8222-222222222222";

describe("ajuste de valor (AT-017)", () => {
  it("exige motivo com ao menos 5 caracteres", () => {
    expect(adjustValueSchema.safeParse({ valueId: uuid, newValue: "10,00", reason: "ok" }).success).toBe(false);
    expect(adjustValueSchema.safeParse({ valueId: uuid, newValue: "10,00", reason: "  ok   " }).success).toBe(false);
    expect(adjustValueSchema.safeParse({ valueId: uuid, newValue: "10,00", reason: "Correção pela DRE" }).success).toBe(true);
  });

  it("rejeita valor não numérico", () => {
    expect(adjustValueSchema.safeParse({ valueId: uuid, newValue: "dez", reason: "Correção pela DRE" }).success).toBe(false);
  });

  it("normaliza decimal brasileiro", () => {
    expect(normalizeDecimal("1.234,56")).toBe("1234.56");
    expect(normalizeDecimal("1234.56")).toBe("1234.56");
  });
});

describe("justificativa de divergência (AT-009)", () => {
  it("exige texto mínimo", () => {
    expect(justifySchema.safeParse({ reconciliationId: uuid, justification: "x" }).success).toBe(false);
    expect(justifySchema.safeParse({ reconciliationId: uuid, justification: "Devoluções de setembro" }).success).toBe(true);
  });
});

describe("CNPJ e dossiê", () => {
  it("valida dígitos verificadores", () => {
    expect(isValidCnpj("11.222.333/0001-81")).toBe(true);
    expect(isValidCnpj("11222333000180")).toBe(false);
    expect(isValidCnpj("11111111111111")).toBe(false);
  });

  it("exige empresa existente ou CNPJ válido com razão social", () => {
    expect(createCaseSchema.safeParse({ periodStart: "2026-06", periodEnd: "2026-08" }).success).toBe(false);
    expect(
      createCaseSchema.safeParse({ cnpj: "11222333000181", legalName: "Comércio", periodStart: "2026-06", periodEnd: "2026-08" }).success,
    ).toBe(true);
    expect(createCaseSchema.safeParse({ companyId: uuid, periodStart: "2026-06", periodEnd: "2026-08" }).success).toBe(true);
  });

  it("rejeita período invertido", () => {
    expect(createCaseSchema.safeParse({ companyId: uuid, periodStart: "2026-08", periodEnd: "2026-06" }).success).toBe(false);
  });
});

describe("upload e tolerância", () => {
  it("limita o tamanho a 20 MB e exige hash hexadecimal", () => {
    const base = { caseId: uuid, fileId: uuid, storagePath: `${uuid}/${uuid}/${uuid}.pdf`, originalName: "a.pdf" };
    expect(registerUploadSchema.safeParse({ ...base, sha256: "a".repeat(64), sizeBytes: 1024 }).success).toBe(true);
    expect(registerUploadSchema.safeParse({ ...base, sha256: "a".repeat(64), sizeBytes: 21 * 1024 * 1024 }).success).toBe(false);
    expect(registerUploadSchema.safeParse({ ...base, sha256: "xyz", sizeBytes: 1024 }).success).toBe(false);
  });

  it("não aceita tolerância negativa", () => {
    expect(toleranceSchema.safeParse({ tolerance: -1 }).success).toBe(false);
    expect(toleranceSchema.safeParse({ tolerance: 0 }).success).toBe(true);
    expect(toleranceSchema.safeParse({ tolerance: 1 }).success).toBe(true);
  });
});

describe("confirmação de premissa (AT-104)", () => {
  it("dispensa justificativa quando confirma o valor sugerido", async () => {
    const { confirmAssumptionSchema } = await import("@/lib/schemas");
    expect(confirmAssumptionSchema.safeParse({ assumptionId: uuid, value: "0.02", suggested: "0.02" }).success).toBe(true);
    expect(
      confirmAssumptionSchema.safeParse({ assumptionId: uuid, value: ["icms"], suggested: ["icms"] }).success,
    ).toBe(true);
  });

  it("exige justificativa ao alterar o valor sugerido", async () => {
    const { confirmAssumptionSchema } = await import("@/lib/schemas");
    expect(confirmAssumptionSchema.safeParse({ assumptionId: uuid, value: "0.03", suggested: "0.02" }).success).toBe(false);
    expect(
      confirmAssumptionSchema.safeParse({ assumptionId: uuid, value: "0.03", suggested: "0.02", justification: "CNAE grave" }).success,
    ).toBe(true);
  });

  it("aceita perfil de atividade e declaração", async () => {
    const { confirmAssumptionSchema } = await import("@/lib/schemas");
    const profile = { anexo: "III", presumido: "servicos_gerais", cumulativo_no_real: false, fator_r: true };
    expect(confirmAssumptionSchema.safeParse({ assumptionId: uuid, value: profile, suggested: null, justification: "Serviço de engenharia" }).success).toBe(true);
    expect(confirmAssumptionSchema.safeParse({ assumptionId: uuid, value: "nao", suggested: "nao_informado" }).success).toBe(false);
  });
});

describe("decisão tributária (ciclo 3)", () => {
  it("exige comentário ao devolver a recomendação (AT-217)", async () => {
    const { returnRecommendationSchema } = await import("@/lib/schemas");
    expect(returnRecommendationSchema.safeParse({ recommendationId: uuid, comment: " ok " }).success).toBe(false);
    expect(returnRecommendationSchema.safeParse({ recommendationId: uuid, comment: "Revisar margem" }).success).toBe(true);
  });

  it("exige nome e CRC ao marcar responsável técnico (AT-214)", async () => {
    const { technicalResponsibleSchema } = await import("@/lib/schemas");
    expect(technicalResponsibleSchema.safeParse({ userId: uuid, flag: true, name: "Maria", crc: "" }).success).toBe(false);
    expect(technicalResponsibleSchema.safeParse({ userId: uuid, flag: true, name: "Maria", crc: "SP-123456/O-7" }).success).toBe(true);
    expect(technicalResponsibleSchema.safeParse({ userId: uuid, flag: false }).success).toBe(true);
  });

  it("aceita limiar só entre 0 e 1 exclusive", async () => {
    const { thresholdSchema } = await import("@/lib/schemas");
    expect(thresholdSchema.safeParse({ threshold: 0 }).success).toBe(false);
    expect(thresholdSchema.safeParse({ threshold: 1 }).success).toBe(false);
    expect(thresholdSchema.safeParse({ threshold: 0.05 }).success).toBe(true);
  });
});
