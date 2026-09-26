# BUILD REPORT: Reforma Tributária 2027 (ciclo 4)

> Implementation report for Reforma Tributária 2027 — regras versionadas por exercício (CBS/IBS no lugar de PIS/Cofins, crédito financeiro, IPI zero), quatro alternativas com o Simples híbrido, projeção 2027 deslocada da projeção 2026, Livro de Apuração do ICMS com conciliação R7 e golden aprovado.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | REFORMA_2027 |
| **Date** | 2026-09-26 |
| **Author** | SDD Build by RDD |
| **BRAINSTORM** | `sdd/BRAINSTORM_REFORMA_2027.md` |
| **DEFINE** | `sdd/DEFINE_REFORMA_2027.md` |
| **DESIGN** | `sdd/DESIGN_REFORMA_2027.md` |
| **Status** | Complete |

---

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 45 itens (≈ 60 arquivos) |
| Cross-file coupling | High — regras por exercício atravessam motor, projeção, sensibilidade, recomendação, pipeline, banco e telas; goldens de 2026 não podem mudar |
| Security surface | Migration com constraints, RPCs `security definer` (`request_calculation`, `request_projection`), gatilho de reset de recomendações |
| LLM prompts | None |
| Independent volume | Baixo — cadeia regras → motor → projeção → decisão → PDF |
| Context-rot risk | Alto (45 itens; sessão compactada uma vez); mitigado por testes por módulo, goldens e Verify Gate |
| Runtime capabilities | default disponível |

**Recommendation:** default — acoplamento alto e proteção dos goldens de 2026.

**User decision:** default, branch `feat/reforma-2027` (primeiro commit `302628c` com Brainstorm/Define/Design), revisão somente após o build; premissas do golden: CBS 9,5%, IBS 0,1%, crescimento 5%.

**Pre-build review:** No — usuário escolheu revisão pós-build.

---

## Summary

| Metric | Value |
|---|---|
| **Tasks Completed** | 45/45 (3 sem alteração no arquivo previsto, ver Deviations) |
| **Files Created** | 18 (8 regras 2027, `decisao_2027.json`, `cbs_ibs.py`, parser do livro, migration, pgTAP, 4 testes, golden) |
| **Files Modified** | 44 (manifest + 9 fora dele, ver Drift) |
| **Files Deleted** | 0 |
| **Verification Commands Run** | 24 (pytest por módulo ×10, pytest `-m "not db"` ×3, pytest `-m db` ×3, pgTAP ×4, typecheck, vitest, `npm run verify` ×3, `next build`, build/execução da imagem Docker, smoke E2E, extração do PDF 2027) |
| **Verify Gate** | Green |
| **Execution Mode** | default |

---

## Task Execution

