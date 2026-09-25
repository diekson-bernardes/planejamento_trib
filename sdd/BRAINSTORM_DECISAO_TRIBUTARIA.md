# BRAINSTORM: Decisão Tributária (ciclo 3 do Planejamento Tributário)

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|---|---|
| Feature | DECISAO_TRIBUTARIA |
| Date | 2026-09-25 |
| Author | brainstorm-agent |
| Status | Handoff Ready |

## Initial Idea

**Raw Input:** "Use a skill sdd-brainstorm para o ciclo 3" — ciclo 3 do planejamento tributário: projeção, sensibilidade, ponto de virada, recomendação/parecer, aprovação do responsável técnico, PDF executivo e custo de conformidade (itens adiados no ciclo 2). Base: PRD em `docs/PRD_Planejamento_Tributario.md`, `sdd/*_MOTOR_TRIBUTARIO.md` e `kb/`.

**Context Gathered:**
- PRD §9 (projeções): métodos realizado anual, média simples, sazonalidade (≥ 24 meses), orçamento e cenários; 10 variáveis mínimas de sensibilidade; a recomendação indica o ponto de virada.
- PRD §10 (comparação e recomendação): métricas por regime (tributos, alíquota efetiva, carga consumo/renda/folha, créditos, resultado líquido, custo de conformidade, economia vs. regime atual e segundo colocado); algoritmo de decisão com "resultado inconclusivo" abaixo de limiar, bloqueio por dado crítico ausente, custo de conformidade separado; explicabilidade ("recomendamos X porque…", três fatores, intervalo de sensibilidade, ressalvas, data-base normativa, responsável técnico).
- PRD §11: RF-11 cenários e sensibilidade (Should), RF-12 PDF executivo (Must), RF-13 fluxo elaborar → revisar → aprovar → emitir (Must), RF-14/RF-15 (Should).
- PRD §15: "Dada recomendação emitida, PDF informa data-base, premissas, ressalvas, responsável e assinatura/aprovação".
- Observado no projeto: motor do ciclo 2 calcula somente o período realizado, com simulações imutáveis, memória linha a linha e regras versionadas de 2026 (`services/worker/rules/2026`, versão 2026.1.0); não há regras de 2027.
- Observado no projeto: papéis existentes são apenas `admin` e `analyst` (`supabase/migrations/20260924000001_tenancy.sql`).
- Observado nos dados: amostra com 3 competências completas (06, 07, 08/2026); o PGDAS-D traz séries de receita e folha dos 12 meses anteriores; nenhum trimestre completo sem setembro; golden 06–08/2026 aprovado (Simples 99.249,46 < Presumido 102.578,12 < Real 299.770,55; diferença Simples × Presumido ≈ 3%).
- KB: `kb/planejamento-comparativo/patterns/encontrar-ponto-de-virada.md` define o método (uma variável por vez, bisseção, descontinuidades, robustez > 20% / 5–20% / < 5%).

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|---|---|---|
| Likely Location | `services/worker/src/worker/engine/` (motor), `services/worker/src/worker/pipeline.py` (jobs), `supabase/migrations/` (tabelas, papéis, RLS), `apps/web/src/app/(app)/cases/[id]/planning/` (telas) | Projeção e sensibilidade reutilizam as funções do motor do ciclo 2; fluxo e PDF são componentes novos |
| Relevant KB Domains | `kb/planejamento-comparativo`, `kb/simples-nacional`, `kb/lucro-presumido`, `kb/lucro-real` | Ponto de virada, descontinuidades (faixa, Fator R, adicional, LC 224, sublimite) e comparação por exercício |
| IaC Patterns | N/A (Supabase local via `npx supabase`, worker em Docker, Next.js) | Geração de PDF no worker exige dependência nova na imagem Docker |

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|---|---|---|
| 1 | Qual o recorte do ciclo 3? | (a) Decisão completa: projeção, sensibilidade com ponto de virada, recomendação, fluxo revisar → aprovar → emitir e PDF executivo | Ciclo cobre a fase 4 inteira do roadmap do PRD |
| 2 | Horizonte e método da projeção? (usuário pediu sugestão; recomendado (a)) | (a) Exercício 2026 jan–dez com orçamento opcional: jan–mai pelas séries do PGDAS-D, jun–ago realizado, set–dez média simples ou orçamento informado | Usa só regras de 2026; 2027 (Reforma) fica como ressalva; campos sem documento em jan–mai viram premissa proporcional à receita |
| 3 | Quem aprova a recomendação? | (a) Papel novo de responsável técnico (nome + CRC), atribuído por escritório; quem elabora não aprova | Novo papel, RLS e segregação de funções |
| 4 | Política da recomendação? | (a) Limiar configurável por escritório (padrão 5% do custo do vencedor); custo de conformidade informado por regime e só exibido | Amostra (≈ 3%) tende a "inconclusivo"; conformidade não altera ranking |
| 5 | Amostras e referências? | (c) Usar o SPTE como referência de formato do comparativo, sem validar números (resposta inicial (a), modelo de parecer, alterada pelo usuário para (c)) | PDF segue o formato SPTE + seções exigidas pelo PRD; sem ground truth de projeção |

