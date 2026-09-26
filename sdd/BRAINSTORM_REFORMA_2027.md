# BRAINSTORM: Reforma Tributária 2027 (ciclo 4 do Planejamento Tributário)

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|---|---|
| Feature | REFORMA_2027 |
| Date | 2026-09-25 |
| Author | brainstorm-agent |
| Status | Handoff Ready |

## Initial Idea

**Raw Input:** "Use a skill sdd-brainstorm para o ciclo 4" — candidatos (roadmap do PRD, fase 5, e itens adiados nos ciclos 1–3): regras de 2027 com a transição da Reforma Tributária (CBS/IBS) e projeção de 2027; novos layouts/sistemas (OCR, XLSX, Domínio, Questor, Netsped); decisão mais rica (sazonalidade, cenários, RF-14/RF-15, assinatura eletrônica).

**Context Gathered:**
- KB `kb/reforma-tributaria` (EC 132/2023 e LC 214/2025 via fontes secundárias, LC 214 não conferida na fonte primária): em 2027 PIS/Cofins extintos, CBS plena não cumulativa com crédito financeiro amplo, IBS 0,1%, IPI zero (exceto ZFM), Imposto Seletivo inicia; ICMS/ISS integrais até 2028 e reduzidos em 2029–2032.
- KB: a diferença cumulativo × não cumulativo deixa de existir para consumo em 2027 — Presumido × Real passa a depender de IRPJ/CSLL.
- KB: a partir de 2027 o optante do Simples escolhe IBS/CBS "por dentro" do DAS ou regime regular ("híbrido"), com opção semestral e efeito no crédito do cliente B2B.
- KB não contém a alíquota de referência da CBS de 2027 (depende de resolução do Senado).
- Fontes da KB indicam que a primeira janela de opção pelo híbrido (1º semestre de 2027) vence em 30/09/2026 — prazo não atendível por este ciclo.
- PRD §8.5: módulos CBS/IBS parametrizados por exercício; informar se o cálculo é histórico, corrente ou projetado; não presumir neutralidade do Simples para clientes B2B.
- Observado no projeto: motor do ciclo 2 com regras versionadas por exercício (`services/worker/rules/2026`, versão 2026.1.0); projeção, sensibilidade, recomendação, fluxo de aprovação e PDF do ciclo 3 na `master` (`6f71835`).
- Amostra nova: `docs/Amostras/Livro Apuração ICMS 08.pdf` — Registro de Apuração do ICMS (Alterdata), 2 páginas, 08/2026, CNPJ 37.704.456/0001-42. Entradas por CFOP totalizando R$ 158.503,98; compras para comercialização (CFOP 1102, 2102, 1403, 2403) = R$ 149.985,71, igual aos débitos da conta 13101 do balancete de 08/2026; frete (2353) R$ 6.121,50; devoluções de venda (1202, 1411). Saídas R$ 205.577,54 contra receita do PGDAS-D de R$ 203.180,77 (diferença R$ 2.396,77). ICMS zerado (optante do Simples).

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|---|---|---|
| Likely Location | `services/worker/rules/2027/` (nova versão), `services/worker/src/worker/engine/` (cálculo por exercício, projeção, sensibilidade, recomendação), `services/worker/src/worker/parsers/` e `classify.py` (novo documento), `supabase/migrations/` (tipo de documento, conciliação R7, premissas), `apps/web/src/app/(app)/cases/[id]/planning/` | Reuso dos ciclos 1–3; motor protegido pelos goldens |
| Relevant KB Domains | `kb/reforma-tributaria`, `kb/simples-nacional`, `kb/lucro-presumido`, `kb/lucro-real`, `kb/documentos-fonte` | Calendário, Simples na Reforma, opção pelo regime regular, layouts Alterdata |
| IaC Patterns | N/A (Supabase local, worker em Docker, Next.js) | Sem infraestrutura nova |

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|---|---|---|
| 1 | Qual frente entra no ciclo 4? | (a) Reforma 2027: regras 2027 versionadas, projeção 2027 dos regimes e Simples por dentro × híbrido | Ciclo focado na virada federal de 2027 |
| 2 | Como obter a alíquota de CBS/IBS de 2027? | (b) Premissa do escritório por dossiê, sem valor padrão nas regras | Sem premissa confirmada o 2027 fica bloqueado; regras guardam só a estrutura |
| 3 | Qual decisão apoiar? | (a) As duas juntas: Simples por dentro, Simples híbrido, Presumido e Real | Quatro alternativas no comparativo e na recomendação |
| 4 | De onde vêm os números de 2027? | (a) Projeção 2026 do ciclo 3 deslocada para 2027 com crescimento da receita como premissa (padrão 0%) | Reuso integral do ciclo 3; RBT12 e limites coerentes |
| 5 | Amostras e referências? | (a) e (b) — mix de vendas e compras | Motivou a pergunta 6 |
| 6 | De onde vêm os PDFs de mix e compras? | (c) Só o Livro de Apuração do ICMS (entradas) foi anexado; mix de vendas fica para o próximo ciclo. Compras: importar PDF ou informar manualmente | Novo documento importado (Livro de Apuração) + premissa manual; efeito B2B adiado |