| # | Manifest | Task | Mode | Status | Verification | Evidence |
|---:|---|---|---|---|---|---|
| 1 | 1–9 | Regras `rules/2027/*` (2027.1.0, `verificado: false`) e `decisao_2027.json` | direct | Complete | `load_rules(…, "2027")`; hash 2026 `e00eaa79e1ae` inalterado | regras 2027 carregam; goldens 2026 intactos |
| 2 | 10–13 | `rules.py` (consumo), `decision_params.py` (unidade), `config.py`, `memory.py` (`regimes_for`) | direct | Complete | pytest `-m "not db"` | 148 passed |
| 3 | 14–18 | `cbs_ibs.py`; Presumido/Real/Simples (por dentro e híbrido); `calculate.py` | direct | Complete | `test_engine_cbs_ibs.py` | sem PIS/Cofins/IPI; débito − crédito; saldo credor; 2026 = golden |
| 4 | 20–23 | Premissas `reforma_2027`, `shift_year`, sensibilidade com `cbs`, decisão por exercício | direct | Complete | `test_decisao_2027.py` | receita 2027 = 2026 × 1,05; 6 variáveis; 4 alternativas; 4,9–11 s |
| 5 | 24–27 | Livro de Apuração: tipo, classificação, parser, validações, R7 | direct | Complete | `test_livro_icms.py`, `test_classify.py`, `test_validations.py`, `test_reconcile.py` | 100 valores, 21 validações OK; R7 = 149.985,71 (diferença 0) |
| 6 | 28–29 | PDF com 4 alternativas; pipeline por exercício e bloqueio só de 2027 | direct | Complete | `test_report_pdf.py`; `test_reforma_pipeline.py` | PDF com 2027, híbrido, CBS 9,50%, IBS 0,10% e ressalva de regras não conferidas |
| 7 | 30–31 | Migration `20260925000004_reforma_2027.sql` e pgTAP | direct | Complete | `npx supabase test db` | Files=5, Tests=108 PASS |
| 8 | 32–38 | Testes, conftest, golden `decisao_2027` + teste | direct | Complete | pytest | golden aprovado em 2026-09-26 reproduzido |
| 9 | 39–43 | Tipos, rótulos, schemas, tabelas com regimes dinâmicos, "Projetar 2027", admin | direct | Complete | typecheck, vitest, `next build`, smoke HTTP | 19 vitest; páginas 200 |
| 10 | 44–45 | `verify.mjs`, README, KB `simples-na-reforma.md` | direct | Complete | `npm run verify` | PASS |

---

## Files Changed

| File | Action | Notes |
|---|---|---|
| `services/worker/rules/2027/{manifest,consumo,simples,presumido,real,encargos,elegibilidade,atividades}.json` | Create | 2027.1.0; `simples.json` com `cbs` no lugar de PIS+Cofins, `ibs` 0 e `hibrido: true` |
| `services/worker/rules/decisao_2027.json` | Create | variável `cbs` (fração, 0,5–1,5); carga de consumo com `cbs`/`ibs`; ressalvas 2027 |
| `services/worker/src/worker/engine/cbs_ibs.py` | Create | alíquotas-premissa, base sem ICMS/ISS, crédito financeiro, saldo credor |
| `services/worker/src/worker/engine/{rules,memory,presumido,real,simples,calculate,payroll,assumptions,projection,sensitivity,decision_params,decision,recommendation}.py` | Modify | motor por exercício; 4 alternativas; premissas `reforma_2027`; `shift_year`; bloqueio sem alíquota |
| `services/worker/src/worker/{models,classify,validations,reconcile,report_pdf,pipeline,config}.py`, `parsers/__init__.py` | Modify | Livro, R7, PDF 2027, projeção por exercício |
| `services/worker/src/worker/parsers/livro_icms_alterdata.py` | Create | entradas/saídas por CFOP, subtotais e totais |
| `supabase/migrations/20260925000004_reforma_2027.sql` | Create | doc_type, R7, alvo `compras_mercadorias`, `SIMPLES_HIBRIDO`, `request_calculation`/`request_projection(p_year)`, reset por exercício |
| `supabase/tests/reforma_2027.test.sql` | Create | 14 asserts |
| `supabase/seed.sql` | Modify | mapeamento `compras_mercadorias` 13101 (drift) |
| `services/worker/tests/{test_livro_icms,test_engine_cbs_ibs,test_decisao_2027,test_reforma_pipeline}.py` | Create | — |
| `services/worker/tests/golden/decisao_2027.json` | Create | aprovado; sem dados pessoais |
| `services/worker/tests/{conftest,test_decisao_golden,test_classify,test_decisao_pipeline,test_motor_pipeline}.py` | Modify | amostra do livro, fixtures 2027, grupo `reforma_2027` pendente nos fluxos de 2026 |
| `apps/web/src/lib/{database.types,format,schemas,schemas.test}.ts` | Modify | tipos, rótulos, `REGIME_ORDER`/`orderedRegimes`, `REQUIRED_DOC_TYPES`, `projectionYearSchema` |
| `apps/web/src/components/{ComparisonTable,ProjectionTable,RecommendationPanel,SensitivityTable,SimulationLines}.tsx` | Modify | regimes dinâmicos; sensibilidade em % para `fracao` |
| `apps/web/src/app/(app)/cases/[id]/{page,planning/page,planning/projection/actions,planning/projection/[projId]/page}.tsx/ts` | Modify | Livro opcional; "Projetar 2027"; pendências por exercício; aviso por exercício |
| `apps/web/src/app/(app)/admin/page.tsx` | Modify | rótulo "Compras de Mercadorias (R7)" |
| `scripts/verify.mjs`, `README.md`, `kb/reforma-tributaria/concepts/simples-na-reforma.md` | Modify | amostra do livro; seção do ciclo 4; hipóteses A-401 e art. 12, § 2º |