## Sample Data Inventory

| Type | Location | Count | Notes |
|---|---|---:|---|
| Input files | `docs/Amostras/` (PGDAS-D, folha, DRE, balancete de 06, 07 e 08/2026) | 12 | Fora do Git (CPF/RG); base da projeção 2026 |
| Output examples | `docs/Amostras/SPTE - Simulador de Planejamento Tributário Econet.pdf` | 1 | 10 páginas; outra empresa (serviços hospitalares, Anexo V); referência apenas de formato |
| Ground truth | `services/worker/tests/golden/motor_202608.json`, `motor_202606_08.json` | 2 | Goldens do período realizado; não há ground truth de projeção ou recomendação |
| Related code | `services/worker/src/worker/engine/` | 11 | Motor do ciclo 2 reutilizado pela projeção e pela sensibilidade |

**How samples will be used:**
- As 12 amostras alimentam a Projeção 2026 (realizado jun–ago) e as séries do PGDAS-D (jan–mai).
- O SPTE define o formato do PDF: resultado mensal por regime (tributos × jan–dez, com Anexo e Fator R), observações por mês e comparativo final regimes × tributos com a frase de maior vantagem.
- Os goldens do ciclo 2 garantem que a projeção reutiliza o motor sem alterar o cálculo do realizado.

## Approaches Explored

### Approach A: Projeção como simulação do motor + sensibilidade recalculada — Recommended

**Description:** O worker monta os 12 meses de 2026 marcados por origem (realizado, estimado pelo PGDAS-D, projetado por média/orçamento), roda as mesmas funções do motor do ciclo 2 e grava uma simulação "Projeção 2026" imutável com memória. A sensibilidade recalcula o motor variando uma variável por vez, acha o ponto de virada por bisseção e classifica a robustez. A recomendação (recomendado / inconclusivo / bloqueado) passa pelo fluxo com responsável técnico e gera PDF imutável com hash.

**Pros:**
- Um único motor: projeção e realizado não divergem.
- Descontinuidades (faixa do Simples, Fator R, adicional de IRPJ, LC 224, sublimite) aparecem naturalmente na sensibilidade.
- Mesma auditoria e reprodutibilidade do ciclo 2.

**Cons:**
- Maior volume de código.
- Sensibilidade executa dezenas de cálculos por variável (≈ 40 ms cada no motor atual).

**Why Recommended:** única abordagem em que todo número da recomendação chega a fórmula, regra e origem (PRD §10.3) e em que o ponto de virada respeita as descontinuidades exigidas pela KB.

### Approach B: Anualização + sensibilidade linear

**Description:** Multiplica o custo realizado de cada regime pela razão de receita anual e estima sensibilidade por elasticidade.

**Pros:**
- Simples e rápida de construir.

**Cons:**
- Ignora descontinuidades; ponto de virada errado perto de faixas.
- Projeção sem memória linha a linha, contra o PRD.

### Approach C: Projeção e sensibilidade em planilha; sistema só com fluxo

**Description:** XLSX com fórmulas para o analista; o sistema faz apenas recomendação, aprovação e PDF.

**Pros:**
- Menor esforço de construção.

**Cons:**
- Números fora do motor: perde reprodutibilidade e auditoria.
- Recomendação dependente de planilha editável.

## Selected Approach