## Sample Data Inventory

| Type | Location | Count | Notes |
|---|---|---:|---|
| Input files | `docs/Amostras/Livro Apuração ICMS 08.pdf` | 1 | Registro de Apuração do ICMS Alterdata, 08/2026; fora do Git |
| Input files | `docs/Amostras/` (PGDAS-D, folha, DRE, balancete 06–08/2026) | 12 | Base da Projeção 2026 que origina 2027 |
| Output examples | `docs/Amostras/SPTE - Simulador de Planejamento Tributário Econet.pdf` | 1 | Formato do comparativo (já usado no ciclo 3) |
| Ground truth | `services/worker/tests/golden/motor_202608.json`, `motor_202606_08.json`, `decisao_2026.json` | 3 | Regressão obrigatória; não há ground truth de 2027 |
| Related code | `services/worker/src/worker/engine/`, `services/worker/src/worker/parsers/` | — | Motor, projeção e parsers dos ciclos 1–3 |

**How samples will be used:**
- O Livro de Apuração de 08/2026 define o layout do parser (entradas e saídas por CFOP, subtotais e totais) e a conciliação R7 (compras para comercialização = conta 13101 do balancete; bate ao centavo na amostra).
- A base de créditos de CBS/IBS é sugerida pelo livro (compras + frete − devoluções de venda) e, sem livro, pela conta 13101.
- Os 12 documentos de 06–08/2026 geram a Projeção 2026, deslocada para 2027.

## Approaches Explored

### Approach A: Regras 2027 como nova versão e motor por exercício — Recommended

**Description:** Criar `services/worker/rules/2027/` (estrutura de CBS/IBS com débito sobre receita e crédito financeiro sobre compras, IPI zero, repartição do DAS de 2027 com CBS/IBS no lugar de PIS/Cofins; alíquotas vindas de premissa). O motor passa a calcular por exercício (2026 inalterado). O Simples é calculado por dentro e híbrido (DAS sem CBS/IBS + CBS/IBS no regime regular), totalizando quatro alternativas. 2027 = Projeção 2026 deslocada + crescimento, com a sensibilidade, a recomendação, o fluxo e o PDF do ciclo 3. O Livro de Apuração do ICMS vira documento importado (parser, validações, conciliação R7) que sugere a base de créditos.

**Pros:**
- Fiel à lei e versionado; memória linha a linha e reprodutibilidade dos ciclos 2 e 3.
- Reuso da projeção, sensibilidade, recomendação, fluxo e PDF.

**Cons:**
- Mexe no motor (protegido pelos goldens).
- Depende da repartição do DAS de 2027 (LC 214), não conferida na fonte primária.

**Why Recommended:** única abordagem que mantém rastreabilidade e reprodutibilidade e trata 2027 como exercício de verdade, usando o versionamento de regras pensado para essa virada.

### Approach B: Ajuste de 2027 sobre o resultado de 2026

**Description:** Retirar PIS/Cofins/IPI da Projeção 2026 pronta e somar CBS/IBS por fórmula; no Simples, trocar a parcela de PIS/Cofins do DAS pela de CBS.

**Pros:**
- Não toca o motor; rápido.

**Cons:**
- Memória vira remendo; sensibilidade não enxerga a CBS; recomendação de 2027 menos confiável.

### Approach C: Calculadora de consumo separada

**Description:** Manter IRPJ/CSLL/folha de 2026 e calcular só os tributos sobre consumo de 2027 em módulo próprio.

**Pros:**
- Escopo menor que A.

**Cons:**
- Dois motores que tendem a divergir; limites e faixas do Simples em 2027 não reaplicados.

## Selected Approach

