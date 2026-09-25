# DESIGN: Decisão Tributária (ciclo 3 do Planejamento Tributário)

> Technical design for implementing Decisão Tributária — projeção 2026 pelo motor, sensibilidade com ponto de virada, recomendação com aprovação do responsável técnico e PDF executivo imutável.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | DECISAO_TRIBUTARIA |
| **Date** | 2026-09-25 |
| **Author** | SDD Design by RDD |
| **BRAINSTORM** | `sdd/BRAINSTORM_DECISAO_TRIBUTARIA.md` |
| **DEFINE** | `sdd/DEFINE_DECISAO_TRIBUTARIA.md` |
| **UX REVIEW** | N/A |
| **LLM Prompts** | false |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
 Web (Next.js 16)                          Supabase (Postgres 17 + RLS + Storage)
 ┌───────────────────────────┐   RPC      ┌──────────────────────────────────────────┐
 │ /cases/[id]/planning       │──────────▶│ request_projection / submit / approve /   │
 │  premissas de projeção      │           │ return / request_report / admin RPCs      │
 │ /planning/projection/[id]   │◀── select │ projections, projection_lines (append)    │
 │  mensal · sensibilidade ·   │           │ recommendations (estado do fluxo)         │
 │  recomendação · fluxo       │           │ recommendation_events (append)            │
 │ /admin: limiar + resp. téc. │           │ office_members (+ responsável técnico)    │
 │ /api/reports/[id] (URL ass.)│           │ jobs (project, emit_report)               │
 └───────────────────────────┘           └───────────────┬──────────────────────────┘
                                                          │ fila (claim/lease)
                                           ┌──────────────▼──────────────────────────┐
                                           │ Worker Python                            │
                                           │  job project:                            │
                                           │   snapshot + premissas ─▶ Projetor ──┐    │
                                           │   (12 meses 2026, origem por mês)     │   │
                                           │                  SnapshotView sintética│   │
                                           │                         ▼              │   │
                                           │   Motor ciclo 2 (calculate) ◀──────────┘   │
                                           │                         ▼                  │
                                           │   Sensibilidade (grade + bisseção) ─▶ N×motor│
                                           │                         ▼                  │
                                           │   Recomendação (limiar, fatores, carga)    │
                                           │  job emit_report: ReportLab ─▶ PDF + SHA   │
                                           └──────────────┬──────────────────────────┘
   regras 2026 (versão 2026.1.0) ─────────────────────────┤
   parâmetros de decisão (rules/decisao.json, versão própria)┘      Storage: <office>/<case>/reports/<rec>.pdf
