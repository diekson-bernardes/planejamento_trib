# BUILD REPORT: Motor Tributário (ciclo 2)

> Implementation report for Motor Tributário — elegibilidade e cálculo comparativo de Simples Nacional, Lucro Presumido e Lucro Real sobre o snapshot homologado do ciclo 1.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | MOTOR_TRIBUTARIO |
| **Date** | 2026-09-25 |
| **Author** | SDD Build by RDD |
| **BRAINSTORM** | `sdd/BRAINSTORM_MOTOR_TRIBUTARIO.md` |
| **DEFINE** | `sdd/DEFINE_MOTOR_TRIBUTARIO.md` |
| **DESIGN** | `sdd/DESIGN_MOTOR_TRIBUTARIO.md` |
| **Status** | Complete |

---

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 49 (File Manifest do DESIGN) |
| Cross-file coupling | High — `Line`, `RuleSet`, `SnapshotView` e `Assumptions` são compartilhados por todos os motores; hashes (snapshot/premissas/regras) ligam worker, banco e web |
| Security surface | Migration com RLS, RPCs `security definer`, política de Storage e rota de URL assinada |
| LLM prompt items | None (`LLM Prompts: false`) |
| Independent volume | Baixo — os motores dependem de regras, snapshot, premissas e encargos na mesma ordem |
| Context-rot risk | Médio (49 itens); mitigado por testes por módulo e caso dourado |
| Runtime capabilities | default disponível; ralph/briefs não recomendados por acoplamento e superfície de segurança |

**Recommendation:** default — alto acoplamento entre os módulos do motor e itens de segurança (RLS/RPC/Storage) que não devem ir a workers isolados.

**User decision:** default (commit do ciclo 1 e nova branch `feat/motor-tributario` antes da primeira alteração).

**Pre-build review:** No — o usuário escolheu revisão somente após o build.

---

## Summary

| Metric | Value |
|---|---|
| **Tasks Completed** | 49/49 |
| **Files Created** | 37 |
| **Files Modified** | 14 (12 do manifest + 2 fora do manifest, ver Drift) |
| **Files Deleted** | 0 |
| **Verification Commands Run** | 14 (pytest por módulo, pytest completo, pgTAP, typecheck, vitest, `npm run verify` ×3, `next build` ×2, build da imagem Docker, smoke E2E ×2) |
| **Verify Gate** | Green |
| **Execution Mode** | default |

---

## Task Execution