---

## Drift Detected

| File | Change outside manifest | Decision | Reason |
|---|---|---|---|
| `supabase/seed.sql` | mapeamento padrão `compras_mercadorias` = 13101 | registrado neste relatório | seed local precisa do alvo da R7 (a migration cobre escritórios existentes) |
| `services/worker/src/worker/engine/payroll.py` | terceiros: `not regime.startswith("SIMPLES")` | registrado | o híbrido é Simples para a folha |
| `apps/web/src/components/SensitivityTable.tsx`, `SimulationLines.tsx` | unidade `fracao` e regimes dinâmicos | registrado | exibir a variável CBS e o híbrido |
| `apps/web/src/app/(app)/cases/[id]/page.tsx` | Livro fora da lista de documentos faltantes | registrado | documento opcional |
| `services/worker/tests/test_classify.py`, `test_decisao_pipeline.py`, `test_motor_pipeline.py` | livro na classificação; grupo `reforma_2027` deixado pendente | registrado | premissas de 2027 sem padrão não podem ser confirmadas com nulo |
| `apps/web/.next/dev/types` | arquivo gerado truncado pelo dev server removido e regenerado | registrado | typecheck quebrava por arquivo gerado, não por código |

---

## Verification Results

### Incremental Verification

| Step | Command | Result | Evidence |
|---|---|---|---|
| Regressão após conftest/livro | `pytest -m "not db"` | Pass | 149 passed |
| Livro, classificação, validações, R7 | `pytest test_livro_icms test_classify test_validations test_reconcile` | Pass | 41 passed |
| Motor e decisão 2027 | `pytest test_engine_cbs_ibs test_decisao_2027` | Pass | 11 → 12 → 14 passed com as correções |
| Integração | `pytest -m db` | Pass (após ajuste dos helpers) | 16 passed; projeção 2027 em 6,6 s (90 execuções) |
| Banco | `npx supabase test db` | Pass | Files=5, Tests=108 |
| Web | typecheck; `vitest run` | Pass | 19 passed |
| Golden | `pytest test_decisao_golden.py` | Pass | 2 passed (2026 e 2027) |
| Smoke E2E | script autenticado em dossiê próprio `6c65265c…` | Pass | ver abaixo |

### Verify Gate

| Attribute | Value |
|---|---|
| **Kind** | test |
| **Command / Method** | `npm run verify` |
| **Exit / Result** | 0 |
| **Status** | Green |
| **Evidence** | pytest 184 passed; pgTAP Files=5 Tests=108 Result: PASS; typecheck ok; vitest 19 passed — "VERIFY GATE: PASS" (após correções da revisão e golden aprovado) |

### Manual UX Receipt

N/A

### Complementary Checks

