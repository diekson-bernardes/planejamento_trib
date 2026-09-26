# BRAINSTORM: Planejamento Rápido (ciclo 5)

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|---|---|
| Feature | PLANEJAMENTO_RAPIDO |
| Date | 2026-09-26 |
| Author | brainstorm-agent |
| Status | Handoff Ready |

## Initial Idea

**Raw Input:** "Criar uma nova branch e cria uma nova rotina para importar apenas o faturamento acumulado dos ultimos 12 meses e com base neste faturamento o aplicativo fazer o planejamento tributário do simples Nacional por dentro, por fora e lucro presumido."

Complemento do usuário: "neste planejamento rápido o usuario irá inserir o relatorio do faturamento, folha e DRE, todos em PDF, porém o usuário pode inserir manualmente estas informações caso não exista os pdf".

**Context Gathered:**
- Branch `feat/planejamento-faturamento-12m` criada a partir da `master` em `8960b4c` (ciclos 1–4 merged; ciclo 4 = PR #5).
- Ciclos anteriores entregaram: importação/conciliação (PGDAS-D, folha, DRE, balancete e Livro de ICMS da Alterdata; R1–R7), motor Simples/Presumido/Real, motor 2027 (CBS/IBS, Simples híbrido), projeção, sensibilidade, recomendação com aprovação do responsável técnico e PDF.
- Observado no código: o motor usa o PGDAS-D para anexo, divisão da receita por atividade, receitas com ICMS-ST/monofásico e RBT12; o dossiê só tem competência "completa" com PGDAS-D, folha, DRE e balancete.
- Observado na amostra `docs/Amostras/RBT12.pdf`: "Declaração de Faturamento" emitida pelo escritório contábil, 1 página com camada de texto, CNPJ 37704456000142, período 09/2025 a 08/2026, 12 linhas "mês/ano → faturamento" e "Total Geral" R$ 3.719.883,51; contém CPF e CRC dos signatários (fora do Git e dos goldens).
- Inferência: RBT12 da amostra (R$ 3.719.883,51) está acima do sublimite de R$ 3,6 milhões — ICMS fora do DAS no Simples.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|---|---|---|
| Likely Location | `services/worker/src/worker/parsers/` (parser novo), `engine/snapshot.py`, `engine/projection.py`, `engine/assumptions.py`, `pipeline.py`, `supabase/migrations/`, `apps/web/src/app/(app)/cases/` | parser da declaração, montagem do snapshot sem PGDAS, premissas novas, tipo de dossiê e telas de digitação |
| Relevant KB Domains | `kb/simples-nacional`, `kb/lucro-presumido`, `kb/reforma-tributaria`, `kb/documentos-fonte` | anexo/sublimite, presunção, CBS/IBS 2027 e layout do novo documento |
| IaC Patterns | Supabase local (migrations + pgTAP), worker Python em Docker | migration nova para tipo de dossiê, tipo de documento e valores digitados; imagem do worker sem mudança estrutural |

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|---|---|---|
| 1 | Qual problema o ciclo 5 resolve primeiro? | Rotina nova que importa o faturamento dos últimos 12 meses (mais folha e DRE, em PDF ou digitados) e compara Simples por dentro, Simples por fora e Lucro Presumido | Ciclo = "planejamento rápido" com menos documentos; mix B2B, governança de regras, cenários e transição ficam para depois |
| 2 | De onde vem o faturamento dos 12 meses? | (d) Relatório de faturamento em PDF — amostra `RBT12.pdf`; folha e DRE também em PDF; digitação manual quando não houver PDF | Parser novo da Declaração de Faturamento; reaproveitar parsers de folha e DRE da Alterdata; formulários de digitação |
| 3 | Qual exercício comparar? | (a) Só 2027 | Usa o motor de 2027 do ciclo 4 (CBS/IBS, híbrido) e as premissas de alíquota e crescimento |
| 4 | Quem usa e o que entrega? | (b) Mesmo fluxo de hoje com menos documentos: dossiê, validações, homologação, premissas, aprovação do responsável técnico e PDF | Novo tipo de dossiê com o mesmo ciclo de vida; nada de "simulação avulsa" sem homologação |
| 5 | A base de 2027? | Montar 2026 (realizados/estimados/projetados) e deslocar com o crescimento | Mantém o caminho de projeção do ciclo 4 (`build_projection` + `shift_year`) |

## Sample Data Inventory

| Type | Location | Count | Notes |
|---|---|---:|---|
| Input files | `docs/Amostras/RBT12.pdf` | 1 | Declaração de Faturamento 09/2025–08/2026; contém dados pessoais (fora do Git) |
| Input files | `docs/Amostras/2.Resumo da Folha 06/07/08.pdf`, `3.DRE 06/07/08.pdf` | 6 | Layout Alterdata já suportado |
| Output examples | `docs/Amostras/SPTE - Simulador de Planejamento Tributário Econet.pdf` | 1 | Referência de formato do relatório (já usada no ciclo 3) |
| Ground truth | N/A | 0 | Sem cálculo de referência; os totais serão aprovados pelo usuário como golden |
| Related code | `services/worker/src/worker/parsers/`, `engine/projection.py`, `engine/decision.py` | — | Parsers de folha/DRE, projeção e decisão de 2027 |

**How samples will be used:**
- `RBT12.pdf` define o layout do parser e o teste de extração (12 meses, Total Geral, CNPJ, período).
- Folha e DRE de 06–08/2026 entram como meses realizados no caso dourado do planejamento rápido.
- Golden novo aprovado pelo usuário, como nos ciclos 2–4, sem dados pessoais.

## Approaches Explored

### Approach A: Dossiê simplificado com snapshot montado a partir de faturamento, folha e DRE — Recommended

**Description:** Novo tipo de dossiê "planejamento rápido". Parser da Declaração de Faturamento e digitação manual de faturamento, folha e DRE; a homologação grava as mesmas estruturas que o motor lê (receita por mês, RBT12, folha, resultado). O que o PGDAS-D fornecia vira premissa confirmada (atividade/anexo, % com ST, % monofásico, ICMS no regime normal). Projeção de 2027, aprovação e PDF iguais aos do ciclo 4.

**Pros:**
- Motor e regras não mudam — goldens protegidos e mesma memória de cálculo, sensibilidade, aprovação e PDF.
- Simples por fora e Presumido de 2027 já calculados pelo motor do ciclo 4.

**Cons:**
- Montar o snapshot sem PGDAS (RBT12, atividades) exige cuidado.
- R1–R7 não se aplicam; o dossiê rápido precisa de validações próprias.

**Why Recommended:** o usuário pediu o mesmo fluxo de hoje com menos documentos; o trabalho novo fica na entrada, sem reescrever regra tributária.

### Approach B: Calculadora anual separada

**Description:** Cálculo próprio sobre totais anuais (receita × alíquota efetiva do anexo, presunções do Presumido, CBS/IBS por fora), fora do motor e do snapshot.

**Pros:**
- Construção mais rápida e simples de entender.

**Cons:**
- Duplica regras tributárias fora do motor versionado; risco de divergir do motor para a mesma empresa.
- Perde memória mensal e sensibilidade; contradiz o fluxo escolhido (aprovação e PDF iguais aos de hoje).

## Selected Approach

| Attribute | Value |
|---|---|
| Chosen | Approach A |
| User Confirmation | 2026-09-26, resposta "A" |
| Reasoning | Reaproveita o motor e o fluxo de decisão do ciclo 4; mudança concentrada na entrada de dados |

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|---|---|---|
| 1 | Novo tipo de dossiê "planejamento rápido" com o mesmo ciclo de vida do completo | Usuário quer homologação, aprovação do RT e PDF | Simulação avulsa sem homologação (opção a/c da pergunta 4) |
| 2 | Parser da Declaração de Faturamento (layout `RBT12.pdf`) + digitação manual | PDF quando existir; digitação quando não | Importar só o PGDAS-D do último mês; entrada por XLSX |
| 3 | Folha e DRE pelos parsers Alterdata, de 1 a 12 meses, ou digitadas | Reaproveita parsers existentes; flexibilidade de meses | Exigir 12 meses de folha e DRE |
| 4 | Exercício comparado: só 2027 | Simples por fora só existe a partir de 2027 | 2026 + 2027 lado a lado; recorte dos próximos 12 meses |
| 5 | Alternativas: Simples por dentro, Simples por fora (híbrido) e Lucro Presumido | Pedido do usuário | Incluir Lucro Real |
| 6 | Base de 2027 = 2026 montado (realizados/estimados/projetados) deslocado com o crescimento | Mesmo cálculo do ciclo 4 | Crescimento aplicado direto sobre os 12 meses da declaração |
| 7 | Digitação só para mês/documento sem PDF; mudança em valor extraído = ajuste justificado | Rastreabilidade | Sobrescrever valor extraído livremente |
| 8 | Anexo/atividade, % ST, % monofásico e ICMS no regime normal viram premissas confirmadas | Sem PGDAS-D essas informações não existem nos documentos | Inferir do CNAE sem confirmação |

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed/Deferred | Can Add Later? |
|---|---|---|
| Lucro Real no dossiê rápido | Não pedido; sem balancete o Real ficaria frágil | Yes |
| Outros layouts de declaração de faturamento | Só há uma amostra | Yes |
| Folha e DRE de outros ERPs | Só há amostras Alterdata | Yes |
| Entrada por XLSX/CSV | PDF + digitação cobrem o pedido | Yes |
| Comparativo de 2026 | Usuário escolheu só 2027 | Yes |
| Mix de vendas B2B × consumidor final | Adiado desde o ciclo 4; fora do pedido | Yes |
| Conciliações R1–R7 no dossiê rápido | Dependem de PGDAS-D e balancete | N/A |

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---|---|---|---|
| Checkpoint 1 — conceito, componentes e cortes | Yes | "sim, Real fica de fora e folha/DRE de 1 a 12 meses" | No |
| Checkpoint 2 — fluxo, falhas, dependências e base de 2027 | Yes | "sim, montar 2026 e deslocar com o crescimento" | No |

## Suggested Requirements for /define

### Problem Statement (Draft)

O escritório precisa comparar, para 2027, o Simples Nacional por dentro, o Simples por fora (híbrido) e o Lucro Presumido de uma empresa a partir apenas do faturamento dos últimos 12 meses, da folha e da DRE (em PDF ou digitados), com o mesmo rigor de homologação, aprovação e relatório do dossiê completo.

### Target Users (Draft)

| User | Pain Point |
|---|---|
| Analista do escritório | Não consegue planejar quem não tem o pacote completo (PGDAS-D, balancete, conciliações) |
| Responsável técnico (contador) | Precisa aprovar e assinar um comparativo rastreável mesmo com entrada simplificada |

### Success Criteria (Draft)

- [ ] A Declaração de Faturamento da amostra é extraída com os 12 meses e a soma igual ao Total Geral (R$ 3.719.883,51).
- [ ] Faturamento, folha e DRE podem ser digitados quando não houver PDF, com registro de quem digitou e quando.
- [ ] O dossiê rápido homologado projeta 2027 e compara as três alternativas com memória de cálculo, sensibilidade e recomendação.
- [ ] Golden do planejamento rápido aprovado pelo usuário; goldens anteriores inalterados.
- [ ] Tempo da projeção: TBD no Define (referência dos ciclos 3–4: ≤ 60 s).

### Constraints Identified

- Motor e regras tributárias não mudam; regras de 2027 seguem `verificado: false`.
- Amostras com dados pessoais ficam fora do Git; goldens sem PII.
- Um único layout de declaração (o da amostra); folha e DRE só no layout Alterdata.
- Premissas de 2027 sem padrão (alíquotas de CBS/IBS) continuam bloqueando a recomendação enquanto pendentes.

### Out of Scope (Confirmed)

- Lucro Real no dossiê rápido.
- Comparativo de 2026.
- Outros layouts de faturamento, folha e DRE; entrada por XLSX.
- Mix de vendas B2B, transição 2029–2033, Imposto Seletivo, ZFM, NCM, split payment.
- Conciliações R1–R7 no dossiê rápido.

## Session Summary

| Metric | Value |
|---|---:|
| Questions Asked | 6 |
| Approaches Explored | 2 |
| Features Removed (YAGNI) | 7 |
| Validations Completed | 2 |

## Next Step

Execute o **SDD Define by RDD**.
