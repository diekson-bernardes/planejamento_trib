# BUILD REPORT: Decisão Tributária (ciclo 3)

> Implementation report for Decisão Tributária — projeção 2026 pelo motor, sensibilidade com ponto de virada, recomendação com aprovação do responsável técnico e PDF executivo imutável.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | DECISAO_TRIBUTARIA |
| **Date** | 2026-09-25 |
| **Author** | SDD Build by RDD |
| **BRAINSTORM** | `sdd/BRAINSTORM_DECISAO_TRIBUTARIA.md` |
| **DEFINE** | `sdd/DEFINE_DECISAO_TRIBUTARIA.md` |
| **DESIGN** | `sdd/DESIGN_DECISAO_TRIBUTARIA.md` |
| **Status** | Complete |

---

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 38 |
| Cross-file coupling | High — projetor, sensibilidade e recomendação dependem uns dos outros e do motor do ciclo 2 (contrato do snapshot sintético) |
| Security surface | Migration com papel de responsável técnico, segregação de aprovação, RLS, gatilhos, RPCs `security definer` e política de Storage |
| LLM prompts | None (`LLM Prompts: false`; texto da recomendação montado por regras) |
| Independent volume | Baixo — cadeia projeção → motor → sensibilidade → recomendação → PDF |
| Context-rot risk | Médio (38 itens); mitigado por testes por módulo e golden |
| Runtime capabilities | default disponível; ralph possível via subagentes, mas desaconselhado pelo acoplamento; briefs inadequado para itens de segurança |

**Recommendation:** default — alto acoplamento com o motor do ciclo 2 e superfície de segurança no banco.

**User decision:** default, com branch nova `feat/decisao-tributaria` (primeiro commit `a4265e7` com Brainstorm/Define/Design) e revisão somente após o build.

**Pre-build review:** No — usuário escolheu revisão pós-build.

---

## Summary

| Metric | Value |
|---|---|
| **Tasks Completed** | 38/38 (1 sem alteração necessária, ver Deviations) |
| **Files Created** | 22 |
| **Files Modified** | 16 (15 do manifest + `AssumptionForm.tsx`, ver Drift) |
| **Files Deleted** | 0 |
| **Verification Commands Run** | 17 (pytest por módulo ×8, pgTAP ×4, typecheck, vitest, `npm run verify` ×3, `next build`, build e execução da imagem Docker, smoke E2E, render do PDF) |
| **Verify Gate** | Green |
| **Execution Mode** | default |

---

## Task Execution

| # | Manifest ID | Task | Executor | Status | Verification | Evidence |
|---:|---:|---|---|---|---|---|
| 1 | 1–2, 11 | Create `rules/decisao.json`, `engine/decision_params.py`; modify `config.py` (`DECISION_PARAMS`) | direct | Complete | carga local e na imagem Docker | versão 2026.1.0, hash `fe9143cce7d3…` igual no Windows e no contêiner |
| 2 | 3 | Modify `engine/assumptions.py` (premissas `projecao.*` e `conformidade.custo_anual`) | direct | Complete | `pytest -m "not db"` | 128 passed sem regressão; smoke: 12 de projeção + 3 de conformidade |
| 3 | 4 | Create `engine/projection.py` (snapshot sintético jan–dez) | direct | Complete | `pytest tests/test_decisao_projection.py` | 7 passed; meses realizados reproduzem `motor_202606_08`; sem alerta de RBT12 |
| 4 | 5 | Create `engine/sensitivity.py` | direct | Complete | `pytest tests/test_decisao_sensitivity.py` | 4 passed; virada de receita +9,7% (Presumido), limite jurídico +37% |
| 5 | 6 | Create `engine/recommendation.py` | direct | Complete | `pytest tests/test_decisao_recommendation.py` | 6 passed |
| 6 | 7 | Create `engine/decision.py` | direct | Complete | hash repetido em duas execuções | mesmo `result_hash`; 88 execuções do motor em ≈ 2,5 s |
| 7 | 8–9 | Create `report_pdf.py`; `reportlab>=5` em `pyproject.toml` | direct | Complete | `pytest tests/test_report_pdf.py` + render das páginas | 2 passed; mesmo SHA-256 em duas gerações |
| 8 | 12–14 | Modify `db.py`, `pipeline.py`; create migration `20260925000003_decisao.sql` | direct | Complete | `npx supabase migration up`; `pytest tests/test_decisao_pipeline.py` | 2 passed; projeção em 3,2 s |
| 9 | 15 | Create `supabase/tests/decisao.test.sql` | direct | Complete | `npx supabase test db` | 31 asserts (94 no total) PASS |
| 10 | 16–23 | Create testes e golden; modify `conftest.py` | direct | Complete | `pytest services/worker/tests` | 161 passed |
| 11 | 24–27 | Modify `database.types.ts`, `schemas.ts`, `schemas.test.ts`, `format.ts` | direct | Complete | `npm run typecheck`, `vitest` | limpo; 17 passed |
| 12 | 28–36 | Create/modify telas, componentes, admin e rota do PDF | direct | Complete | `next build` + smoke HTTP autenticado | rotas compiladas; páginas 200; download 307 |
| 13 | 37–38 | Modify `scripts/verify.mjs` (rótulos) e `README.md` | direct | Complete | `npm run verify` | PASS |
| 14 | 10 | `services/worker/Dockerfile` | direct | Complete (sem alteração) | `docker build` + `docker run` | `COPY rules` e `pip install .` já cobrem `decisao.json` e ReportLab 5.0.1 |

