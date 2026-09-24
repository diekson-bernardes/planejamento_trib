# BRAINSTORM: Motor Tributário — Elegibilidade e Cálculo dos Regimes (ciclo 2)

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|---|---|
| Feature | MOTOR_TRIBUTARIO |
| Date | 2026-09-24 |
| Author | brainstorm-agent |
| Status | Handoff Ready |

## Initial Idea

**Raw Input:** "observei que o sistema não fez nenhum planejamento tributário, qual seria o segundo ciclo conforme o brainstorm" → "sim" (iniciar o brainstorm do ciclo 2: motor tributário — elegibilidade e cálculo de Simples, Presumido e Real consumindo o snapshot homologado do ciclo 1; PRD §8–10 e §17; KB em `kb/`).

**Context Gathered:**
- (Provided) O ciclo 1 (importação, conciliação, homologação) foi concluído e verificado; o usuário constatou que ainda não há planejamento tributário e pediu o ciclo 2.
- (Observed) PRD `docs/PRD_Planejamento_Tributario.md` §17: Fase 3 "Cálculo MVP" (elegibilidade + três regimes + memória) e Fase 4 "Decisão" (comparação, projeção, sensibilidade, recomendação). §8: regras em tabelas versionadas; regime inelegível = "não aplicável"; cada resultado guarda a versão normativa. §10.2: regra legal sem parametrização não é estimada silenciosamente.
- (Observed) Ciclo 1 entrega um snapshot homologado imutável (`snapshots.content` + `sha256`) com valores efetivos, ajustes, validações e conciliações; worker Python com fila `jobs`, `Decimal`, pytest e golden; site Next.js com RLS por escritório (`sdd/DESIGN_IMPORTACAO_CONCILIACAO.md`, `sdd/BUILD_REPORT_IMPORTACAO_CONCILIACAO.md`).
- (Observed) O snapshot das amostras contém PGDAS-D de 06, 07 e 08/2026 e folha, DRE e balancete apenas de 08/2026; o PGDAS-D traz a série de receitas anteriores (seção 2.2, 01/2025 a 07/2026) e a seção 2.3 (folha anterior, "Nenhuma" na amostra).
- (Observed) KB `kb/` (6 domínios, PENDENTE DE REVISÃO) contém as regras e receitas: `simples-nacional/patterns/calcular-das-mensal.md`, `lucro-presumido/patterns/calcular-trimestre-presumido.md`, `lucro-real/patterns/apurar-irpj-csll-lucro-real.md`, `planejamento-comparativo/*`.
- (Observed) O DAS de jun/2026 da amostra foi recalculado ao centavo no ciclo anterior: faixa 6 do Anexo I (efetiva 9,159%) para tributos federais e ICMS pela faixa 5 (12,027% × 33,5%).
- (Observed) Novo arquivo `docs/Amostras/SPTE - Simulador de Planejamento Tributário Econet.pdf` (10 páginas): simulação Econet do cliente CONESP (CNAEs 8630-5/01 e 8630-5/03), jan–jul/2026, Simples no Anexo V (Fator R 11,92%–13,18%), comparativo total Simples 195.342,11 · Presumido 190.847,68 · Real 370.665,08 ("maior vantagem: Lucro Presumido"). O PDF não traz as entradas (receitas, folha, lucro).
- (Inferred) Pelos números Econet: receita do período ≈ R$ 1.018.915 (Cofins 3% e PIS 0,65% coerentes); ISS 5%; no Real, PIS/Cofins iguais ao cumulativo — coerente com a manutenção de serviços hospitalares no regime cumulativo (Lei 10.833/2003, art. 10). Não verificado.
- (Inferred) Na p. 6 do PDF Econet (comparativo do CNAE 8630-5/03), a CPP do Real (6.000,00) diverge da CPP do total (53.004,79) — possível inconsistência do relatório; não investigada.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|---|---|---|
| Likely Location | `services/worker/src/worker/` (novos módulos do motor), `services/worker/rules/` (regras versionadas), `supabase/migrations/` (novas tabelas), `apps/web/src/app/(app)/cases/[id]/` (telas de premissas e comparativo) | Extensão do monorepo do ciclo 1 |
| Relevant KB Domains | `kb/simples-nacional`, `kb/lucro-presumido`, `kb/lucro-real`, `kb/planejamento-comparativo`, `kb/documentos-fonte` | Fonte das regras; revisão contábil pendente |
| IaC Patterns | Supabase local (migrations + RLS + pgTAP), worker em Docker, Verify Gate `npm run verify` | Reusar o mesmo gate, ampliado |

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|---|---|---|
| 1 | Qual o recorte do ciclo 2? | (a) Só cálculo (Fase 3): elegibilidade + três regimes sobre o período realizado, com memória e comparativo; projeção, sensibilidade e recomendação no ciclo 3 | Sem parecer/recomendação neste ciclo; foco em exatidão verificável |
| 2 | Qual período o cálculo cobre? | (a) Mês a mês, só nas competências completas (PGDAS + folha + DRE + balancete); Presumido/Real trimestrais marcados "parcial" se incompletos | Funciona com as amostras atuais; meses incompletos ficam fora com aviso |
| 3 | Como tratar dados que os documentos não trazem (ICMS/ISS, créditos PIS/Cofins, adições/exclusões)? | (a) Premissas informadas pelo analista com sugestão automática derivada dos documentos, confirmadas ou alteradas com justificativa, marcadas como premissa na memória | Nova entidade de premissas com autor/data/origem; cálculo bloqueado com premissa pendente |