```

---

## Components

| Component | Purpose | Technology / Pattern | Inputs | Outputs | Dependencies |
|---|---|---|---|---|---|
| Parâmetros de decisão | Método de projeção, campos proporcionais, variáveis e intervalos da sensibilidade, faixas de robustez, limiar padrão, grupos de carga, textos de ressalva | JSON versionado com hash próprio (`rules/decisao.json`) | — | `DecisionParams` (versão, hash) | Rules Loader do ciclo 2 (mesmo padrão) |
| Projetor | Monta os 12 meses de 2026 com origem (realizado / estimado / projetado / orçamento) como conteúdo de snapshot sintético e as premissas derivadas por mês | Funções puras, `Decimal` | Snapshot homologado, premissas confirmadas, `DecisionParams`, multiplicadores de sensibilidade | Conteúdo sintético (mesmo schema do snapshot), premissas por mês, mapa de origem | SnapshotView, assumptions |
| Motor (ciclo 2) | Cálculo de Simples, Presumido e Real sobre a visão sintética | Reuso sem alteração (`engine/calculate.py`) | `SnapshotView`, `Assumptions`, `RuleSet` | `SimulationResult` | Regras 2026 |
| Sensibilidade | Ponto de virada por variável (grade + bisseção), limite jurídico, distância e robustez | Funções puras sobre Projetor + Motor | Base projetada, `DecisionParams` | Lista de `SensitivityResult` | Projetor, Motor, elegibilidade |
| Recomendação | Status (recomendado / inconclusivo / bloqueado), texto, 3 fatores, economia vs. atual e vs. segundo, carga consumo/renda/folha, custo de conformidade exibido | Funções puras | Resultado da projeção, sensibilidade, limiar do escritório, premissas | `RecommendationView` (JSON) | Motor, Sensibilidade |
| Orquestrador da projeção | Encadeia Projetor → Motor → Sensibilidade → Recomendação, calcula `result_hash` | Função pura `project()` | Snapshot, premissas, regras, parâmetros, limiar | `ProjectionResult` | Todos os anteriores |
| Relatório PDF | PDF executivo no formato SPTE + seções do PRD, byte a byte reprodutível | ReportLab 5 (`invariant=1`), platypus | Projeção, recomendação, eventos, responsável técnico, empresa | Bytes do PDF + SHA-256 | Projeção gravada |
| Jobs do worker | `project` (grava projeção + recomendação em rascunho) e `emit_report` (gera PDF, grava no Storage, marca emitida) | `Pipeline.handle`, fila existente | Jobs | Linhas no banco, objeto no Storage | db.py, storage.py |
| Banco | Tabelas, papel, RLS, RPCs do fluxo, gatilho de premissa alterada | Migration SQL + pgTAP | RPCs da web | Estados, auditoria | Ciclos 1 e 2 |
| Telas | Premissas de projeção, página da projeção (mensal, sensibilidade, recomendação, fluxo), admin (limiar e responsável técnico), download do PDF | Next.js 16 server components + server actions | Supabase (RLS) | UI, RPCs | Banco |

---

## Key Decisions

### Decision 1: Projeção como snapshot sintético lido pelo motor sem alteração

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-25 |
| **Source** | Brainstorm (Approach A) + evidência no código (`engine/*` lê dados só via `SnapshotView`) |

**Context:** A projeção precisa usar "as mesmas funções do motor" (DEFINE, MUST) e manter os goldens do ciclo 2 (AT-223). O motor lê PGDAS-D, folha, DRE e balancete somente por `SnapshotView` (`values`, `get`, `value`, `pgdas_series`, `activities`, `dre_accounts`, `balancete_accounts`, `complete_competences`).

**Choice:** O Projetor gera um **conteúdo de snapshot sintético** no mesmo schema de `homologate_case` (`files`, `values`) para jan–dez/2026: os quatro documentos por mês, com os `field_key` que o motor lê (receita, séries, atividades com tributos declarados, bases da folha, lucro da DRE, conta de Simples, ICMS). Cada valor sintético leva o campo `projecao` com `origem` e `base` e os meses realizados são copiados do snapshot homologado. As premissas por competência dos meses não realizados são derivadas pelo Projetor (origem `projecao`). O motor roda sobre `SnapshotView(conteudo_sintetico)` sem mudança de código.

**Rationale:** Zero divergência entre realizado e projetado; descontinuidades (faixa, Fator R, adicional, LC 224, sublimite) tratadas pelo próprio motor; nenhuma regressão possível no cálculo do ciclo 2.

**Alternatives Rejected:**
1. Refatorar o motor para uma abstração "fatos do mês" — alteraria o motor aprovado e exigiria revalidar os goldens.
2. Anualização/elasticidade (Approach B do Brainstorm) — rejeitada no Brainstorm.

**Consequences:**
- O Projetor precisa conhecer os `field_key` lidos pelo motor; um teste de contrato garante que o motor sobre o conteúdo sintético de jun–ago reproduz o golden `motor_202606_08`.
- Linhas da projeção herdam a memória do motor e ganham a origem do mês.

### Decision 2: Composição dos meses de 2026

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-25 |
| **Source** | DEFINE (Goals, A-201 a A-203) |

**Context:** Só há documentos completos de 06–08/2026; o PGDAS-D traz séries de receita e folha dos 12 meses anteriores e a RBAA (receita de 2025).

**Choice:**
- **Realizado:** competências completas do snapshot (06–08/2026), copiadas.
- **Estimado (jan–mai):** receita e folha das séries do PGDAS-D da competência completa mais recente que contém o mês; lucro antes de tributos, créditos de PIS/Cofins, ICMS/ISS, outras receitas e bases da folha pela **razão média sobre a receita** dos meses completos (A-201).
- **Projetado (set–dez):** média simples dos meses completos para receita, margem e folha; o valor confirmado em `projecao.receita`, `projecao.margem` ou `projecao.folha` substitui a média e marca a origem `orcamento`.
- **RBT12 dos meses estimados (A-203):** meses de 2025 ausentes nas séries (antes de 06/2025) recebem a diferença `RBAA declarada − soma dos meses de 2025 presentes`, distribuída igualmente; premissa marcada na memória.
- **Margem** = (lucro líquido da DRE + despesa de Simples da DRE) ÷ receita; na DRE sintética o lucro = receita × margem e a conta de Simples = 0, de modo que a reclassificação do Real (lucro + Simples − encargos − PIS/Cofins) permanece correta.

**Rationale:** Usa todos os dados declarados antes de estimar; mantém a reclassificação do Real consistente entre realizado e projetado.

**Alternatives Rejected:**
1. Exigir DRE/balancete de jan–mai — contraria A-201 validado.
2. Completar o RBT12 com a média da série — ignora a RBAA declarada, que fecha o total de 2025 exatamente.

**Consequences:**
- Presumido/Real de jan–mai dependem da premissa proporcional; o PDF lista essa ressalva.
- Trimestres T1–T4 de 2026 ficam completos na projeção (IRPJ/CSLL trimestrais sem parcial).

### Decision 3: Parâmetros de decisão em arquivo próprio, fora do hash das regras tributárias

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-25 |
| **Source** | Evidência (goldens do ciclo 2 fixam `rules_version` 2026.1.0) |

**Context:** Intervalos da sensibilidade, faixas de robustez e grupos de carga são política de decisão, não legislação. Incluí-los no manifesto de 2026 mudaria `rules_hash`/versão e invalidaria os goldens aprovados sem mudança de cálculo.

**Choice:** `services/worker/rules/decisao.json` com `versao` e hash próprios (`decision_version`, `decision_hash`), gravados em cada projeção. Conteúdo inicial:

| Chave | Valor inicial |
|---|---|
| `limiar_padrao` | 0.05 (fração do custo do vencedor) |
| `robustez` | robusta > 0.20; atenção 0.05–0.20; frágil < 0.05 (A-204) |
| `sensibilidade.receita` | multiplicador da receita anual 0.50–1.50 |
| `sensibilidade.margem` | margem antes de tributos 0.00–0.40 (absoluta) |
| `sensibilidade.folha_receita` | multiplicador da folha 0.50–2.00 |
| `sensibilidade.creditos` | multiplicador da base de créditos 0.00–2.00 |
| `sensibilidade.icms_iss` | multiplicador do ICMS/ISS no regime normal 0.00–2.00 |
| `busca` | grade de 11 pontos + bisseção até 0,1% do intervalo (máx. 12 iterações) |
| `carga` | consumo = PIS, Cofins, ICMS, ISS, IPI; renda = IRPJ, adicional, CSLL; folha = CPP, RAT, terceiros |
| `ressalvas` | textos fixos: regras de 2027 (Reforma), estimativa de jan–mai, custo de conformidade fora do ranking |

**Rationale:** Mantém a reprodutibilidade das simulações do ciclo 2 e torna a política versionada e auditável (A-205 fica ajustável por nova versão do arquivo).

**Alternatives Rejected:**
1. Parâmetros no manifesto de 2026 — muda `rules_hash` sem mudança tributária.
2. Parâmetros no código — sem versão nem hash gravados.

**Consequences:**
- A idempotência da projeção usa `(snapshot_sha256, assumptions_hash, rules_hash, decision_hash, threshold)`.

### Decision 4: Sensibilidade por grade + bisseção sobre o motor completo

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-25 |
| **Source** | DEFINE (AT-207, AT-208, AT-221) + KB (`encontrar-ponto-de-virada.md`) |

**Context:** O ponto de virada precisa respeitar descontinuidades e caber em 60 s.

**Choice:** Para cada variável, reconstruir a visão sintética com o multiplicador (ou margem absoluta) e rodar o motor em 11 pontos do intervalo; entre dois pontos em que o primeiro colocado (entre regimes rankeáveis) muda, bisseção até a precisão configurada. Se entre dois pontos o conjunto de regimes elegíveis muda, registrar **limite jurídico** (valor, regime afetado) em vez de virada. Distância = |virada − base| ÷ base; robustez pelas faixas. Sem troca no intervalo → "sem virada no intervalo".

**Rationale:** Estimativa de 5 variáveis × (11 + ≤ 12) ≈ 115 execuções; medido no ciclo 2 ≈ 40 ms para 3 meses → ≈ 0,15 s para 12 meses → ≈ 17 s, abaixo de 60 s.

**Alternatives Rejected:**
1. Derivada/elasticidade linear — erra perto de faixas.
2. Varredura fina sem bisseção — mais lenta e menos precisa.

**Consequences:**
- A sensibilidade não grava linhas de memória por ponto (só o resultado por variável); a projeção base grava a memória completa.

### Decision 5: Tabelas e máquina de estados da recomendação

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-25 |
| **Source** | DEFINE (AT-209 a AT-219) |

**Context:** Projeção é imutável; o fluxo de aprovação muda de estado; PDF emitido é imutável.

**Choice:**
- `projections` (append-only): hashes, `status` (done/failed), `result` (resumo por regime/mês), `sensitivity` (JSON por variável), `recommendation` (JSON calculado: status, texto, fatores, economia, carga, conformidade, bloqueios), `result_hash`, `decision_version`, `decision_hash`, `threshold`.
- `projection_lines` (append-only): linhas do motor + `origem` do mês.
- `recommendations` (estado): `projection_id`, `status` em `rascunho → em_revisao → aprovada → emitida`, devolução volta a `rascunho`; `elaborated_by` (quem pediu a projeção), `approved_by`, `approved_at`, `pdf_path`, `pdf_sha256`, `emitted_at`. Linha `emitida` é imutável (trigger).
- `recommendation_events` (append-only): `submitted`, `returned` (comentário ≥ 5), `approved`, `emitted`, `reset_by_assumption`.
- Gatilho em `assumptions`: ao confirmar premissa de um caso, recomendações `em_revisao`/`aprovada` desse caso voltam a `rascunho` com evento `reset_by_assumption` (AT-219). Emitidas não mudam.
- Envio para revisão recusado quando `projections.recommendation.status = 'bloqueado'` (AT-211).

**Rationale:** Separa o cálculo imutável do estado do fluxo; toda transição é auditada.

**Alternatives Rejected:**
1. Estado dentro de `projections` — quebraria o append-only.
2. Tabela separada para sensibilidade — a sensibilidade é imutável e 1:1 com a projeção; JSON basta.

**Consequences:**
- Nova projeção cria nova recomendação em rascunho; recomendações antigas permanecem no histórico.

### Decision 6: Responsável técnico em `office_members` e limiar em `offices.settings`

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-25 |
| **Source** | DEFINE (Clarification 3, AT-214 a AT-216) |

**Context:** O admin marca responsáveis técnicos (nome + CRC) e define o limiar; o responsável técnico pode elaborar, mas não aprova a própria elaboração.

**Choice:** Colunas `is_technical_responsible boolean default false`, `professional_name text`, `crc text` em `office_members`; RPC `set_technical_responsible(p_office, p_user, p_flag, p_name, p_crc)` (somente admin; nome e CRC obrigatórios quando `p_flag`). Limiar em `offices.settings ->> 'decision_threshold'` (0 < x < 1, padrão 0.05) por RPC `set_decision_threshold` (somente admin). Função `is_technical_responsible(office)`. `approve_recommendation` exige responsável técnico e `auth.uid() <> elaborated_by`.

**Rationale:** Reusa tenancy e auditoria existentes; o enum `member_role` permanece `admin | analyst`.

**Alternatives Rejected:**
1. Novo valor no enum `member_role` — um membro não pode ser admin e responsável técnico ao mesmo tempo.
2. Tabela separada de responsáveis — duplicaria a associação membro/escritório.

**Consequences:**
- A página de admin ganha a gestão do responsável técnico e do limiar.

### Decision 7: PDF com ReportLab em modo invariant

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-25 |
| **Source** | Clarificação técnica do usuário (opção a) |

**Context:** O PDF precisa de tabelas densas (formato SPTE), rodar no Windows (Python 3.14) e no Docker (Python 3.12) e ter SHA-256 reprodutível.

**Choice:** `reportlab>=5` (wheel puro; `pip install --dry-run` confirmou 5.0.1 no Python 3.14 local) com `rl_config.invariant = 1` e fontes base (Helvetica); data de emissão vinda da aprovação (não do relógio) para reprodutibilidade.

**Rationale:** Sem dependências nativas; mesma entrada → mesmos bytes → hash testável.

**Alternatives Rejected:**
1. WeasyPrint — exige Pango/GTK no Windows; saída não reprodutível.
2. fpdf2 — tabelas longas e quebras de página mais trabalhosas.

**Consequences:**
- Nova dependência em `pyproject.toml` e na imagem do worker.

### Decision 8: Premissas de projeção e conformidade no catálogo existente

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-25 |
| **Source** | DEFINE (AT-203, AT-204, SHOULD conformidade) |

**Context:** Orçamento e custo de conformidade precisam de sugestão, confirmação e justificativa ao alterar — regra já implementada em `confirm_assumption`.

**Choice:** `suggest()` passa a gerar, para cada mês de 2026 posterior à última competência completa, `projecao.receita`, `projecao.margem` e `projecao.folha` (grupo `projecao`, sugerido = média dos meses completos), e `conformidade.custo_anual` com escopo `regime:SIMPLES|PRESUMIDO|REAL` (grupo `conformidade`, sugerido 0.00). Confirmação e justificativa reutilizam `confirm_assumption` e `assumption_value_ok` (decimal/percent).

**Rationale:** Sem nova UI de formulário nem nova regra de validação; premissas pendentes bloqueiam como no ciclo 2 (AT-211).

**Alternatives Rejected:**
1. Tabela própria de orçamento — duplicaria confirmação, justificativa e auditoria.

**Consequences:**
- O número de premissas do caso cresce (4 meses × 3 + 3 = 15 na amostra); goldens do ciclo 2 não mudam (usam só as chaves que já liam).

---

## File Manifest

| # | File | Action | Purpose | Agent / Owner | Dependencies |
|---:|---|---|---|---|---|
| 1 | `services/worker/rules/decisao.json` | Create | Parâmetros de decisão versionados (Decision 3) | (general) | None |
| 2 | `services/worker/src/worker/engine/decision_params.py` | Create | `DecisionParams`, `load_decision_params()` com versão e hash (CRLF normalizado) | (general) | 1 |
| 3 | `services/worker/src/worker/engine/assumptions.py` | Modify | Sugestões `projecao.*` e `conformidade.custo_anual` (Decision 8) | (general) | None |
| 4 | `services/worker/src/worker/engine/projection.py` | Create | Projetor: conteúdo sintético jan–dez/2026, origem por mês, premissas derivadas, multiplicadores (Decisions 1–2) | (general) | 2, 3 |
| 5 | `services/worker/src/worker/engine/sensitivity.py` | Create | Grade + bisseção, limite jurídico, distância, robustez (Decision 4) | (general) | 4 |
| 6 | `services/worker/src/worker/engine/recommendation.py` | Create | Status, texto, 3 fatores, economia, carga, conformidade, bloqueios | (general) | 2 |
| 7 | `services/worker/src/worker/engine/decision.py` | Create | Orquestrador `project()` e `ProjectionResult` com `result_hash` | (general) | 4, 5, 6 |
| 8 | `services/worker/src/worker/report_pdf.py` | Create | PDF executivo ReportLab invariant (formato SPTE + seções do PRD) | (general) | 7 |
| 9 | `services/worker/pyproject.toml` | Modify | Dependência `reportlab>=5` | (general) | None |
| 10 | `services/worker/Dockerfile` | Modify | Copiar `rules/decisao.json` (já coberto por `COPY rules`) e instalar a nova dependência via `pip install .` | (general) | 9 |
| 11 | `services/worker/src/worker/config.py` | Modify | `decision_params_path` (env `DECISION_PARAMS`, padrão `rules/decisao.json`) | (general) | 1 |
| 12 | `services/worker/src/worker/db.py` | Modify | Ler limiar e responsável técnico, gravar projeção/linhas/recomendação, ler dados do PDF, marcar emissão | (general) | 13 |
| 13 | `supabase/migrations/20260925000003_decisao.sql` | Create | Jobs `project`/`emit_report`; responsável técnico; limiar; tabelas; RLS; RPCs; gatilho de premissa; política de Storage `reports/` | (general) | None |
| 14 | `services/worker/src/worker/pipeline.py` | Modify | Handlers `project` e `emit_report` | (general) | 7, 8, 12 |
| 15 | `supabase/tests/decisao.test.sql` | Create | pgTAP: papel, limiar, segregação, estados, devolução, reset por premissa, emitida imutável, RLS, Storage | (general) | 13 |
| 16 | `services/worker/tests/test_decisao_projection.py` | Create | Origem por mês, estimativa jan–mai, orçamento, RBT12 com RBAA, contrato jun–ago = golden `motor_202606_08`, idempotência | (general) | 4, 7 |
| 17 | `services/worker/tests/test_decisao_sensitivity.py` | Create | Virada por bisseção, "sem virada", limite jurídico, robustez | (general) | 5 |
| 18 | `services/worker/tests/test_decisao_recommendation.py` | Create | Recomendado, inconclusivo, bloqueado, inelegível fora do ranking, conformidade fora do ranking, fatores, economia, carga | (general) | 6 |
| 19 | `services/worker/tests/test_report_pdf.py` | Create | Seções obrigatórias no texto extraído, SHA-256 reprodutível | (general) | 8 |
| 20 | `services/worker/tests/test_decisao_pipeline.py` | Create | Integração com Postgres: projetar → submeter → aprovar → emitir; ≤ 60 s; reset por premissa; PDF inalterado | (general) | 14, 13 |
| 21 | `services/worker/tests/golden/decisao_2026.json` | Create | Golden da Projeção 2026 aprovado pelo usuário no build (totais por regime e mês, status, viradas) | (general) | 7 |
| 22 | `services/worker/tests/test_decisao_golden.py` | Create | Reproduz o golden aprovado (AT-222) | (general) | 21 |
| 23 | `services/worker/tests/conftest.py` | Modify | Fixtures `decision_params`, `projection_assumptions`; limpeza das novas tabelas | (general) | 2 |
| 24 | `apps/web/src/lib/database.types.ts` | Modify | Regenerar tipos (`npm run db:types`) | (general) | 13 |
| 25 | `apps/web/src/lib/schemas.ts` | Modify | `returnRecommendationSchema` (comentário ≥ 5), `technicalResponsibleSchema` (nome, CRC), `thresholdSchema` (0–1) | (general) | None |
| 26 | `apps/web/src/lib/schemas.test.ts` | Modify | Testes dos schemas novos | (general) | 25 |
| 27 | `apps/web/src/lib/format.ts` | Modify | Rótulos de origem, estados da recomendação, robustez, grupos `projecao`/`conformidade`, meses | (general) | None |
| 28 | `apps/web/src/app/(app)/cases/[id]/planning/projection/actions.ts` | Create | Server actions: pedir projeção, submeter, aprovar, devolver, pedir emissão | (general) | 24, 25 |
| 29 | `apps/web/src/app/(app)/cases/[id]/planning/projection/[projId]/page.tsx` | Create | Página da projeção: mensal por regime, sensibilidade, recomendação, fluxo, download | (general) | 28, 30, 31, 32 |
| 30 | `apps/web/src/components/ProjectionTable.tsx` | Create | Tributos × jan–dez por regime com origem do mês e observações (formato SPTE) | (general) | 27 |
| 31 | `apps/web/src/components/SensitivityTable.tsx` | Create | Variável, base, virada/limite jurídico, distância, robustez | (general) | 27 |
| 32 | `apps/web/src/components/RecommendationPanel.tsx` | Create | Status, texto, fatores, economia, carga, conformidade, ressalvas, eventos e botões do fluxo por papel | (general) | 27, 28 |
| 33 | `apps/web/src/app/(app)/cases/[id]/planning/page.tsx` | Modify | Botão "Projeção 2026" e lista de projeções/recomendações | (general) | 28 |
| 34 | `apps/web/src/app/(app)/admin/actions.ts` | Modify | Actions de limiar e responsável técnico | (general) | 24, 25 |
| 35 | `apps/web/src/app/(app)/admin/page.tsx` | Modify | Formulário de limiar e marcação de responsável técnico (nome, CRC) | (general) | 34 |
| 36 | `apps/web/src/app/api/reports/[id]/route.ts` | Create | Redirect para URL assinada do PDF emitido (RLS) | (general) | 24 |
| 37 | `scripts/verify.mjs` | Modify | Rótulos do gate incluindo o ciclo 3 (comandos inalterados) | (general) | 15, 20 |
| 38 | `README.md` | Modify | Seção do ciclo 3: projeção, sensibilidade, recomendação, fluxo, PDF | (general) | 14 |

**Total Files:** 38

### Agent Assignment Rationale

| Agent / Owner | Files Assigned | Why |
|---|---|---|
| (general) | 1–38 | Nenhum catálogo de agentes especializados no projeto; mesmo executor dos ciclos 1 e 2 |

**Agent Discovery:** Not available

---

## Code Patterns

### Pattern 1: Projetor gerando visão sintética para o motor

```python
@dataclass(frozen=True)
class Levers:
    """Multiplicadores da sensibilidade; 1 = cenário base."""
    receita: Decimal = Decimal("1")
    margem: Decimal | None = None          # margem absoluta; None = base
    folha: Decimal = Decimal("1")
    creditos: Decimal = Decimal("1")
    icms_iss: Decimal = Decimal("1")


@dataclass(frozen=True)
class ProjectedCase:
    content: dict                 # mesmo schema do snapshot homologado (files, values)
    assumptions: list[dict]       # confirmadas (realizado) + derivadas (origem "projecao")
    origins: dict[str, str]       # "2026-01" → estimado | realizado | projetado | orcamento


def build_projection(view: SnapshotView, confirmed: Assumptions, params: DecisionParams,
                     levers: Levers = Levers(), year: int = 2026) -> ProjectedCase: ...
```

### Pattern 2: Orquestração e hash

```python
def project(view: SnapshotView, confirmed: Assumptions, rules: RuleSet, params: DecisionParams,
            threshold: Decimal) -> ProjectionResult:
    base = build_projection(view, confirmed, params)
    sim = calculate(SnapshotView(base.content), Assumptions(base.assumptions), rules)
    sens = run_sensitivity(view, confirmed, rules, params, sim)
    rec = recommend(sim, sens, confirmed, params, threshold, blockers=blockers(view, confirmed))
    payload = {"sim": sim.summary(), "sens": [s.as_dict() for s in sens], "rec": rec.as_dict(),
               "origins": base.origins, "decision_hash": params.hash}
    return ProjectionResult(sim, sens, rec, base.origins, canonical_hash(payload))
```

### Pattern 3: RPC de aprovação com segregação

```sql
create or replace function public.approve_recommendation(p_id uuid)
returns void language plpgsql security definer set search_path = public as $$
declare v public.recommendations%rowtype;
begin
  select * into v from public.recommendations where id = p_id for update;
  if not found or not public.is_member(v.office_id) then
    raise exception 'Recomendação não encontrada' using errcode = 'P0002';
  end if;
  if not public.is_technical_responsible(v.office_id) then
    raise exception 'Somente o responsável técnico aprova' using errcode = '42501';
  end if;
  if v.elaborated_by = auth.uid() then
    raise exception 'Quem elaborou não pode aprovar' using errcode = '42501';
  end if;
  if v.status <> 'em_revisao' then
    raise exception 'Recomendação não está em revisão' using errcode = 'P0001';
  end if;
  update public.recommendations set status = 'aprovada', approved_by = auth.uid(), approved_at = now()
   where id = p_id;
  insert into public.recommendation_events (office_id, recommendation_id, event, actor)
  values (v.office_id, p_id, 'approved', auth.uid());
end $$;
```

### Pattern 4: PDF reprodutível

```python
from reportlab import rl_config
rl_config.invariant = 1          # sem timestamp/ID aleatório no PDF

def build_recommendation_pdf(data: ReportData) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), title=data.title, author=data.office_name,
                            creator="Planejamento Tributário", subject="Exercício " + str(data.year))
    doc.build(story_for(data))
    return buf.getvalue()
```

---

## Data Flow

```text
1. Premissas de projeção (worker, job suggest_assumptions já existente)
   suggest() acrescenta projecao.receita, projecao.margem e projecao.folha por mês set–dez e conformidade.custo_anual por regime
   │  analista confirma ou altera com justificativa (confirm_assumption; AT-204)
   ▼
2. request_projection(case)  [RPC]
   exige dossiê homologado, premissas geradas e nenhuma pendente → job "project" (chave com txid)
   │
   ▼
3. Worker: project
   snapshot + premissas + regras 2026 + decisao.json + limiar do escritório
   ├─ idempotência: (snapshot_sha, assumptions_hash, rules_hash, decision_hash, limiar) já existe → reutiliza
   ├─ Projetor → conteúdo sintético jan–dez com origem por mês
   ├─ Motor (calculate) → resultado por regime/mês + linhas de memória
   ├─ Sensibilidade → 5 variáveis (virada / sem virada / limite jurídico, distância, robustez)
   ├─ Recomendação → status, texto, fatores, economia, carga, conformidade, bloqueios
   └─ grava projections + projection_lines (append-only) e recommendations(status=rascunho, elaborated_by=solicitante)
   │  falha inesperada → retry do job (até 3); dado crítico ausente → projeção gravada com recomendação "bloqueado"
   ▼
4. Web: página da projeção (prévia "incompleta" quando bloqueado)
   │  submit_recommendation → em_revisao (recusado se bloqueado)
   ▼
5. Responsável técnico: approve_recommendation (segregação) ou return_recommendation(comentário) → rascunho
   │  premissa confirmada no caso → gatilho: em_revisao/aprovada → rascunho (evento reset_by_assumption)
   ▼
6. request_report(rec)  [RPC] → exige aprovada → job "emit_report"
   ▼
7. Worker: emit_report → ReportLab (invariant) → <office>/<case>/reports/<rec>.pdf + SHA-256
   → recommendations: status=emitida, pdf_path, pdf_sha256, emitted_at; evento emitted (linha imutável)
   ▼
8. /api/reports/[id] → URL assinada (60 s) somente para membros do escritório
```

---

## Integration Points

| External System | Integration Type | Authentication | Direction | Failure / Retry |
|---|---|---|---|---|
| Supabase Postgres | DB (psycopg no worker; RPC/select na web) | Service role no worker; JWT + RLS na web | bidirectional | Falha do job → retry com backoff (fila existente, 3 tentativas); RPC devolve erro de negócio (P0001/P0002/42501) à tela |
| Supabase Storage (bucket `documents`) | SDK/HTTP (worker grava; web lê por URL assinada) | Service role no worker; JWT na web | out (worker) / in (web) | Falha de upload → job em retry; recomendação só vira `emitida` após upload e hash gravados na mesma transação lógica do job |

---

## Testing Strategy

| Test Type | Scope / Requirement | Files | Tools | Pass Signal |
|---|---|---|---|---|
| Unit | Projetor: origem por mês, jan–mai estimado, orçamento, RBT12 com RBAA, contrato jun–ago (AT-201 a AT-203, AT-206, AT-223) | `services/worker/tests/test_decisao_projection.py` | pytest | Igualdade exata com `motor_202606_08` e valores esperados |
| Unit | Sensibilidade: virada, sem virada, limite jurídico, robustez (AT-207, AT-208) | `services/worker/tests/test_decisao_sensitivity.py` | pytest | Casos construídos com virada conhecida |
| Unit | Recomendação: estados, fatores, economia, carga, conformidade (AT-209 a AT-213) | `services/worker/tests/test_decisao_recommendation.py` | pytest | Asserções de status e valores |
| Unit | PDF: seções e hash reprodutível (AT-218) | `services/worker/tests/test_report_pdf.py` | pytest + pdfplumber | Texto contém as seções; dois builds → mesmo SHA-256 |
| Unit (golden) | Projeção 2026 da amostra (AT-222) | `services/worker/tests/test_decisao_golden.py`, `golden/decisao_2026.json` | pytest | Igualdade exata com golden aprovado |
| Integration | Fluxo completo no Postgres, ≤ 60 s, reset por premissa, PDF inalterado (AT-205, AT-219, AT-221) | `services/worker/tests/test_decisao_pipeline.py` | pytest + Postgres local | Estados e tempos esperados |
| Database | Papel, limiar, segregação, devolução, RLS, Storage, emitida imutável (AT-214 a AT-217, AT-220) | `supabase/tests/decisao.test.sql` | pgTAP (`npx supabase test db`) | Todos os asserts ok |
| Web | Schemas de devolução, responsável técnico e limiar | `apps/web/src/lib/schemas.test.ts` | vitest | Testes passam |
| E2E / Verify Gate | Gate do DEFINE | `scripts/verify.mjs` | `npm run verify` | exit 0 |

---

## Error Handling

| Error Type | Detection | Handling Strategy | Retry? | Observability |
|---|---|---|---|---|
| Premissa pendente ao pedir projeção | `request_projection` conta pendentes | RPC recusa listando as pendentes | No | Mensagem na tela |
| Dado crítico ausente (sem competência completa, série do PGDAS-D incompleta) | Projetor/`blockers()` | Grava projeção com recomendação `bloqueado`; prévia "incompleta"; envio recusado | No | Log `projection.blocked` com códigos |
| Regime inelegível ou "não calculado" | Resultado do motor | Fora do ranking com motivo e regra | No | Campo `pending`/`eligibility` no resultado |
| Aprovação indevida (não RT ou própria elaboração) | `approve_recommendation` | `42501` com mensagem | No | Auditoria da tentativa não gravada; erro na tela |
| Transição inválida (ex.: aprovar em rascunho, emitir não aprovada) | Checagem de estado nas RPCs | `P0001` | No | Erro na tela |
| Falha inesperada no worker (cálculo, PDF, upload) | Exceção no handler | Rollback + retry do job (backoff, 3 tentativas); após o limite, job `failed` | Yes | Log `job.retry`/`job.failed` com código |
| Pedido repetido com mesmas entradas | Unicidade dos hashes | Reutiliza projeção; nenhuma duplicação | N/A | Log `projection.reused` |
| Tempo acima do alvo | `duration_ms` gravado | Teste de integração falha acima de 60 s | N/A | `duration_ms` por projeção |

---

## Configuration

| Config Key | Type | Source / Default | Sensitive? | Description |
|---|---|---|---|---|
| `DECISION_PARAMS` | path | env; padrão `services/worker/rules/decisao.json` (imagem: `/app/rules/decisao.json`) | No | Parâmetros de decisão versionados |
| `offices.settings.decision_threshold` | numeric (0–1) | banco; padrão 0.05 quando ausente | No | Limiar de inconclusivo por escritório |
| `RULES_DIR`, `RULES_EXERCISE` | path, string | existentes (ciclo 2) | No | Regras tributárias 2026 |
| `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, `SUPABASE_URL` | secret/url | env existentes | Yes | Acesso do worker (somente servidor) |

---

## Security Considerations

- Aprovação restrita a responsável técnico do escritório e diferente de quem elaborou, validada no banco (RPC `security definer`), não só na tela.
- Tabelas novas com RLS select-only para membros; escrita somente por RPC ou worker; `projections`, `projection_lines` e `recommendation_events` append-only por trigger; recomendação `emitida` imutável.
- PDFs em `<office>/<case>/reports/`, com política de Storage que impede escrita por usuários (mesmo padrão de `exports/` e `simulations/`) e leitura por URL assinada de 60 s.
- CRC e nome profissional são dados do membro, editáveis só pelo admin; logs registram apenas IDs e códigos (sem valores do cliente).
- O PDF contém razão social e CNPJ da empresa (dados da pessoa jurídica) e nenhum CPF/RG; as amostras continuam fora do Git.
- `SUPABASE_SERVICE_ROLE_KEY` somente no worker e em `admin.ts`, como nos ciclos anteriores.

---

## Observability

| Aspect | Implementation | Signal / Why |
|---|---|---|
| Logging | JSON estruturado no worker: `projection.done`, `projection.reused`, `projection.blocked`, `report.emitted`, com IDs, status, `duration_ms`, contagem de execuções da sensibilidade | Diagnóstico de fluxo e desempenho sem dados sensíveis |
| Metrics | `duration_ms` gravado em `projections`; número de execuções do motor na sensibilidade no resultado | AT-221 (≤ 60 s) |
| Tracing | N/A | Um job por projeção; logs com `job_id` bastam |

---

## Requirements Traceability

| Requirement / AT | Design Element | Test / Gate |
|---|---|---|
| AT-201, AT-202, AT-203 | Projetor (Decisions 1–2), premissas `projecao.*` (Decision 8) | `test_decisao_projection.py` |
| AT-204 | `confirm_assumption` reutilizado | `test_decisao_projection.py`, pgTAP do ciclo 2 |
| AT-205 | Unicidade de hashes em `projections` | `test_decisao_pipeline.py` |
| AT-206 | Motor sobre visão sintética (sublimite, teto, LC 224, R$ 78 mi) | `test_decisao_projection.py` |
| AT-207, AT-208 | Sensibilidade (Decision 4) | `test_decisao_sensitivity.py` |
| AT-209 a AT-213 | Recomendação | `test_decisao_recommendation.py` |
| AT-214 a AT-217 | Decision 5–6, RPCs | `decisao.test.sql` |
| AT-218 | Relatório PDF (Decision 7) | `test_report_pdf.py`, `test_decisao_pipeline.py` |
| AT-219 | Gatilho em `assumptions` | `decisao.test.sql`, `test_decisao_pipeline.py` |
| AT-220 | RLS e Storage | `decisao.test.sql` |
| AT-221 | Sensibilidade dimensionada (Decision 4), `duration_ms` | `test_decisao_pipeline.py` |
| AT-222 | Golden `decisao_2026.json` | `test_decisao_golden.py` |
| AT-223 | Motor inalterado (Decision 1) | `test_engine_calculate.py` (goldens do ciclo 2) |
| Verify Gate | `npm run verify` | exit 0 |

---

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual Risk |
|---|---|---|---|
| Visão sintética omitir um `field_key` lido pelo motor | Cálculo projetado incorreto | Teste de contrato: conteúdo sintético de jun–ago reproduz `motor_202606_08` exatamente | Baixo |
| Estimativa proporcional de jan–mai distante da realidade | Presumido/Real de jan–mai imprecisos | Premissa marcada na memória e no PDF; orçamento não cobre jan–mai, então a ressalva é obrigatória | Médio |
| Sensibilidade acima de 60 s em casos maiores | AT-221 | Grade de 11 pontos + bisseção limitada; `duration_ms` medido no teste | Baixo |
| Intervalos da sensibilidade insuficientes (A-205) | "Sem virada" onde haveria virada | Intervalos em `decisao.json` versionado; ajuste por nova versão | Médio |
| Recomendação da amostra sair inconclusiva | Golden com status inconclusivo | Esperado pelo Brainstorm (≈ 3% < 5%); golden aprovado pelo usuário registra o status | Baixo |
| Novas premissas aumentarem o trabalho de confirmação | Atrito na tela | Sugestões preenchidas pela média; "Confirmar sugerido" existente | Baixo |

---

## Advisor Ledger

None — no formal external design review.

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-09-25 | SDD Design by RDD | Initial version |

---

## Next Step

Execute o **SDD Build by RDD**.