---

## Files Changed

| File | Action | Manifest ID | Verified | Notes |
|---|---|---:|---|---|
| `services/worker/rules/decisao.json` | Create | 1 | Yes | política de decisão versionada |
| `services/worker/src/worker/engine/decision_params.py` | Create | 2 | Yes | |
| `services/worker/src/worker/engine/assumptions.py` | Modify | 3 | Yes | |
| `services/worker/src/worker/engine/projection.py` | Create | 4 | Yes | |
| `services/worker/src/worker/engine/sensitivity.py` | Create | 5 | Yes | revisão: base no mesmo eixo; virada só na região elegível do base |
| `services/worker/src/worker/engine/recommendation.py` | Create | 6 | Yes | |
| `services/worker/src/worker/engine/decision.py` | Create | 7 | Yes | |
| `services/worker/src/worker/report_pdf.py` | Create | 8 | Yes | ReportLab invariant |
| `services/worker/pyproject.toml` | Modify | 9 | Yes | `reportlab>=5` |
| `services/worker/Dockerfile` | Unchanged | 10 | Yes | ver Deviations |
| `services/worker/src/worker/config.py` | Modify | 11 | Yes | |
| `services/worker/src/worker/db.py` | Modify | 12 | Yes | |
| `supabase/migrations/20260925000003_decisao.sql` | Create | 13 | Yes | revisão: chave de emissão por pedido, reset em pendente/remoção, limiar só para membros |
| `services/worker/src/worker/pipeline.py` | Modify | 14 | Yes | jobs `project` e `emit_report` |
| `supabase/tests/decisao.test.sql` | Create | 15 | Yes | 31 asserts |
| `services/worker/tests/test_decisao_projection.py` | Create | 16 | Yes | |
| `services/worker/tests/test_decisao_sensitivity.py` | Create | 17 | Yes | |
| `services/worker/tests/test_decisao_recommendation.py` | Create | 18 | Yes | |
| `services/worker/tests/test_report_pdf.py` | Create | 19 | Yes | |
| `services/worker/tests/test_decisao_pipeline.py` | Create | 20 | Yes | |
| `services/worker/tests/golden/decisao_2026.json` | Create | 21 | Yes | aprovado pelo responsável de negócio em 2026-09-25 |
| `services/worker/tests/test_decisao_golden.py` | Create | 22 | Yes | |
| `services/worker/tests/conftest.py` | Modify | 23 | Yes | fixtures e limpeza das novas tabelas |
| `apps/web/src/lib/database.types.ts` | Modify | 24 | Yes | regenerado |
| `apps/web/src/lib/schemas.ts` | Modify | 25 | Yes | |
| `apps/web/src/lib/schemas.test.ts` | Modify | 26 | Yes | |
| `apps/web/src/lib/format.ts` | Modify | 27 | Yes | |
| `apps/web/src/app/(app)/cases/[id]/planning/projection/actions.ts` | Create | 28 | Yes | |
| `apps/web/src/app/(app)/cases/[id]/planning/projection/[projId]/page.tsx` | Create | 29 | Yes | |
| `apps/web/src/components/ProjectionTable.tsx` | Create | 30 | Yes | |
| `apps/web/src/components/SensitivityTable.tsx` | Create | 31 | Yes | |
| `apps/web/src/components/RecommendationPanel.tsx` | Create | 32 | Yes | |
| `apps/web/src/app/(app)/cases/[id]/planning/page.tsx` | Modify | 33 | Yes | |
| `apps/web/src/app/(app)/admin/actions.ts` | Modify | 34 | Yes | |
| `apps/web/src/app/(app)/admin/page.tsx` | Modify | 35 | Yes | |
| `apps/web/src/app/api/reports/[id]/route.ts` | Create | 36 | Yes | |
| `scripts/verify.mjs` | Modify | 37 | Yes | |
| `README.md` | Modify | 38 | Yes | |
| `apps/web/src/components/AssumptionForm.tsx` | Modify | — | Yes | fora do manifest: entrada do tipo `ratio` (margem com sinal) |