## Sample Data Inventory

| Type | Location | Count | Notes |
|---|---|---:|---|
| Input files | `docs/Amostras/` (PGDAS-D 06–08/2026, folha, DRE, balancete 08/2026) e snapshot homologado local | 6 | Mesmas amostras do ciclo 1; comércio, Anexo I faixa 6 |
| Output examples | `docs/Amostras/SPTE - Simulador de Planejamento Tributário Econet.pdf` | 1 | Referência de **formato** (quadro mensal por regime/CNAE, comparativo por tributo, vencedor, observações); sem entradas, não é caso dourado |
| Ground truth | DAS declarado nos 3 PGDAS-D; exemplos numéricos da `kb/` | 3 + exemplos | Usuário escolheu (d): casos dourados montados pela IA a partir da KB e das amostras, conferidos pelo usuário |
| Related code | Ciclo 1: `services/worker/`, `supabase/`, `apps/web/` | — | Fila, `Decimal`, golden, RLS, snapshot |

**How samples will be used:**
- Simples: recalcular o DAS de 06, 07 e 08/2026 e bater ao centavo com o PGDAS-D (inclui faixa 6 com ICMS pela faixa 5).
- Presumido e Real: casos dourados da KB (trimestre de comércio R$ 54.570,00; Real trimestral com compensação R$ 43.980,00) e um caso construído com a amostra de 08/2026, conferido pelo usuário.
- Econet (CONESP): modelo da tela e do relatório do comparativo; revela a regra de PIS/Cofins cumulativo para serviços hospitalares no Real (a confirmar).

## Approaches Explored

### Approach A: Motor Python no worker com regras versionadas no repositório — Recommended

**Description:** Novo job `calculate` no worker lê o snapshot homologado e as premissas confirmadas, calcula elegibilidade + Simples (mensal) + Presumido e Real (trimestrais) nas competências completas, e grava `simulations`/`simulation_lines` com memória. Regras (anexos, faixas, repartição, presunções, alíquotas, limites, vigência, fonte legal) ficam em arquivos versionados; cada simulação grava versão e hash das regras.

**Pros:**
- Reaproveita fila, `Decimal`, pytest e golden do ciclo 1.
- Determinístico e reproduzível (snapshot + premissas + versão de regras = mesmo resultado), como exige o PRD.
- Regras desacopladas do código e auditáveis no Git.

**Cons:**
- Cálculo assíncrono (segundos na fila).
- Nova regra exige deploy (sem tela de publicação de regras neste ciclo).