| # | Manifest ID | Task | Executor | Status | Verification | Evidence |
|---:|---:|---|---|---|---|---|
| 1 | 1 | Create migration `20260925000001_motor.sql` (tabelas, RLS, RPCs, append-only, validação de tipo de premissa) | direct | Complete | `npx supabase test db` | 63 asserções PASS (22 em motor.test.sql) |
| 2 | 2 | Create `supabase/tests/motor.test.sql` | direct | Complete | `npx supabase test db` | PASS |
| 3 | 3–9 | Create regras `rules/2026/*.json` (manifest 2026.1.0) | direct | Complete | `pytest tests/test_engine_rules.py` | carga, repartições somando 1, hash estável (normaliza CRLF) |
| 4 | 10–11 | Modify `config.py` e `Dockerfile` (`RULES_DIR`) | direct | Complete | build da imagem + carga das regras no contêiner | mesmo `rules_hash` no contêiner |
| 5 | 12–16 | Create `engine/__init__`, `memory`, `rules`, `snapshot`, `activities` | direct | Complete | `pytest tests/test_engine_*.py` | PASS |
| 6 | 17 | Create `engine/assumptions.py` | direct | Complete | `pytest tests/test_engine_payroll_assumptions.py` | sugestões com origem; regeneração respeita perfis confirmados |
| 7 | 18–19 | Create `engine/eligibility.py`, `engine/payroll.py` | direct | Complete | `pytest tests/test_engine_eligibility.py tests/test_engine_payroll_assumptions.py` | PASS |
| 8 | 20 | Create `engine/simples.py` | direct | Complete | `pytest tests/test_engine_simples.py` | DAS 06/07/08-2026 = PGDAS-D ao centavo |
| 9 | 21 | Create `engine/presumido.py` | direct | Complete | `pytest tests/test_engine_presumido.py` | golden KB 54.570,00; LC 224; trimestre parcial |
| 10 | 22 | Create `engine/real.py` | direct | Complete | `pytest tests/test_engine_real.py` | golden KB 43.980,00; trava 30%; cumulativo; saldo credor |
| 11 | 23 | Create `engine/calculate.py` | direct | Complete | `pytest tests/test_engine_calculate.py` | golden 08/2026 aprovado reproduzido |
| 12 | 24–26 | Modify `db.py`, `export_xlsx.py`, `pipeline.py` | direct | Complete | `pytest tests/test_motor_pipeline.py` | fluxo real com Postgres; XLSX assinado `PK` |
| 13 | 27–36 | Modify `conftest.py`; create testes e `golden/motor_202608.json` | direct | Complete | `pytest tests/` | 127 passed |
| 14 | 37–40 | Modify `database.types.ts`, `schemas.ts`, `schemas.test.ts`, `format.ts` | direct | Complete | `npm run typecheck`, `vitest` | 14 testes PASS |
| 15 | 41–48 | Create/modify telas de planejamento, componentes e rota de export | direct | Complete | `next build` + smoke HTTP autenticado | páginas 200; export 307 |
| 16 | 49 | Modify `README.md` (seção do motor) | direct | Complete | revisão | seção presente |

---

## Files Changed

