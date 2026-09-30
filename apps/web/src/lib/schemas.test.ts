import { describe, expect, it } from "vitest";

import {
  activitiesSchema,
  adjustValueSchema,
  createCaseSchema,
  isValidCnpj,
  justifySchema,
  normalizeDecimal,
  percentToCents,
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

  it("exige empresa existente ou CNPJ válido (razão social opcional: vem da consulta)", () => {
    expect(createCaseSchema.safeParse({ periodStart: "2026-06", periodEnd: "2026-08" }).success).toBe(false);
    expect(createCaseSchema.safeParse({ cnpj: "11222333000181", periodStart: "2026-06", periodEnd: "2026-08" }).success).toBe(true);
    expect(createCaseSchema.safeParse({ cnpj: "11222333000100", periodStart: "2026-06", periodEnd: "2026-08" }).success).toBe(false);
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

describe("Reforma 2027 (ciclo 4)", () => {
  const uuid = "3f1d2c4b-5a6e-4f70-8a9b-0c1d2e3f4a5b";

  it("aceita o Livro de Apuração do ICMS na reclassificação, mas não o exige por competência", async () => {
    const { reclassifySchema, REQUIRED_DOC_TYPES } = await import("@/lib/schemas");
    expect(reclassifySchema.safeParse({ fileId: uuid, docType: "LIVRO_ICMS_ALTERDATA" }).success).toBe(true);
    expect(REQUIRED_DOC_TYPES).not.toContain("LIVRO_ICMS_ALTERDATA");
    expect(REQUIRED_DOC_TYPES).toHaveLength(4);
  });

  it("aceita a conta de compras de mercadorias (R7) no mapeamento do balancete", async () => {
    const { mappingSchema } = await import("@/lib/schemas");
    expect(mappingSchema.safeParse({ target: "compras_mercadorias", docType: "BALANCETE_ALTERDATA", accountCode: "13101" }).success).toBe(true);
    expect(mappingSchema.safeParse({ target: "compras_servicos", docType: "BALANCETE_ALTERDATA", accountCode: "1" }).success).toBe(false);
  });
});

describe("planejamento rápido (ciclo 5)", () => {
  const uuid = "3f1d2c4b-5a6e-4f70-8a9b-0c1d2e3f4a5b";
  const company = { companyId: uuid };

  it("exige 12 meses no período do dossiê rápido", async () => {
    const { createCaseSchema } = await import("@/lib/schemas");
    expect(createCaseSchema.safeParse({ ...company, periodStart: "2025-09", periodEnd: "2026-08", kind: "rapido" }).success).toBe(true);
    expect(createCaseSchema.safeParse({ ...company, periodStart: "2026-01", periodEnd: "2026-08", kind: "rapido" }).success).toBe(false);
    const completo = createCaseSchema.safeParse({ ...company, periodStart: "2026-06", periodEnd: "2026-08" });
    expect(completo.success && completo.data.kind).toBe("completo");
  });

  it("valida a digitação por documento", async () => {
    const { manualValuesSchema } = await import("@/lib/schemas");
    const base = { caseId: uuid, competence: "2026-05" };
    const ok = manualValuesSchema.safeParse({ ...base, docType: "FOLHA", values: { "folha.salarios": "40.000,00" } });
    expect(ok.success && ok.data.values["folha.salarios"]).toBe("40000.00");
    expect(manualValuesSchema.safeParse({ ...base, docType: "DRE", values: { "dre.resultado": "-500,00" } }).success).toBe(true);
    expect(manualValuesSchema.safeParse({ ...base, docType: "FOLHA", values: { "folha.salarios": "-1" } }).success).toBe(false);
    expect(manualValuesSchema.safeParse({ ...base, docType: "FOLHA", values: { "dre.resultado": "1" } }).success).toBe(false);
    expect(manualValuesSchema.safeParse({ ...base, docType: "FATURAMENTO", values: {} }).success).toBe(false);
  });

  it("normaliza o CNAE e exige 7 dígitos", async () => {
    const { cnaeSchema, REQUIRED_DOC_TYPES } = await import("@/lib/schemas");
    const ok = cnaeSchema.safeParse({ companyId: uuid, cnae: "4744-0/01" });
    expect(ok.success && ok.data.cnae).toBe("4744001");
    expect(cnaeSchema.safeParse({ companyId: uuid, cnae: "47440" }).success).toBe(false);
    expect(REQUIRED_DOC_TYPES).not.toContain("DECLARACAO_FATURAMENTO");
  });
});

describe("gestão do dossiê", () => {
  const uuid = "3f1d2c4b-5a6e-4f70-8a9b-0c1d2e3f4a5b";

  it("exige motivo para reabrir ou excluir", async () => {
    const { reasonSchema } = await import("@/lib/schemas");
    expect(reasonSchema.safeParse({ caseId: uuid, reason: "abc" }).success).toBe(false);
    expect(reasonSchema.safeParse({ caseId: uuid, reason: "Dossiê duplicado" }).success).toBe(true);
  });

  it("valida a edição do dossiê", async () => {
    const { updateCaseSchema } = await import("@/lib/schemas");
    expect(updateCaseSchema.safeParse({ caseId: uuid, periodStart: "2026-01", periodEnd: "2026-06", kind: "completo" }).success).toBe(true);
    expect(updateCaseSchema.safeParse({ caseId: uuid, periodStart: "2026-01", periodEnd: "2026-06", kind: "rapido" }).success).toBe(false);
    expect(updateCaseSchema.safeParse({ caseId: uuid, periodStart: "2026-08", periodEnd: "2026-06", kind: "completo" }).success).toBe(false);
  });

  it("exige razão social ao editar a empresa", async () => {
    const { companyNameSchema } = await import("@/lib/schemas");
    expect(companyNameSchema.safeParse({ companyId: uuid, legalName: " " }).success).toBe(false);
    expect(companyNameSchema.safeParse({ companyId: uuid, legalName: "Comércio Ltda" }).success).toBe(true);
  });
});

describe("atividades do planejamento rápido (ciclo 6)", () => {
  const item = (cnae: string, percentual = "") => ({ cnae, descricao: "x", percentual, origem: "receita" });
  it("converte percentuais para centésimos", () => {
    expect(percentToCents("60")).toBe(6000);
    expect(percentToCents("39,99")).toBe(3999);
    expect(percentToCents("40.5")).toBe(4050);
    expect(percentToCents("1,234")).toBeNull();
    expect(percentToCents("")).toBeNull();
  });
  it("exige soma exata de 100,00% com mais de uma atividade (AT-603)", () => {
    const ok = activitiesSchema.safeParse({ caseId: uuid, items: [item("4744-0/01", "60"), item("6201501", "40,00")] });
    expect(ok.success && ok.data.items.map((i) => [i.cnae, i.percentual])).toEqual([["4744001", "60.00"], ["6201501", "40.00"]]);
    const bad = activitiesSchema.safeParse({ caseId: uuid, items: [item("4744001", "60"), item("6201501", "39,99")] });
    expect(bad.success).toBe(false);
    expect(bad.error?.issues[0].message).toContain("exatamente 100,00%");
  });
  it("atividade única recebe 100% e lista vazia, CNAE inválido ou repetido são recusados (AT-604/605)", () => {
    const one = activitiesSchema.safeParse({ caseId: uuid, items: [item("6201501")] });
    expect(one.success && one.data.items[0].percentual).toBe("100.00");
    expect(activitiesSchema.safeParse({ caseId: uuid, items: [] }).success).toBe(false);
    expect(activitiesSchema.safeParse({ caseId: uuid, items: [item("47440")] }).success).toBe(false);
    expect(activitiesSchema.safeParse({ caseId: uuid, items: [item("4744001", "50"), item("4744-0/01", "50")] }).success).toBe(false);
  });
});