| Check | Command / Method | Status | Evidence |
|---|---|---|---|
| Lint | N/A | N/A | o projeto não define lint |
| Typecheck | `npm run typecheck` | Pass | sem erros |
| Tests | `npm run verify` | Pass | ver Verify Gate |
| Build / Compile | `next build`; `docker build` + `docker run` | Pass | imagem carrega `rules_for(2027)` e `decision_params_for(2027)` = 2027.1.0 |
| Smoke E2E | 13 PDFs → R7 → homologação → cálculo 2026 com reforma pendente → premissas 2027 → Projetar 2027 → aprovação → PDF → páginas | Pass | R7 ok (149.985,71); cálculo 2026 liberado; projeção 2027 em 15,3 s = golden; analista aprova → 42501; PDF 19.948 bytes com SHA-256 conferido; escritório B vê 0/0; páginas 200; download 307 |

---

## Acceptance Test Verification

| AT | Description | Status | Evidence |
|---|---|---|---|
| AT-401 | 2026 inalterado | Pass | goldens `motor_*`, `decisao_2026`; `test_2026_calculation_unchanged` |
| AT-402 | 2027 sem PIS/Cofins/IPI, com CBS/IBS | Pass | `test_no_pis_cofins_ipi_in_2027`; pipeline (linhas gravadas) |
| AT-403 | Débito − crédito, saldo credor | Pass | `test_regular_regime_cbs_is_debit_minus_financial_credit`, `test_credit_balance_is_carried_forward` |
| AT-404 | Simples por dentro com CBS no DAS | Pass | `test_hybrid_takes_cbs_ibs_out_of_das` (Simples com `cbs` do DAS, `ibs` 0 — hipótese A-401) |
| AT-405 | Híbrido: CBS/IBS fora do DAS | Pass | mesmo teste; demais parcelas iguais ao Simples |
| AT-406 | 2027 = 2026 deslocado com crescimento | Pass | `test_2027_is_2026_projection_shifted_with_growth` |
| AT-407 | Sem alíquota → bloqueado | Pass | pipeline (prévia bloqueada); `test_legacy_case_without_rates_is_blocked_not_recommended` |
| AT-408 | Quatro alternativas, limiar, fatores | Pass | golden 2027; `test_consumption_load_includes_cbs_ibs` |
| AT-409 | Sensibilidade com CBS | Pass | `test_sensitivity_has_cbs_rate_variable` (sem virada no intervalo 0,5–1,5) |
| AT-410 | Livro classificado, extraído e validado | Pass | `test_livro_is_parsed_with_totals`; classify |
| AT-411 | Soma adulterada falha | Pass | `test_tampered_cfop_fails_validation` |
| AT-412 | R7 pela tolerância | Pass | `test_r7_purchases_match_balancete`, `test_r7_divergence_and_absence`; pipeline; smoke |
| AT-413 | R7 divergente bloqueia homologação | Pass | mecanismo genérico de `homologate_case` (qualquer regra divergente sem justificativa, pgTAP `homologation.test.sql`); R7 aceita na constraint (pgTAP) |
| AT-414 | Base de créditos pelo livro ou balancete | Pass | `test_reform_suggestions_are_all_in_their_own_group` (origem = Livro, CFOPs); sem livro: contas de mercadorias do balancete (ver Deviations) |
| AT-415 | Documento em dossiê homologado recusado | Pass | pgTAP "Livro enviado depois da homologação é recusado" |
| AT-416 | Livro com outro CNPJ | Pass | `test_livro_with_other_cnpj_is_blocked` |
| AT-417 | ≤ 60 s | Pass | pipeline 6,6 s; smoke 15,3 s |
| AT-418 | PDF 2027 | Pass | pipeline emite; texto extraído contém 2027, híbrido, CBS 9,50%, IBS 0,10%, crescimento e "não conferid" |
| AT-419 | Golden 2027 aprovado | Pass | `test_projection_2027_matches_approved_golden`; aprovação: Diekson Bernardes, 2026-09-26 |
| AT-420 | Goldens anteriores | Pass | `npm run verify` |

Golden `decisao_2027` (CBS 9,5%, IBS 0,1%, crescimento 5%): Simples 378.692,23 < híbrido 471.845,47 < Presumido 475.153,57 < Real 1.260.440,27; recomendado Simples, 24,60% abaixo do híbrido; viradas: receita +20,9% (Presumido), créditos +55% (híbrido); limite jurídico da receita +31%.