| Attribute | Value |
|---|---|
| Chosen | Approach A |
| User Confirmation | 2026-09-25, "sim, opção A" |
| Reasoning | Mantém rastreabilidade, reprodutibilidade e versionamento por exercício dos ciclos anteriores |

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|---|---|---|
| 1 | Ciclo 4 = Reforma 2027 | Opção de regime para 2027 é decidida agora; ciclo 3 só compara 2026 | Novos documentos; decisão mais rica |
| 2 | Alíquotas de CBS/IBS de 2027 como premissa do escritório, sem padrão nas regras | Alíquota de referência não definida na KB | Regras com melhor fonte; faixa de cenários |
| 3 | Quatro alternativas: Simples por dentro, Simples híbrido, Presumido, Real | Apoiar a escolha do regime e a opção do Simples juntas | Só regime do ano; só por dentro × híbrido |
| 4 | 2027 = Projeção 2026 deslocada + crescimento (premissa, padrão 0%) | Reuso do ciclo 3; sem documentos de 2027 | Últimos 12 meses; orçamento mensal obrigatório |
| 5 | Compras: importar o Livro de Apuração do ICMS (PDF) ou informar manualmente | Pedido do usuário; amostra disponível | Somente premissa manual |
| 6 | Livro de Apuração é documento opcional (não altera "competência completa") | Goldens dos ciclos 2 e 3 não mudam | Exigir o livro para competência completa |
| 7 | Conciliação R7: compras para comercialização (1102, 2102, 1403, 2403) = conta 13101; saídas × PGDAS-D apenas informativa | Bate ao centavo na amostra; diferença das saídas sem regra conhecida | Conciliar saídas com bloqueio |
| 8 | Regras 2027 com `verificado: false` até a revisão contábil | LC 214 não conferida na fonte primária | Marcar como verificadas |
| 9 | Sensibilidade ganha a variável "alíquota da CBS" | Alíquota incerta é a maior fonte de variação em 2027 | Sensibilidade só com as 5 variáveis do ciclo 3 |

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed/Deferred | Can Add Later? |
|---|---|---|
| Mix de vendas e efeito no crédito do cliente B2B | Adiado pelo usuário para o próximo ciclo | Yes (próximo ciclo) |
| Transição 2029–2033 (ICMS/ISS reduzidos + IBS crescente) | Ciclo cobre só 2027 | Yes (próximo ciclo) |
| Imposto Seletivo | Alcança produtos específicos; amostra é comércio de máquinas e parafusos | Yes (próximo ciclo) |
| Exceção da Zona Franca de Manaus no IPI | Fora do perfil da amostra | Yes (próximo ciclo) |
| Alíquotas reduzidas por produto/NCM | Alíquota única por dossiê basta para o MVP | Yes (próximo ciclo) |
| Split payment | Não altera o custo tributário anual comparado | Yes (próximo ciclo) |
| Opção semestral do híbrido | 2027 calculado com a mesma opção nos dois semestres | Yes (próximo ciclo) |

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---|---|---|---|
| Checkpoint 1: YAGNI, conceito (2027 a partir da Projeção 2026, quatro alternativas), limites e componentes | Yes | "sim, no entanto deixe para um próximo ciclo (proposta de corte) sugeridas acima" | Yes — itens cortados registrados como próximo ciclo |
| Checkpoint 2: fluxo (importação do livro, R7, premissas, projeção 2027), falhas, dependências e comportamento esperado | Yes | "sim" | No |

## Suggested Requirements for /define

### Problem Statement (Draft)

O escritório só compara os regimes em 2026 e não consegue recomendar o regime (nem a opção do Simples por dentro × híbrido) para 2027, ano em que PIS/Cofins dão lugar à CBS não cumulativa com crédito financeiro sobre as compras.

### Target Users (Draft)

| User | Pain Point |
|---|---|
| Analista do escritório | Precisa projetar 2027 com CBS/IBS e comparar as quatro alternativas sem planilha paralela |
| Responsável técnico | Precisa aprovar a recomendação de 2027 com premissas de alíquota e ressalvas visíveis |
| Cliente do escritório | Decide o regime e a opção do Simples para 2027 |

### Success Criteria (Draft)

- [ ] Projeção 2026 e goldens dos ciclos 2 e 3 continuam idênticos após a introdução do cálculo por exercício.
- [ ] Livro de Apuração de 08/2026 importado com as entradas por CFOP e R7 conciliada ao centavo com a conta 13101.
- [ ] Projeção 2027 com quatro alternativas, memória linha a linha e reprodutível.
- [ ] Sem alíquota de CBS/IBS confirmada, a recomendação de 2027 fica bloqueada.
- [ ] Tempo da projeção 2027: TBD (ciclo 3 usou ≤ 60 s).
- [ ] Golden de 2027 aprovado pelo usuário após informar as alíquotas.

### Constraints Identified

- Só o exercício de 2027; alíquotas por premissa do escritório.
- Regras 2027 com `verificado: false` (LC 214 não conferida); repartição do DAS de 2027 depende de pesquisa complementar na KB.
- Livro de Apuração: layout Alterdata de uma única amostra (08/2026); documento opcional.
- Janela de opção do híbrido para o 1º semestre de 2027 (30/09/2026, segundo as fontes) não é atendida por este ciclo.
- Isolamento por escritório, amostras fora do Git e logs sem dados sensíveis, como nos ciclos anteriores.

### Out of Scope (Confirmed)

- Mix de vendas e efeito no crédito do cliente B2B (próximo ciclo).
- Transição 2029–2033, Imposto Seletivo, exceção ZFM, alíquotas por NCM, split payment, opção semestral do híbrido (próximo ciclo).
- Novos layouts/sistemas (OCR, XLSX, Domínio, Questor, Netsped) e decisão mais rica (sazonalidade, cenários, RF-14/RF-15, assinatura eletrônica).

## Session Summary

| Metric | Value |
|---|---:|
| Questions Asked | 6 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 7 |
| Validations Completed | 2 |

## Next Step

Execute o **SDD Define by RDD**.