---

## Drift Detected

| # | Task / Path | Drift | Decision | Action |
|---:|---|---|---|---|
| 1 | `engine/projection.py` | A amostra (Anexo I, sem Fator R) não tem série de folha no PGDAS-D; o Design previa folha de jan–mai pelas séries | approved deviation (dado de entrada) | folha de meses estimados = média dos meses completos, marcada como estimada |
| 2 | `engine/projection.py` | As séries do PGDAS-D de 06/2026 já trazem 2025-01 a 2026-05; a complementação pela RBAA (A-203) ficou só como contingência | false positive | mantida para PGDAS com série curta |
| 3 | migration + `AssumptionForm.tsx` | Margem projetada pode ser negativa: tipo novo `ratio` em `assumption_value_ok` e no formulário (arquivo fora do manifest) | approved deviation (necessário para AT-203/AT-204) | pgTAP cobre valor inválido e margem negativa |
| 4 | migration `request_projection` | Design dizia "exige nenhuma premissa pendente"; o DEFINE (AT-211) pede prévia bloqueada | DEFINE prevalece | RPC aceita pendentes; worker grava recomendação `bloqueado` com prévia e o envio é recusado |
| 5 | migration, `sensitivity.py` | Revisão pós-build: 5 correções (ver Advisor Ledger) | approved deviation | testes pgTAP adicionais e Verify Gate repetido |

---

## Verification Results

### Incremental Verification

| Task | Command / Method | Result | Evidence |
|---|---|---|---|
| Projetor | `pytest tests/test_decisao_projection.py` | Pass | 7 passed; Simples de jun–ago = golden `motor_202606_08` |
| Sensibilidade | `pytest tests/test_decisao_sensitivity.py` | Pass | 4 passed |
| Recomendação | `pytest tests/test_decisao_recommendation.py` | Pass | 6 passed |
| PDF | `pytest tests/test_report_pdf.py`; render com pdfplumber | Pass | seções presentes; SHA-256 reprodutível; 4 páginas |
| Fluxo no banco | `pytest tests/test_decisao_pipeline.py` | Pass | 2 passed; 3,2 s |
| Golden | `pytest tests/test_decisao_golden.py` | Pass | igualdade exata |
| Banco | `npx supabase test db` | Pass | 94 asserts |
| Web | `npm run typecheck`, `vitest`, `next build` | Pass | 17 testes; rotas novas compiladas |
| Imagem | `docker build` + `docker run` | Pass | ReportLab 5.0.1; hashes iguais |
| Smoke E2E | script autenticado em dossiê próprio (`55e52405…`) | Pass | projeção 4,1 s = golden; aprovação por analista recusada (42501); PDF 17.134 bytes com SHA-256 conferido; escritório B vê 0/0; páginas 200; download 307 |

### Verify Gate

| Attribute | Value |
|---|---|
| **Kind** | test |
| **Command / Method** | `npm run verify` |
| **Exit / Result** | 0 |
| **Status** | Green |
| **Evidence** | pytest 161 passed; pgTAP Files=4 Tests=94 Result: PASS; typecheck ok; vitest 17 passed — "VERIFY GATE: PASS" (após correções da revisão e golden aprovado) |

### Manual UX Receipt

N/A

### Complementary Checks