---

## Advisor Ledger

| # | Phase | Note | Severity | Decision | Evidence |
|---:|---|---|---|---|---|
| 1 | post-build | Premissa de 2027 devolvia a rascunho a recomendação de 2026 aprovada | HIGH | APPLIED | gatilho filtra por `projections.year`; 2 asserts pgTAP |
| 2 | post-build | Dossiê sem alíquotas (premissas pré-ciclo 4) recomendava o Simples "único calculado" | HIGH | APPLIED | bloqueio explícito em `decision.project`; teste |
| 3 | build | Base de CBS/IBS sem exclusão de ICMS/ISS (design, art. 12, § 2º) | HIGH | APPLIED | ICMS/ISS do regime fora da base; memória mostra o valor |
| 4 | build | Razão de créditos usava receita já multiplicada pela alavanca | MEDIUM | APPLIED | virada falsa removida; teste da alavanca |
| 5 | build | Carga de consumo de 2027 sem CBS/IBS | MEDIUM | APPLIED | `decisao_2027.json`; teste |
| 6 | post-build | Custo de conformidade do híbrido bloqueava o cálculo de 2026 | MEDIUM | APPLIED | grupo `reforma_2027`; teste |
| 7 | post-build | Ordem dos regimes no PDF diferente da tela | LOW | APPLIED | ordem única Simples, híbrido, Presumido, Real |

---

## Issues Encountered

| # | Issue | Resolution | Impact |
|---:|---|---|---|
| 1 | Helpers de integração confirmavam premissas de 2027 com valor nulo (recusado pelo banco) | grupo `reforma_2027` fica pendente nos fluxos de 2026 (demonstra que não bloqueia) | nenhum |
| 2 | Arquivo gerado `.next/dev/types` truncado pelo dev server | removido e regenerado | nenhum |
| 3 | Primeiro smoke com worker sem variáveis do Supabase (extração TRANSIENT) | dossiê de teste removido do banco local; worker religado com a configuração local | objetos órfãos no Storage local |
| 4 | PowerShell corrompeu a codificação do `seed.sql` | restaurado pelo Git e editado preservando UTF-8 | nenhum |
| 5 | Planalto indisponível (ECONNRESET) na pesquisa da LC 214 | fontes secundárias; regras `verificado: false` | revisão contábil pendente |

---

## Deviations from Design

| Deviation | User Decision | Reason | Impact |
|---|---|---|---|
| `eligibility.py` (19), `db.py` (29) e `test_reconcile.py` (33) sem alteração | registrado neste relatório | elegibilidade do híbrido = a do Simples em `calculate.py`; `save_projection` já gravava `year`; testes de R7 em `test_livro_icms.py` | nenhum |
| ICMS/ISS excluído da base pelo valor calculado no regime (líquido), não pelo destacado nas notas | registrado | sem campo de ICMS destacado sem o livro; o livro traz o destacado só da amostra de 08 | CBS/IBS levemente superestimadas quando há créditos de ICMS |
| Devoluções de venda (CFOP 1202/1411) não deduzidas da receita | registrado | base usa a premissa de exclusões | tratar no ciclo do mix de vendas |
| Monofásico de PIS/Cofins tratado como isento de CBS | registrado (hipótese) | sem regra de monofásico na CBS nas fontes | ressalva |
| SHOULD "saídas do livro × receita do PGDAS (informativa)" não implementado | registrado | fora do caminho crítico | nenhum no cálculo |
| Base de créditos sem livro vem das contas de mercadorias do balancete (rótulos), não só da 13101 | registrado | reaproveita a regra de sugestão de créditos do ciclo 2 | premissa editável com justificativa |
| Gatilho de reset redefinido na migration de 2027 | registrado | correção da revisão | recomendações de 2026 preservadas |

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