**Why Recommended:** Atende às exigências do PRD (regras versionadas, reprodutibilidade, memória auditável) sobre infraestrutura já testada.

### Approach B: Motor em SQL/PL/pgSQL no Postgres

**Description:** Funções no banco calculam direto sobre `effective_values`.

**Pros:**
- Transacional, sem fila.

**Cons:**
- Regras com faixas, repartição, Fator R e trimestres ficam difíceis de ler, testar e versionar.
- pgTAP é pobre para cálculo; manutenção ruim para quem conhece o tributário.

### Approach C: Motor em TypeScript no Next.js com regras em JSON

**Description:** Cálculo síncrono em server actions ao abrir o comparativo.

**Pros:**
- Resposta imediata; uma linguagem no front.

**Cons:**
- Aritmética decimal em JS exige biblioteca; lógica de domínio dividida entre worker e web; reprodutibilidade dependente do deploy do site.

## Selected Approach

| Attribute | Value |
|---|---|
| Chosen | Approach A — Motor Python no worker com regras versionadas no repositório |
| User Confirmation | Confirmado na conversa em 2026-09-24 ("A") |
| Reasoning | Regras versionadas, reprodutibilidade e memória auditável sobre a infraestrutura do ciclo 1 |

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|---|---|---|
| 1 | Ciclo 2 = elegibilidade + cálculo dos três regimes + memória + comparativo ordenado, sem recomendação | Conferir cada cálculo com casos dourados antes de virar parecer (PRD: "casos dourados conferidos pelo contador") | Cálculo + decisão num só ciclo; um regime por vez |
| 2 | Base = snapshot homologado; somente competências completas; Presumido/Real trimestrais "parciais" quando incompletos | Funciona com os dados reais do piloto sem inventar meses | Exigir 12 meses; completar lacunas por média (projeção) |
| 3 | Lacunas dos documentos viram premissas sugeridas e confirmadas pelo analista, com justificativa quando alteradas | PRD separa dados extraídos, premissas e regras | Só tributos federais; cálculo completo por NCM |
| 4 | Premissa pendente bloqueia o cálculo; declaração de elegibilidade ausente → regime "indeterminado" | Não estimar silenciosamente (PRD §10.2) | Assumir padrões sem confirmação |
| 5 | Regras em arquivos versionados no repositório; simulação grava versão e hash | Reprodutibilidade e auditoria sem tela de administração | Regras em tabela com tela de publicação |
| 6 | Nova premissa ou nova versão de regra gera nova simulação; anteriores preservadas | Comparar versões e manter trilha | Sobrescrever simulação |
| 7 | Comparativo ordenado por custo entre elegíveis, sem parecer | Recomendação é do ciclo 3 | Recomendar já neste ciclo |
| 8 | Simples no MVP inclui faixa 6 com ICMS/ISS pela faixa 5, ST/monofásico e CPP fora do DAS no Anexo IV | Regras observadas nas amostras e na KB | Simples simplificado por alíquota efetiva única |
| 9 | Real com PIS/Cofins não cumulativo e créditos como premissa, incluindo tratamento de receitas mantidas no cumulativo (ex.: serviços hospitalares) | Observado no comparativo Econet; evita erro material em serviços de saúde | Aplicar 9,25% a toda receita do Real |

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed/Deferred | Can Add Later? |
|---|---|---|
| Real anual por estimativa com balancete de suspensão | Trimestral basta para o período realizado | Yes |
| Projeção 12 meses, sensibilidade, ponto de virada, recomendação, aprovação, PDF executivo, custo de conformidade | Ciclo 3 (decisão da pergunta 1) | Yes |
| Pró-labore × dividendos (Lei 15.270/2025), JCP | Planejamento do sócio, não do regime | Yes |
| CBS/IBS (reforma) | Meses realizados de 2026 são teste sem custo; entra com a projeção de 2027 | Yes |
| Tela de administração/publicação de regras | Versionamento via Git atende ao MVP | Yes |
| ICMS por NCM, DIFAL, MEI | Sem cadastro fiscal no MVP | Yes |

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---|---|---|---|
| Checkpoint 1: YAGNI, conceito (premissas → cálculo → simulação), componentes (regras versionadas, motor, tabelas `assumptions`/`simulations`/`simulation_lines`, telas) e limites | Yes | "sim" | No |
| Checkpoint 2: fluxo (snapshot → competências completas → sugestão de premissas → revisão → `calculate` idempotente → gravação → comparativo com drill-down → nova simulação a cada mudança), erros, casos dourados e dependências | Yes | "sim" | No |