| File | Action | Manifest ID | Verified | Notes |
|---|---|---:|---|---|
| `supabase/migrations/20260925000001_motor.sql` | Create | 1 | Yes | inclui `assumption_value_ok` e chave de sugestão com `txid_current()` (revisão pós-build) |
| `supabase/tests/motor.test.sql` | Create | 2 | Yes | 22 asserções |
| `services/worker/rules/2026/manifest.json` | Create | 3 | Yes | versão 2026.1.0 |
| `services/worker/rules/2026/simples.json` | Create | 4 | Yes | Anexos I–V transcritos do DOU de 28/10/2016 (`verificado: true`) |
| `services/worker/rules/2026/presumido.json` | Create | 5 | Yes | LC 224 `verificado: false` (A-002) |
| `services/worker/rules/2026/real.json` | Create | 6 | Yes | |
| `services/worker/rules/2026/encargos.json` | Create | 7 | Yes | |
| `services/worker/rules/2026/elegibilidade.json` | Create | 8 | Yes | |
| `services/worker/rules/2026/atividades.json` | Create | 9 | Yes | |
| `services/worker/src/worker/config.py` | Modify | 10 | Yes | |
| `services/worker/Dockerfile` | Modify | 11 | Yes | |
| `services/worker/src/worker/engine/__init__.py` | Create | 12 | Yes | |
| `services/worker/src/worker/engine/memory.py` | Create | 13 | Yes | |
| `services/worker/src/worker/engine/rules.py` | Create | 14 | Yes | |
| `services/worker/src/worker/engine/snapshot.py` | Create | 15 | Yes | chave de atividade inclui tributos declarados zero |
| `services/worker/src/worker/engine/activities.py` | Create | 16 | Yes | |
| `services/worker/src/worker/engine/assumptions.py` | Create | 17 | Yes | |
| `services/worker/src/worker/engine/eligibility.py` | Create | 18 | Yes | |
| `services/worker/src/worker/engine/payroll.py` | Create | 19 | Yes | |
| `services/worker/src/worker/engine/simples.py` | Create | 20 | Yes | |
| `services/worker/src/worker/engine/presumido.py` | Create | 21 | Yes | |
| `services/worker/src/worker/engine/real.py` | Create | 22 | Yes | |
| `services/worker/src/worker/engine/calculate.py` | Create | 23 | Yes | |
| `services/worker/src/worker/db.py` | Modify | 24 | Yes | regeneração remove premissas que deixaram de ser sugeridas |
| `services/worker/src/worker/export_xlsx.py` | Modify | 25 | Yes | |
| `services/worker/src/worker/pipeline.py` | Modify | 26 | Yes | |
| `services/worker/tests/conftest.py` | Modify | 27 | Yes | amostra da folha renomeada para `2.Resumo da Folha 08.pdf` |
| `services/worker/tests/test_engine_rules.py` | Create | 28 | Yes | |
| `services/worker/tests/test_engine_simples.py` | Create | 29 | Yes | |
| `services/worker/tests/test_engine_presumido.py` | Create | 30 | Yes | |
| `services/worker/tests/test_engine_real.py` | Create | 31 | Yes | |
| `services/worker/tests/test_engine_eligibility.py` | Create | 32 | Yes | |
| `services/worker/tests/test_engine_payroll_assumptions.py` | Create | 33 | Yes | |
| `services/worker/tests/test_engine_calculate.py` | Create | 34 | Yes | |
| `services/worker/tests/golden/motor_202608.json` | Create | 35 | Yes | aprovado pelo responsável de negócio em 2026-09-25 |
| `services/worker/tests/test_motor_pipeline.py` | Create | 36 | Yes | |
| `apps/web/src/lib/database.types.ts` | Modify | 37 | Yes | regenerado |
| `apps/web/src/lib/schemas.ts` | Modify | 38 | Yes | |
| `apps/web/src/lib/schemas.test.ts` | Modify | 39 | Yes | |
| `apps/web/src/lib/format.ts` | Modify | 40 | Yes | |
| `apps/web/src/app/(app)/cases/[id]/planning/actions.ts` | Create | 41 | Yes | |
| `apps/web/src/components/AssumptionForm.tsx` | Create | 42 | Yes | |
| `apps/web/src/app/(app)/cases/[id]/planning/page.tsx` | Create | 43 | Yes | botão "Regenerar premissas" e aviso do último cálculo |
| `apps/web/src/components/ComparisonTable.tsx` | Create | 44 | Yes | |
| `apps/web/src/components/SimulationLines.tsx` | Create | 45 | Yes | |
| `apps/web/src/app/(app)/cases/[id]/planning/[simId]/page.tsx` | Create | 46 | Yes | trata simulação com falha |
| `apps/web/src/app/api/simulations/[id]/export/route.ts` | Create | 47 | Yes | |
| `apps/web/src/app/(app)/cases/[id]/page.tsx` | Modify | 48 | Yes | |
| `README.md` | Modify | 49 | Yes | |
| `scripts/verify.mjs` | Modify | — | Yes | fora do manifest: nomes das amostras de 08/2026 renomeadas pelo usuário (folha, DRE, balancete) |
| `supabase/migrations/20260925000002_simulation_assumptions.sql` | Create | — | Yes | fora do manifest: cópia das premissas por simulação (revisão do PR #2) |
| `supabase/tests/rls.test.sql` | Modify | — | Yes | fora do manifest: contagem de objetos do Storage restrita ao caminho da fixture |

---

## Drift Detected

| # | Task / Path | Drift | Decision | Action |
|---:|---|---|---|---|
| 1 | `supabase/migrations/20260925000001_motor.sql` | A política `documents_insert` do Storage passou a bloquear também `%/simulations/%`, para que o usuário não grave o XLSX da memória | approved deviation (segurança, mesma migration do manifest) | coberto por asserção pgTAP |
| 2 | `services/worker/src/worker/main.py` | O DESIGN previa carregar as regras no início do worker; `main.py` não foi alterado: `Pipeline` usa `default_rules()` com cache por processo, e uma regra inválida levanta `RulesError` no primeiro job | false positive (mesmo efeito, sem arquivo extra) | nenhum |
| 3 | `scripts/verify.mjs`, `services/worker/tests/conftest.py` | Durante o build, o usuário renomeou a amostra `2.Resumo da Folha.pdf` para `2.Resumo da Folha 08.pdf` (e acrescentou as folhas 06 e 07) | approved deviation (dado de entrada) | referência atualizada; competência 2026-08 conferida pelo parser |
| 4 | `supabase/tests/rls.test.sql` | Asserção do ciclo 1 contava todos os objetos do escritório A no Storage e falhou depois do smoke E2E, que grava arquivos reais | false positive (teste frágil a dados locais) | contagem restrita ao caminho da fixture |
| 5 | migration, `db.py`, `planning/page.tsx` | Revisão pós-build: regenerar premissas (chave nova por pedido + botão) e remover as que deixaram de ser sugeridas | approved deviation (achado da revisão escolhida pelo usuário) | testes em `test_motor_pipeline.py` |

---

## Verification Results

### Incremental Verification

| Task | Command / Method | Result | Evidence |
|---|---|---|---|
| Regras | `pytest tests/test_engine_rules.py` | Pass | hash `e00eaa79e1ae…` estável entre Windows e contêiner |
| Simples | `pytest tests/test_engine_simples.py` | Pass | DAS de 06, 07 e 08/2026 = PGDAS-D por tributo; Fator R sem folha levanta `MissingRule` |
| Presumido | `pytest tests/test_engine_presumido.py` | Pass | KB 54.570,00 |
| Real | `pytest tests/test_engine_real.py` | Pass | KB 43.980,00; saldo credor transportado; exclusões na parte cumulativa |
| Orquestração | `pytest tests/test_engine_calculate.py` | Pass | golden 08/2026: Simples 23.430,47 · Presumido 26.165,68 · Real 63.093,28 |
| Pipeline | `pytest tests/test_motor_pipeline.py` | Pass | sugerir → confirmar → calcular → simulação → XLSX; regeneração |
| Banco | `npx supabase test db` | Pass | 63 asserções |
| Web | `npm run typecheck`, `vitest` | Pass | 14 testes |
| Imagem do worker | build Docker + carga de regras | Pass | mesmo `rules_hash` |
| Smoke E2E | script autenticado (`@supabase/ssr`) contra o ambiente local | Pass | 23 premissas; simulação igual ao golden; B não vê dados de A (0/0); XLSX 14.583 bytes; páginas 200; export 307 |

### Verify Gate

| Attribute | Value |
|---|---|
| **Kind** | test |
| **Command / Method** | `npm run verify` |
| **Exit / Result** | 0 |
| **Status** | Green |
| **Evidence** | Após as correções das revisões (pós-build e PR #2): pytest 130 passed; pgTAP 63 (Result: PASS); typecheck ok; vitest 14 passed — "VERIFY GATE: PASS" |

### Manual UX Receipt

N/A

### Complementary Checks

| Check | Command / Method | Status | Evidence |
|---|---|---|---|
| Lint | N/A | N/A | o projeto não define script de lint (web) nem ruff (worker) |
| Typecheck | `npm run typecheck` (no gate) | Pass | sem erros |
| Tests | `npm run verify` | Pass | ver Verify Gate |
| Build / Compile | `npx next build` | Pass | 12 rotas, incluindo `/cases/[id]/planning`, `/cases/[id]/planning/[simId]` e `/api/simulations/[id]/export` |

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|---|---|---|---|
| AT-101 | Competências completas e excluídas listadas | Pass | `test_engine_calculate.py`; página da simulação |
| AT-102 | Dossiê não homologado recusado | Pass | pgTAP `motor.test.sql`; `test_planning_requires_homologated_case` |
| AT-103 | Premissas sugeridas com origem | Pass | `test_suggestions_cover_catalog_with_origin`; smoke (23 premissas) |
| AT-104 | Justificativa ≥ 5 caracteres ao alterar sugestão | Pass | pgTAP; `schemas.test.ts` |
| AT-105 | Cálculo bloqueado com premissa pendente | Pass | pgTAP; `test_full_planning_flow` |
| AT-106 | Simulação com hash do snapshot, premissas e regras | Pass | `test_full_planning_flow` |
| AT-107 | Simples = PGDAS-D de 06/07/08-2026 | Pass | `test_das_equals_declared_pgdas` (3 competências) |
| AT-108 | Faixa 6: ICMS pela faixa 5 | Pass | `test_band6_icms_uses_band5` (regra marcada `verificado: false`) |
| AT-109 | ST/monofásico zera o tributo | Pass | `test_st_activity_has_no_icms` |
| AT-110 | Fator R escolhe III × V | Pass | `test_fator_r_chooses_annex`, `test_fator_r_line_in_memory`, `test_fator_r_without_payroll_premise_is_not_silently_annex_v` |
| AT-111 | Presumido golden KB | Pass | `test_engine_presumido.py` |
| AT-112 | LC 224 acima de R$ 5 mi | Pass | `test_engine_presumido.py` (vigências IRPJ 01/2026 e CSLL 04/2026) |
| AT-113 | Real golden KB com trava de 30% | Pass | `test_kb_golden_quarter_with_loss_compensation` |
| AT-114 | Receita cumulativa no Real | Pass | `test_cumulative_revenue_stays_at_365_in_real`, `test_exclusions_reduce_cumulative_base` |
| AT-115 | Trimestre parcial marcado | Pass | `test_engine_presumido.py`; golden (`2026-T3` parcial) |
| AT-116 | Impedimento → inelegível | Pass | `test_engine_eligibility.py` |
| AT-117 | Declaração ausente → indeterminado | Pass | `test_engine_eligibility.py`; confirmado no ambiente local (Simples indeterminado com "não informado") |
| AT-118 | Regra ausente → "não calculado" | Pass | `test_engine_calculate.py` |
| AT-119 | Encargos por regime | Pass | `test_engine_payroll_assumptions.py` |
| AT-120 | Linha com base, alíquota, fórmula, regra e origem | Pass | `test_full_planning_flow` (0 linhas sem regra) |
| AT-121 | Reexecução idêntica não duplica | Pass | `test_full_planning_flow` |
| AT-122 | Premissa alterada gera nova simulação | Pass | `test_full_planning_flow` |
| AT-123 | Comparativo ordenado por custo | Pass | smoke (`SIMPLES < PRESUMIDO < REAL`); página da simulação 200 |
| AT-124 | RLS entre escritórios | Pass | pgTAP; smoke (B vê 0/0) |
| AT-125 | Simulação em ≤ 60 s | Pass | `test_full_planning_flow`; smoke (cálculo em 34–41 ms no worker) |
| AT-126 | Golden aprovado reproduzido | Pass | `test_matches_approved_golden`; aprovação: Diekson Bernardes (responsável de negócio), 2026-09-25 |

---

## Advisor Ledger

| # | Phase | Note | Severity | Decision | Evidence |
|---:|---|---|---|---|---|
| 1 | post-build | Fator R sem premissa de folha caía no Anexo V | HIGH | APPLIED | `MissingRule` + sugestão da folha quando um perfil confirmado tem Fator R; 2 testes |
| 2 | post-build | `confirm_assumption` sem validação de tipo → falha do worker | HIGH | APPLIED | `assumption_value_ok` por `value_type`; 5 asserções pgTAP |
| 3 | post-build | Chave de atividade colidia com descrições iguais (ST × sem ST) | MEDIUM | APPLIED | chave com os tributos declarados zero; teste |
| 4 | post-build | Premissas não podiam ser regeneradas | MEDIUM | APPLIED | chave de job por pedido, botão "Regenerar premissas", remoção de premissas obsoletas; teste de integração |
| 5 | post-build | Limite trimestral da LC 224 majora mesmo com ano < R$ 5 mi | MEDIUM | REBUTTED | comportamento segue a premissa A-002 aprovada no DEFINE; regra marcada `verificado: false` e revisão contábil exigida antes do piloto |
| 6 | post-build | Saldo credor de PIS/Cofins não transportado | MEDIUM | APPLIED | saldo passa ao mês seguinte; teste |
| 7 | post-build | Job de cálculo com premissa pendente encerrava em silêncio | MEDIUM | APPLIED | motivo gravado no job e exibido na página de planejamento |
| 8 | post-build | Página de simulação com falha quebrava | MEDIUM | APPLIED | página mostra o erro; `next build` ok |
| 9 | post-build | Exclusões de PIS/Cofins ignoravam a parte cumulativa | MEDIUM | APPLIED | exclusões rateadas entre as partes; teste |
| 10 | post-build | Expressão confusa em `dre_has_icms` | LOW | APPLIED | regex de palavra inteira; golden inalterado |
| 11 | PR review (Codex, PR #2) | XLSX de simulação antiga exportava as premissas atuais do dossiê | HIGH | APPLIED | coluna `simulations.assumptions` (migration `20260925000002_simulation_assumptions.sql`) com a cópia usada no cálculo; teste em `test_motor_pipeline.py` |
| 12 | PR review (Codex, PR #2) | Sublimite deveria somar a receita do próprio mês | MEDIUM | REBUTTED | excesso acima de 20% produz efeito no mês seguinte (kb/simples-nacional/concepts/limites-sublimites-e-exclusao.md); comentário no código e teste `test_sublimit_takes_effect_in_the_month_after_the_excess` |
| 13 | PR review (Codex, PR #2) | PIS e Cofins zerados em conjunto quando só um é monofásico | MEDIUM | APPLIED | bases por tributo no Presumido e no Real; 2 testes |
| 14 | PR review (Codex, PR #2) | Base de PIS/Cofins do Presumido podia ficar negativa | MEDIUM | APPLIED | base limitada a zero; teste |

---

## Issues Encountered

| # | Issue | Resolution | Impact |
|---:|---|---|---|
| 1 | Perfil "revenda" excluía "exceto para o exterior" | termos proibidos ajustados | nenhum após a correção |
| 2 | Base de créditos de PIS/Cofins somava conta de grupo e analítica | apenas seções analíticas | sugestão 149.985,71 (conta 13101) |
| 3 | Linhas trimestrais de IRPJ/CSLL sem origem | origem com meses, receitas e premissas | AT-120 atendido |
| 4 | Limpeza de testes bloqueada pelos triggers append-only | limpeza em modo replica; lista de tabelas ampliada | nenhum |
| 5 | Worker antigo em segundo plano consumia jobs dos testes | worker parado antes da suíte e reiniciado com o código novo | nenhum |
| 6 | DRE da amostra sem CMV | registrado na aprovação do golden como característica do dado; o lucro do Real fica elevado | ranking do Real reflete a amostra, não um caso típico |
| 7 | O smoke E2E rodou no mesmo dossiê usado pelo usuário na revisão de telas e sobrescreveu as declarações de elegibilidade com "nao" | usuário avisado | só no ambiente local |

---

## Deviations from Design

| Deviation | User Decision | Reason | Impact |
|---|---|---|---|
| Regras carregadas sob demanda (`default_rules()`) em vez de no `main.py` | registrado neste relatório | mesmo efeito, sem arquivo extra | nenhum |
| Regeneração de premissas e validação de tipo no banco (revisão pós-build) | revisão pós-build escolhida pelo usuário | correção de defeitos | 1 função SQL nova; botão na tela de planejamento |

---

## Blockers

None.

---

## Final Status

### Overall: COMPLETE

- [x] All File Manifest tasks completed
- [x] Incremental verification recorded
- [x] Verify Gate green or manual-ux receipt positive
- [x] Complementary checks applicable pass
- [x] Acceptance Tests verified
- [x] LLM prompt receipts complete when required
- [x] Drift decisions recorded
- [x] Advisor findings disposed when applicable
- [x] No unresolved blocker
- [x] No TODO/FIXME used as unfinished implementation

---

## Next Step

Execute o **SDD Handoff by RDD**.