| Attribute | Value |
|---|---|
| Chosen | Approach A |
| User Confirmation | 2026-09-25, "sim, opção A" |
| Reasoning | Mantém rastreabilidade e reprodutibilidade do ciclo 2 e trata corretamente as descontinuidades no ponto de virada |

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|---|---|---|
| 1 | Ciclo 3 = decisão completa (projeção, sensibilidade, recomendação, fluxo, PDF) | Entregar a fase 4 do roadmap como relatório explicável aprovado | Só análise (b); só entregável sobre o realizado (c) |
| 2 | Projeção do exercício 2026 (jan–mai PGDAS-D, jun–ago realizado, set–dez média ou orçamento) | Só há regras de 2026; 2027 muda com a Reforma (CBS); comparação do exercício é a base usual da decisão | Próximos 12 meses (set/2026–ago/2027) com regras de 2026 |
| 3 | Orçamento opcional substitui a média nos meses projetados | Cobre sazonalidade sem 24 meses de histórico | Somente média automática; somente orçamento |
| 4 | Campos sem documento em jan–mai (lucro, créditos, ICMS) proporcionais à receita e marcados como premissa | PGDAS-D traz só receita e folha desses meses | Exigir DRE/balancete de todos os meses |
| 5 | Papel novo de responsável técnico (nome + CRC); quem elabora não aprova | PRD exige responsável técnico e aprovação profissional | Admin aprova; qualquer outro membro aprova |
| 6 | Limiar de inconclusivo configurável por escritório, padrão 5% do custo do vencedor | PRD §10.2; política transparente | Sem limiar automático |
| 7 | Custo de conformidade informado por regime e somente exibido | PRD §10.2 ("não serão ocultamente somados") | Chave para somar ao ranking |
| 8 | Sensibilidade sobre 5 variáveis: receita, margem, folha/receita, créditos de PIS/Cofins, ICMS/ISS | Variáveis calculáveis com os dados e o motor atuais | As 10 variáveis do PRD |
| 9 | Recomendação alterada após aprovação volta a rascunho; PDF emitido permanece imutável | Auditabilidade (PRD §12) | Editar recomendação emitida |
| 10 | PDF no formato do SPTE + seções do PRD, com ressalva de que 2027 terá regras de transição da Reforma | Referência de formato escolhida pelo usuário; PRD §8.5 | Modelo de parecer próprio do escritório (não fornecido) |

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed/Deferred | Can Add Later? |
|---|---|---|
| Projeção por sazonalidade | Exige histórico ≥ 24 meses; amostra tem 3 | Yes |
| Cenários conservador/base/expansão | Sensibilidade por variável já mostra até onde a recomendação vale | Yes |
| Variáveis mix de atividades, B2B/B2C e benefícios fiscais | Dependem da Reforma ou de cadastro inexistente | Yes |
| Resultado líquido e fluxo de caixa após tributos | Não necessário para a recomendação do MVP | Yes |
| Assinatura eletrônica do PDF | Identificação do responsável + registro de aprovação com data e hash atendem ao MVP | Yes |
| Duplicar cenário e comparar versões (RF-14) | "Should" no PRD | Yes |
| Painel de pendências e alertas (RF-15) | "Should" no PRD | Yes |
| Projeção de 2027 com regras da Reforma (CBS/IBS) | Regras de 2027 não parametrizadas | Yes |

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---|---|---|---|
| Checkpoint 1: YAGNI, conceito, limites e componentes (montador de projeção, sensibilidade, recomendação, tabelas, papel de responsável técnico, PDF, telas) | Yes | "sim" | No |
| Checkpoint 2: fluxo de dados, falhas (bloqueio por dado crítico, regime não calculado/inelegível fora do ranking, premissa alterada após aprovação), dependências e comportamento esperado na amostra | Yes | "sim" | No |

## Suggested Requirements for /define

### Problem Statement (Draft)

O escritório compara os regimes apenas no período realizado e não consegue emitir, com aprovação do responsável técnico, uma recomendação explicável do exercício que mostre projeção, ponto de virada e ressalvas.

### Target Users (Draft)

| User | Pain Point |
|---|---|
| Analista do escritório | Precisa projetar o exercício e testar sensibilidade sem planilhas paralelas |
| Responsável técnico (contador) | Precisa revisar e aprovar a recomendação antes de ela chegar ao cliente, com premissas e ressalvas visíveis |
| Cliente do escritório | Recebe um PDF executivo com a recomendação, a economia e as condições em que ela deixa de valer |

### Success Criteria (Draft)

- [ ] Projeção 2026 calculada pelas mesmas funções do motor, reprodutível (mesmas entradas → mesmo resultado) e com cada mês marcado como realizado, estimado ou projetado.
- [ ] Para cada uma das 5 variáveis, o sistema informa o ponto de virada ou "sem virada no intervalo", com a distância e a classificação de robustez.
- [ ] Diferença entre os dois primeiros abaixo do limiar do escritório gera "resultado inconclusivo"; dado crítico ausente bloqueia a recomendação.
- [ ] Somente o responsável técnico aprova, e nunca a própria elaboração; apenas recomendação aprovada gera PDF emitido.
- [ ] PDF emitido é imutável, tem hash e informa data-base, premissas, ressalvas, responsável e registro de aprovação.
- [ ] Tempo da projeção + sensibilidade: TBD (o PRD pede resultado padrão em até 5 minutos).

### Constraints Identified

- Somente regras do exercício 2026 (versão 2026.1.0); 2027 fica como ressalva.
- Janeiro a maio sem DRE/balancete: lucro, créditos e ICMS estimados em proporção à receita, marcados como premissa.
- Amostra com 3 competências completas e nenhum trimestre fechado.
- Regras `verificado: false` (LC 224 trimestral, ICMS/ISS da faixa 6 pela faixa 5, cumulatividade hospitalar) aparecem como ressalva no PDF.
- Isolamento por escritório (RLS), logs sem dados sensíveis e amostras fora do Git, como nos ciclos anteriores.
- Sem ground truth de projeção ou recomendação; validação por reprodutibilidade, casos construídos e revisão do responsável técnico.

### Out of Scope (Confirmed)

- Sazonalidade, cenários conservador/base/expansão, variáveis de mix/B2B-B2C/benefícios.
- Resultado líquido e fluxo de caixa após tributos.
- Assinatura eletrônica.
- RF-14 (duplicar/comparar cenários) e RF-15 (painel de pendências).
- Projeção de 2027 e regras da Reforma Tributária.

## Session Summary

| Metric | Value |
|---|---:|
| Questions Asked | 5 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 8 |
| Validations Completed | 2 |

## Next Step

Execute o **SDD Define by RDD**.