## Suggested Requirements for /define

### Problem Statement (Draft)

Depois de homologar os dados de um cliente, o escritório ainda precisa calcular manualmente (ou em simulador externo, como o Econet) quanto a empresa pagaria no Simples, no Presumido e no Real, sem trilha até os documentos nem controle das premissas; o sistema deve calcular os três regimes sobre o período realizado, com elegibilidade, premissas justificadas e memória de cálculo auditável.

### Target Users (Draft)

| User | Pain Point |
|---|---|
| Analista contábil/fiscal | Refazer em planilha/simulador os cálculos dos três regimes e explicar de onde veio cada número |
| Responsável técnico / contador | Conferir premissas e regras antes de o comparativo virar parecer (ciclo 3) |
| Administrador do escritório | Garantir que as regras aplicadas sejam versionadas e rastreáveis |

### Success Criteria (Draft)

- [ ] O DAS recalculado pelo motor para 06, 07 e 08/2026 da amostra é igual ao DAS declarado no PGDAS-D, por tributo, com diferença ≤ R$ 0,01.
- [ ] Os casos dourados da KB são reproduzidos exatamente: Presumido comércio trimestre R$ 54.570,00; Real trimestral com compensação R$ 43.980,00 e saldo de prejuízo R$ 87.000,00.
- [ ] 100% das linhas da simulação têm fórmula/base/alíquota, regra (com versão) e origem (valor do snapshot ou premissa).
- [ ] Mesmo snapshot + mesmas premissas + mesma versão de regras produzem simulação idêntica (mesmo hash de resultado).
- [ ] Nenhum regime inelegível aparece no ordenamento; inelegível e indeterminado aparecem com motivo.
- [ ] Nenhum cálculo roda com premissa pendente.
- [ ] Caso dourado construído com a amostra de 08/2026 para Presumido e Real: valores TBD, a conferir pelo usuário.
- [ ] Tempo máximo do cálculo por dossiê: TBD.

### Constraints Identified

- Entrada exclusiva: snapshot homologado do ciclo 1 + premissas confirmadas; nenhuma leitura das tabelas vivas.
- Regras parametrizadas e versionadas com vigência e fonte legal; regra ausente → regime "não calculado" com pendência (nunca estimativa silenciosa).
- Reusar a stack do ciclo 1 (worker Python, Supabase com RLS por escritório, Next.js) e ampliar o Verify Gate `npm run verify`.
- `kb/` está PENDENTE DE REVISÃO; LC 224/2025 (aferição trimestral), regra da faixa 5 para ICMS/ISS e regime cumulativo de hospitais não foram conferidos na fonte primária — revisão contábil é dependência antes do uso no piloto.
- Amostras cobrem um único cliente comercial (Anexo I) e apenas 08/2026 completo; casos de serviços (Anexos III/V, Fator R) dependem de casos construídos.

### Out of Scope (Confirmed)

- Projeção, sensibilidade, ponto de virada, recomendação/parecer, fluxo de aprovação e PDF executivo (ciclo 3).
- Real anual por estimativa; remuneração de sócios (Lei 15.270/2025) e JCP; CBS/IBS.
- Tela de administração de regras; ICMS por NCM, DIFAL, MEI.
- Uso do PDF Econet (CONESP) como caso dourado (sem entradas).

## Session Summary

| Metric | Value |
|---|---:|
| Questions Asked | 5 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 6 |
| Validations Completed | 2 |

## Next Step

Execute o **SDD Define by RDD**.