| Check | Command / Method | Status | Evidence |
|---|---|---|---|
| Lint | N/A | N/A | o projeto não define lint |
| Typecheck | `npm run typecheck` | Pass | sem erros |
| Tests | `npm run verify` | Pass | ver Verify Gate |
| Build / Compile | `npx next build`; `docker build` | Pass | rotas `/cases/[id]/planning/projection/[projId]`, `/api/reports/[id]`, `/admin`; imagem do worker |

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|---|---|---|---|
| AT-201 | 12 meses com origem | Pass | `test_months_are_labeled_by_origin` |
| AT-202 | Meses estimados pelo PGDAS-D e proporcionais | Pass | `test_estimated_months_use_pgdas_series_and_proportional_premises` |
| AT-203 | Orçamento substitui a média | Pass | `test_budget_replaces_average_and_marks_origin` |
| AT-204 | Alteração sem justificativa recusada | Pass | `confirm_assumption` (pgTAP ciclo 2) + margem inválida/negativa (pgTAP ciclo 3) |
| AT-205 | Idempotência | Pass | `test_projection_is_idempotent`, `test_full_decision_flow` (1 projeção após pedido repetido) |
| AT-206 | Limites aplicados no mês correto | Pass | `test_projected_revenue_crossing_the_sublimit_takes_ICMS_out_of_the_DAS` |
| AT-207 | Virada, distância e robustez | Pass | `test_every_variable_reports_turning_point_or_no_turn`, `test_turning_point_is_where_the_leader_changes` |
| AT-208 | Limite jurídico | Pass | `test_eligibility_change_is_reported_as_legal_limit` |
| AT-209 | Recomendado com explicação | Pass | `test_difference_above_threshold_is_recommended` |
| AT-210 | Inconclusivo | Pass | `test_difference_below_threshold_is_inconclusive` |
| AT-211 | Bloqueado com prévia | Pass | `test_missing_critical_data_blocks_with_preview`, `test_projection_blocked_while_premises_are_pending`, pgTAP |
| AT-212 | Inelegível/não calculado fora do ranking | Pass | `test_ineligible_and_not_calculated_regimes_leave_the_ranking` |
| AT-213 | Conformidade fora do ranking | Pass | `test_compliance_cost_is_shown_but_never_changes_the_ranking` |
| AT-214 | Admin configura limiar e responsável técnico | Pass | pgTAP (auditado) |
| AT-215 | Não RT não aprova | Pass | pgTAP; pipeline; smoke (42501) |
| AT-216 | RT não aprova a própria elaboração | Pass | pgTAP |
| AT-217 | Devolução com comentário | Pass | pgTAP; schema web |
| AT-218 | PDF com seções e SHA-256 | Pass | `test_pdf_has_required_sections`, `test_same_input_same_bytes`, pipeline, smoke |
| AT-219 | Premissa alterada → rascunho; PDF emitido intacto | Pass | pipeline; pgTAP (confirmação e volta a pendente) |
| AT-220 | RLS entre escritórios | Pass | pgTAP; smoke (0/0) |
| AT-221 | ≤ 60 s | Pass | pipeline 3,2 s; smoke 4,1 s |
| AT-222 | Golden aprovado | Pass | `test_projection_2026_matches_approved_golden`; aprovação: Diekson Bernardes, 2026-09-25 |
| AT-223 | Goldens do ciclo 2 | Pass | `test_matches_approved_golden` (motor_202608, motor_202606_08) e contrato de jun–ago |

---

## Advisor Ledger

| # | Phase | Note | Severity | Decision | Evidence |
|---:|---|---|---|---|---|
| 1 | post-build | `request_report` com chave fixa impedia reemitir após devolução ou falha | HIGH | APPLIED | chave com `txid_current()` |
| 2 | post-build | Ponto base da margem calculado por caminho diferente dos demais pontos | MEDIUM | APPLIED | base pelo mesmo eixo; resultados da amostra inalterados |
| 3 | post-build | Virada reportada além do limite jurídico | MEDIUM | APPLIED | virada só com o mesmo conjunto elegível do base |
| 4 | post-build | Regenerar premissas não devolvia recomendação aprovada | MEDIUM | APPLIED | gatilho em pendente e remoção; assert pgTAP |
| 5 | post-build | `decision_threshold` legível por outro escritório | LOW | APPLIED | exige `is_member`; assert pgTAP |

---

## Issues Encountered

| # | Issue | Resolution | Impact |
|---:|---|---|---|
| 1 | Worker em segundo plano disputava jobs dos testes de integração | parado antes da suíte e religado depois | nenhum |
| 2 | Divergência real R5 (salários a pagar) em 06 e 07/2026 bloqueava a homologação nos testes | teste e smoke justificam como o analista faria | nenhum |
| 3 | Alerta de 1 centavo no RBT12 sintético | linha do tempo arredondada ao centavo | sem alerta |
| 4 | "Novo líder" da bisseção pegava o lado do base | usa o ponto do lado oposto ao base | corrigido antes dos testes |
| 5 | Contagem de auditoria no pgTAP contava evento do smoke | filtro pela transação do teste | nenhum |
| 6 | DREs sem CMV (margem ≈ 80%) | registrado na aprovação do golden | Real elevado na amostra |
| 7 | Navegador embutido sem sessão no site local | validação por HTML autenticado; conferência visual fica com o usuário | nenhum |

---

## Deviations from Design

| Deviation | User Decision | Reason | Impact |
|---|---|---|---|
| `Dockerfile` sem alteração (item 10) | registrado neste relatório | `COPY rules` e `pip install .` já incluem `decisao.json` e ReportLab | nenhum |
| `request_projection` aceita premissas pendentes (prévia bloqueada) | DEFINE AT-211 prevalece | prévia "incompleta" exigida | envio para revisão recusado enquanto bloqueado |
| Tipo `ratio` e `AssumptionForm.tsx` fora do manifest | registrado neste relatório | margem negativa | 1 arquivo a mais |

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
