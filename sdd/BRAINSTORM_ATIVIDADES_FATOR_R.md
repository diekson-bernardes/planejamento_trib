# BRAINSTORM: Atividades mistas e Fator R no Planejamento Rápido

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|---|---|
| Feature | ATIVIDADES_FATOR_R |
| Date | 2026-09-28 |
| Author | brainstorm-agent |
| Status | Handoff Ready |

## Initial Idea

**Raw Input:** "Use a skill sdd-brainstorm para o ciclo 6" → pergunta 1 respondida com "(c)" (precisão do Planejamento Rápido) → pergunta 2 respondida com "(a) e (b)" (atividades mistas e Fator R).

**Context Gathered:**
- Ciclos 1–5 e os ajustes de layout estão na `master` (PR #7, merge `809be4b`).
- O Planejamento Rápido (ciclo 5) monta o dossiê a partir do faturamento de 12 meses, da folha e da DRE (PDF ou digitados) e compara Simples por dentro × Simples por fora (2027) × Presumido.
- A consulta de CNPJ via n8n (`Consultar_CNPJ`, BrasilAPI) já preenche a razão social e o CNAE principal; a resposta da BrasilAPI também traz os CNAEs secundários (hoje não guardados).
- Não há amostras reais para este ciclo; o usuário aceitou um caso fictício validado por ele.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|---|---|---|
| Likely Location | `services/worker/src/worker/engine/quick_view.py:175-210` cria uma única atividade (CNAE principal) com variantes ST/monofásico por percentual | Criar N atividades a partir dos CNAEs marcados, cada uma com sua parcela da receita |
| Likely Location | `services/worker/src/worker/engine/simples.py:120-160` já calcula o Simples por atividade (perfil, anexo, Fator R por competência via `folha.folha_12m`) | Reaproveitar o caminho multiatividade do motor; sem motor novo |
| Likely Location | `quick_view.py:198-208` sugere `folha.folha_12m` = média dos meses informados × 12, igual em todos os meses | Substituir pela folha acumulada real dos 12 meses anteriores de cada competência |
| Likely Location | `services/worker/src/worker/cnpj_lookup.py`, `pipeline.py` (`lookup_company`), `apps/web/src/components/CompanyCnae.tsx`, tabela `companies` | Guardar CNAEs secundários (código + descrição) e exibi-los para marcação |
| Relevant KB Domains | Simples Nacional (LC 123/2006: anexos I–V, Fator R ≥ 28%), Presumido por atividade, encargos da folha (INSS patronal/FGTS) | Alíquotas de INSS/FGTS da "folha ideal" ficam configuráveis nas regras e marcadas como não verificadas |
| IaC Patterns | Supabase local (migrations + pgTAP + RLS `is_member`/`is_admin`), worker Python, Next.js 16 | Nova migration para CNAEs secundários/atividades do dossiê; RLS por escritório como hoje |

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|---|---|---|
| 1 | Qual o principal problema que o ciclo 6 deve resolver? (produção, mix B2B, precisão do Rápido, novas entradas, outro) | (c) Precisão do Planejamento Rápido | Escopo restrito ao dossiê rápido; motor e regimes atuais preservados |
| 2 | Qual imprecisão mais atrapalha hoje? (atividades mistas, Fator R, tabela CNAE, Presumido simplificado) | (a) atividades mistas e (b) Fator R | Dois eixos: dividir a receita entre atividades e calcular o Fator R corretamente |
| 3 | De onde vem a divisão do faturamento entre atividades? | (a) Percentual digitado pelo usuário, atividades sugeridas pelos CNAEs da Receita | Sem parser novo; percentual único para os 12 meses |
| 4 | O que mudar no Fator R? (mês a mês, folha ideal, folha incompleta) | (d) Todos | Fator R por competência + simulação informativa + escolha explícita para folha incompleta |
| 5 | Checkpoint 1: exigir soma exata ou tolerância? | Exigir 100% exato | Homologação bloqueada se a soma ≠ 100,00% |

## Sample Data Inventory

| Type | Location | Count | Notes |
|---|---|---:|---|
| Input files | N/A | 0 | Sem amostra real de atividade mista ou Fator R |
| Output examples | N/A | 0 | — |
| Ground truth | N/A | 0 | Novo golden fictício (comércio Anexo I + serviço com Fator R III/V) a ser validado pelo usuário antes de aprovado |
| Related code | `services/worker/src/worker/engine/{quick_view,simples,activities,payroll}.py` | 4 | Caminho multiatividade e Fator R já existentes no motor |

**How samples will be used:**
- Caso fictício sem PII, construído no build, com números conferidos pelo usuário antes de virar golden.
- Goldens existentes (`motor_202608`, `motor_202606_08`, `decisao_2026`, `decisao_2027`, `rapido_2027`) servem de teste de não regressão.

## Approaches Explored

### Approach A: Multiatividade no Rápido reaproveitando o motor — Recommended

**Description:** Atividades vindas dos CNAEs (principal + secundários da Receita, ou digitados), com percentual por atividade somando 100%; perfil sugerido pela tabela CNAE por atividade; Fator R por competência com folha acumulada de 12 meses; escolha explícita para folha incompleta; bloco informativo "folha ideal".

**Pros:**
- Reaproveita o cálculo multiatividade do motor, já coberto por golden.
- Resolve os dois problemas no resultado principal, com rastreabilidade linha a linha.
- Atividade única produz exatamente o resultado atual.

**Cons:**
- Percentual fixo para os 12 meses (sem sazonalidade por atividade).
- Encargos da folha ideal usam alíquotas padrão configuráveis, não verificadas.

**Why Recommended:** corrige o número principal para empresas mistas e com Fator R com a menor mudança no motor.

### Approach B: Rápido com atividade única + misto como cenário na decisão

**Description:** Manter um anexo no cálculo principal e oferecer o misto como cenário alternativo na tela de decisão.

**Pros:**
- Quase nenhuma mudança no motor; goldens intocados.

**Cons:**
- O resultado principal continua errado para empresas mistas — o problema central não é resolvido.

### Approach C: Dividir em dois ciclos (Fator R agora, misto depois)

**Description:** Ciclo 6 só com Fator R; ciclo 7 com atividades mistas.

**Pros:**
- Entregas menores, golden por entrega.

**Cons:**
- Fator R só se aplica à parcela de serviço do Anexo V; separar força mexer duas vezes no mesmo trecho do motor.

## Selected Approach

| Attribute | Value |
|---|---|
| Chosen | Approach A |
| User Confirmation | 2026-09-28, resposta "a" |
| Reasoning | Resolve atividades mistas e Fator R no resultado principal reaproveitando o motor multiatividade existente |

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|---|---|---|
| 1 | Divisão da receita por percentual digitado, único para os 12 meses | Sem amostra de relatório por atividade; baixo esforço do usuário | Valor por mês e atividade; leitura do PDF; leitura do PGDAS-D |
| 2 | Atividades sugeridas pelos CNAEs principal + secundários da consulta à Receita, com inclusão manual de CNAE | Aproveita a integração n8n existente | Só digitação manual |
| 3 | Soma dos percentuais exatamente 100,00% para homologar | Pedido explícito do usuário | Tolerância de arredondamento |
| 4 | Uma atividade marcada → 100% automático e resultado idêntico ao atual | Não regressão do `rapido_2027` | — |
| 5 | Fator R por competência = folha acumulada dos 12 meses anteriores ÷ RBT12 | Corrige a média × 12 repetida em todos os meses | Manter média |
| 6 | Folha incompleta exige escolha explícita "completar pela média" ou "considerar zero"; sem nenhum mês de folha, só "zero" | Evita Fator R silencioso; escolha aparece no PDF | Completar pela média automaticamente |
| 7 | "Folha ideal" informativa (folha faltante para 28%, economia de Simples III vs V, custo de INSS/FGTS), fora dos totais | Apoia decisão sem alterar o resultado | Otimização automática do pró-labore |
| 8 | ST e monofásico continuam percentuais da empresa inteira (efeito na parcela de comércio) | Mantém o modelo do ciclo 5 | Percentual ST/mono por atividade |
| 9 | CNAEs secundários guardados na empresa (código + descrição), sem sócios/QSA | Restrição de privacidade vigente | Guardar a resposta completa da BrasilAPI |

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed/Deferred | Can Add Later? |
|---|---|---|
| Percentual de atividade por mês (sazonalidade) | Sem dado disponível hoje | Yes |
| Divisão por atividade lida do PDF de faturamento | Sem amostra | Yes |
| Revisão contábil da tabela CNAE → anexo | Não é o problema escolhido; segue pendente | Yes |
| Otimização automática do pró-labore | Decisão fica com o usuário; simulação basta | Yes |
| Atividades mistas no dossiê completo | Ele já lê atividades do PGDAS-D | N/A |

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---|---|---|---|
| Checkpoint 1 — conceito, componentes e limites | Yes | "sim, exigir 100% exato" | Yes (soma exata, sem tolerância) |
| Checkpoint 2 — fluxo de dados, falhas, segurança e pronto quando | Yes | "sim, pode gerar o documento" | No |

## Suggested Requirements for /define

### Problem Statement (Draft)

O Planejamento Rápido aplica um único anexo (CNAE principal) a todo o faturamento e estima o Fator R pela média da folha repetida em todos os meses, o que distorce o Simples de empresas com atividades mistas ou sujeitas ao Fator R e pode inverter a recomendação de regime.

### Target Users (Draft)

| User | Pain Point |
|---|---|
| Contador/analista do escritório que faz o planejamento rápido | Não consegue representar empresa com comércio e serviço nem ver em que mês o Fator R muda o anexo |
| Administrador/sócio do escritório que apresenta a recomendação ao cliente | Precisa mostrar quanto de folha falta para o Anexo III e se compensa |

### Success Criteria (Draft)

- [ ] Goldens `motor_202608`, `motor_202606_08`, `decisao_2026`, `decisao_2027` e `rapido_2027` permanecem idênticos.
- [ ] Novo golden fictício (comércio Anexo I + serviço com Fator R) aprovado pelo usuário.
- [ ] Dossiê rápido com uma atividade produz resultado idêntico ao atual.
- [ ] Homologação recusada quando a soma dos percentuais ≠ 100,00%.
- [ ] Tela e PDF mostram Fator R mês a mês (folha 12m, RBT12, %, anexo) e o bloco "folha ideal".
- [ ] `npm run verify` passa.

### Constraints Identified

- Regimes do Rápido: SIMPLES, SIMPLES_HIBRIDO (2027) e PRESUMIDO; Real fora.
- Sem armazenar/logar sócios ou QSA da consulta de CNPJ; logs só com IDs e códigos.
- RLS por escritório (`is_member`) em todas as tabelas novas.
- Goldens sem PII; `docs/Amostras` fora do git.
- Chamada real ao n8n só com autorização do usuário.
- Alíquotas de INSS/FGTS da folha ideal configuráveis e marcadas como não verificadas.

### Out of Scope (Confirmed)

- Sazonalidade por atividade; leitura da divisão por atividade em PDF; revisão contábil da tabela CNAE; otimização automática do pró-labore; atividades mistas no dossiê completo; produção/deploy; mix B2B da Reforma; novas fontes de importação.

## Session Summary

| Metric | Value |
|---|---:|
| Questions Asked | 5 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 5 |
| Validations Completed | 2 |

## Next Step

Execute o **SDD Define by RDD**.
