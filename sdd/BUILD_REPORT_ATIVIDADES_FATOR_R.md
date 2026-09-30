# BUILD REPORT: Atividades mistas e Fator R no Planejamento Rápido

> Implementation report for Atividades mistas e Fator R no Planejamento Rápido

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | ATIVIDADES_FATOR_R |
| **Date** | 2026-09-28 |
| **Author** | SDD Build by RDD |
| **BRAINSTORM** | `sdd/BRAINSTORM_ATIVIDADES_FATOR_R.md` |
| **DEFINE** | `sdd/DEFINE_ATIVIDADES_FATOR_R.md` |
| **DESIGN** | `sdd/DESIGN_ATIVIDADES_FATOR_R.md` |
| **Status** | Complete |

---

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 23 |
| Cross-file coupling | High — banco → snapshot → quick_view → projeção/decisão → pipeline → PDF → tela; goldens dependem do conjunto |
| Security surface | Tabela nova com RLS e RPC security definer (`set_case_activities`) |
| LLM prompt items | None (`LLM Prompts: false`) |
| Independent volume | Baixo: tarefas em cadeia |
| Context-rot risk | Médio; mitigado por verificação incremental e goldens |
| Runtime capabilities | default disponível; ralph/briefs possíveis via subagentes, mas desaconselhados pelo acoplamento |

**Recommendation:** default — cadeia de dependências e goldens exigem visão do conjunto (mesmo modo dos ciclos 1–5).

**User decision:** default ("1a").

**Pre-build review:** No — usuário escolheu "2 não"; sem ferramenta de revisão externa formal.

---

## Summary

| Metric | Value |
|---|---|
| **Tasks Completed** | 23/23 |
| **Files Created** | 10 |
| **Files Modified** | 18 |
| **Files Deleted** | 0 |
| **Verification Commands Run** | 18 |
| **Verify Gate** | Green |
| **Execution Mode** | default |

---

## Task Execution

| # | Manifest ID | Task | Executor | Status | Verification | Evidence |
|---:|---:|---|---|---|---|---|
| 1 | 1 | Create migration `20260929000008_atividades_fator_r.sql` | direct | Complete | `npx supabase migration up` | aplicada sem reset (dados do usuário preservados) |
| 2 | 2 | Create `supabase/tests/atividades_fator_r.test.sql` | direct | Complete | `npx supabase test db supabase/tests/atividades_fator_r.test.sql` | 19/19 PASS (após 1 correção de formato decimal) |
| 3 | 3 | Regenerate `database.types.ts` | direct | Complete | `npm run db:types` | tipos de `case_activities`/`set_case_activities` presentes |
| 4 | 4 | Create `rules/fator_r.json` | direct | Complete | `pytest tests/test_fator_r.py` | carregado com hash próprio |
| 5 | 5 | Modify `config.py` (`fator_r_params_path`) | direct | Complete | `pytest tests/test_fator_r.py` | pass |
| 6 | 6 | Create `engine/fator_r.py` | direct | Complete | `pytest tests/test_fator_r.py` | 12 pass |
| 7 | 7 | Modify `engine/quick_view.py` (N atividades, ST/mono no comércio, sugestões) | direct | Complete | `pytest tests/test_quick_view.py tests/test_decisao_golden.py` | 12 pass; `rapido_2027` idêntico |
| 8 | 8 | Modify `engine/projection.py` (`payroll_history`) | direct | Complete | `pytest tests/test_decisao_golden.py tests/test_decisao_2027.py` | 9 pass |
| 9 | 9 | Modify `pipeline.py` (ajuste da folha 12m e folha ideal) | direct | Complete | `pytest tests/test_fator_r.py -k pipeline` | pass |
| 10 | 10 | Modify `report_pdf.py` (+ `db.py` para base/rate/atividades) | direct | Complete | `pytest tests/test_report_pdf.py` e `-k pipeline` | pass; PDF com as 3 seções |
| 11 | 11 | Create `tests/test_fator_r.py` | direct | Complete | `pytest tests/test_fator_r.py` | 13 pass |
| 12 | 12 | `tests/test_quick_view.py` | direct | Complete | `pytest tests/test_quick_view.py` | sem alteração: testes novos ficaram em `test_fator_r.py` (ver Deviations) |
| 13 | 13 | Create golden `rapido_misto_2027.json` | direct | Complete | teste do golden | aprovado pelo usuário em 2026-09-28 |
| 14 | 14 | `tests/test_rapido_pipeline.py` | direct | Complete | `pytest tests/test_fator_r.py -k pipeline` | integração ficou em `test_fator_r.py` sem PDF real (ver Deviations) |
| 15 | 15 | Modify `lib/schemas.ts` (`activitiesSchema`, `percentToCents`) | direct | Complete | `npx vitest run` | pass |
| 16 | 16 | Modify `lib/schemas.test.ts` | direct | Complete | `npx vitest run` | 28 pass |
| 17 | 17 | Modify `cases/actions.ts` (`saveActivities`) | direct | Complete | `npm run typecheck` | exit 0 |
| 18 | 18 | Create `components/CaseActivities.tsx` | direct | Complete | smoke no navegador | soma ao vivo, botão bloqueado com 99,99%, gravação ok |
| 19 | 19 | Modify `cases/[id]/page.tsx` | direct | Complete | smoke no navegador | seção "Atividades da empresa" |
| 20 | 20 | Create `components/FatorRTable.tsx` | direct | Complete | smoke no navegador | quadro igual ao golden |
| 21 | 21 | Create `components/FolhaIdealTable.tsx` | direct | Complete | smoke no navegador | quadro igual ao golden |
| 22 | 22 | Modify projection page | direct | Complete | smoke no navegador | atividades + Fator R + folha ideal |
| 23 | 23 | Modify `lib/format.ts` | direct | Complete | `npm run typecheck` | rótulos `media`/`zero` e grupo "Folha (encargos e Fator R)" |

---

## Files Changed

| File | Action | Manifest ID | Verified | Notes |
|---|---|---:|---|---|
| `supabase/migrations/20260929000008_atividades_fator_r.sql` | Create | 1 | Yes | `rapido_blockers`/`homologate_case` alterados por substituição do trecho, com guarda |
| `supabase/tests/atividades_fator_r.test.sql` | Create | 2 | Yes | 19 asserts |
| `apps/web/src/lib/database.types.ts` | Modify | 3 | Yes | regenerado |
| `services/worker/rules/fator_r.json` | Create | 4 | Yes | `verificado: false` |
| `services/worker/src/worker/config.py` | Modify | 5 | Yes | |
| `services/worker/src/worker/engine/fator_r.py` | Create | 6 | Yes | |
| `services/worker/src/worker/engine/quick_view.py` | Modify | 7 | Yes | |
| `services/worker/src/worker/engine/projection.py` | Modify | 8 | Yes | campo `payroll_history` |
| `services/worker/src/worker/engine/decision.py` | Modify | 8 | Yes | parâmetro `adjust` (ver Deviations) |
| `services/worker/src/worker/pipeline.py` | Modify | 9 | Yes | |
| `services/worker/src/worker/report_pdf.py` | Modify | 10 | Yes | |
| `services/worker/src/worker/db.py` | Modify | 10 | Yes | base/rate das linhas e atividades do snapshot no PDF (ver Deviations) |
| `services/worker/tests/test_fator_r.py` | Create | 11, 12, 14 | Yes | unidade + golden + integração |
| `services/worker/tests/conftest.py` | Modify | 11 | Yes | caso fictício `misto_content`, `fator_r_params`, limpeza de `case_activities` |
| `services/worker/tests/golden/rapido_misto_2027.json` | Create | 13 | Yes | aprovado |
| `apps/web/src/lib/schemas.ts` | Modify | 15 | Yes | |
| `apps/web/src/lib/schemas.test.ts` | Modify | 16 | Yes | |
| `apps/web/src/app/(app)/cases/actions.ts` | Modify | 17 | Yes | |
| `apps/web/src/components/CaseActivities.tsx` | Create | 18 | Yes | |
| `apps/web/src/app/(app)/cases/[id]/page.tsx` | Modify | 19 | Yes | |
| `apps/web/src/components/CompanyCnae.tsx` | Modify | 19 | Yes | texto do anexo "por atividade" |
| `apps/web/src/components/FatorRTable.tsx` | Create | 20 | Yes | |
| `apps/web/src/components/FolhaIdealTable.tsx` | Create | 21 | Yes | |
| `apps/web/src/components/ProjectionTable.tsx` | Modify | 22 | Yes | tipo `ProjectionLine` com base/rate |
| `apps/web/src/app/(app)/cases/[id]/planning/projection/[projId]/page.tsx` | Modify | 22 | Yes | |
| `apps/web/src/lib/format.ts` | Modify | 23 | Yes | |
| `supabase/tests/rls.test.sql` | Modify | — | Yes | fixa a tolerância do escritório A dentro da transação (ver Issues) |
| `sdd/BUILD_REPORT_ATIVIDADES_FATOR_R.md` | Create | — | Yes | este relatório |

---

## Drift Detected

| # | Task / Path | Drift | Decision | Action |
|---:|---|---|---|---|
| 1 | `engine/decision.py` | O gancho da folha 12m projetada precisava valer também nos cenários de sensibilidade; o ponto natural é o `builder` de `project`, não só `projection.py` | approved deviation (técnica, sem mudança de requisito) | `project(..., adjust=None)` + `ProjectedCase.payroll_history`; sem efeito quando `adjust` é None |
| 2 | `services/worker/src/worker/db.py` | O PDF precisava de base/rate das linhas e das atividades do snapshot | approved deviation (técnica) | duas colunas a mais na consulta do relatório |
| 3 | `tests/test_quick_view.py`, `tests/test_rapido_pipeline.py` | Testes novos dependem só do caso fictício; nesses arquivos exigiriam os PDFs reais (`samples`) | approved deviation (técnica) | testes em `tests/test_fator_r.py`, que roda sem amostras |

---

## Verification Results

### Incremental Verification

| Task | Command / Method | Result | Evidence |
|---|---|---|---|
| Migration | `npx supabase migration up` | Pass | "Migrations applied" |
| pgTAP novo | `npx supabase test db supabase/tests/atividades_fator_r.test.sql` | Pass | 19/19 |
| Goldens antes/depois do motor | `python -m pytest tests/test_decisao_golden.py tests/test_decisao_2027.py -q` | Pass | 9 passed |
| Rápido + goldens | `python -m pytest tests/test_quick_view.py tests/test_decisao_golden.py -q` | Pass | 12 passed |
| Fator R | `python -m pytest tests/test_fator_r.py -q` | Pass | 13 passed |
| PDF | `python -m pytest tests/test_report_pdf.py -q` | Pass | 2 passed |
| Web | `npm run typecheck` / `npx vitest run` | Pass | exit 0 / 28 passed |
| Smoke | navegador interno, dossiê fictício `d6000000-…-006` no Escritório A (teste) | Pass | atividades 60/40 gravadas pela tela; soma 99,99% bloqueada; homologação com `activities` no snapshot; projeção 2027 `fee016f5` com Fator R e folha ideal iguais ao golden |

### Verify Gate

| Attribute | Value |
|---|---|
| **Kind** | test |
| **Command / Method** | `npm run verify` |
| **Exit / Result** | 0 |
| **Status** | Green |
| **Evidence** | 3ª execução (2026-09-30): pytest 236 passed em 260 s · pgTAP Files=9, Tests=169, PASS · typecheck ok · vitest 28 passed · `VERIFY GATE: PASS`. 1ª execução vermelha (rls.test.sql #22, Issue 5); 2ª interrompida junto com a sessão, sem falha registrada |

### Manual UX Receipt

N/A

### Complementary Checks

| Check | Command / Method | Status | Evidence |
|---|---|---|---|
| Lint | N/A | N/A | projeto sem lint configurado no Verify Gate |
| Typecheck | `npm run typecheck` (dentro do verify) | Pass | exit 0 |
| Tests | `npm run verify` | Pass | ver Verify Gate |
| Build / Compile | N/A | N/A | não executado (dev server ativo no mesmo `.next`) |

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|---|---|---|---|
| AT-601 | CNAEs secundários guardados sem QSA | Pass | já existente (`cnpj_lookup.parse_payload`, `test_cnpj_lookup.py`); exibidos na tela de atividades |
| AT-602 | Atividades e percentuais gravados | Pass | pgTAP "duas atividades somando 100,00% gravadas"; `test_pipeline_persists_activities_fator_r_and_folha_ideal` |
| AT-603 | Soma ≠ 100,00% recusada | Pass | pgTAP (RPC e `rapido_blockers`), vitest, `test_percentages_must_sum_100`, smoke (botão bloqueado) |
| AT-604 | Lista vazia/CNAE inválido recusados | Pass | pgTAP + vitest |
| AT-605 | Atividade única = 100% | Pass | pgTAP + `test_single_activity_gets_all_revenue` + vitest |
| AT-606 | Receita por atividade e perfil sugerido | Pass | `test_activities_split_revenue` |
| AT-607 | Fator R por competência com FGTS | Pass | `test_monthly_fator_r_changes_anexo`, golden |
| AT-608 | Sem escolha → cálculo para | Pass | `test_missing_payroll_requires_choice`, `test_window_and_missing_treatment` |
| AT-609 | Média × zero | Pass | idem |
| AT-610 | Sem folha → só "zero" | Pass | `test_without_any_payroll_only_zero` |
| AT-611 | Folha ideal informativa | Pass | `test_monthly_fator_r_changes_anexo`, golden, integração |
| AT-612 | CNAE fora da tabela bloqueia o Simples | Pass | `test_unknown_cnae_blocks_simples` |
| AT-613 | Goldens existentes sem diferença | Pass | `npm run verify` (goldens `motor_*`, `decisao_*`, `rapido_2027`) |
| AT-614 | ST/mono da empresa, no comércio | Pass | `test_st_and_mono_come_from_commerce_only`; `test_percentages_split_activities` (ciclo 5) |
| AT-615 | Travado após homologação | Pass | pgTAP "atividades travadas no dossiê homologado" |
| AT-616 | Tela e PDF com os quadros | Pass | integração (texto do PDF) + smoke da tela |
| AT-617 | RLS entre escritórios | Pass | pgTAP (leitura e gravação negadas ao escritório B) |

---

## Advisor Ledger

None — no formal external review was executed.

---

## Issues Encountered

| # | Issue | Resolution | Impact |
|---:|---|---|---|
| 1 | `to_char(..., 'FM990D00')` usava o separador do locale (ponto) na mensagem | `replace(to_char(..., 'FM990.00'), '.', ',')`; funções reaplicadas no banco local | nenhum |
| 2 | Coluna de auditoria é `event`, não `action` | teste pgTAP corrigido | nenhum |
| 3 | Heredoc do bash no Windows quebrou um script Python longo | scripts gravados no scratchpad e executados | nenhum |
| 4 | Aritmética errada num teste unitário (esperado 54.000 em vez de 64.800) | teste corrigido; código estava certo | nenhum |
| 5 | 1º `npm run verify` vermelho: `rls.test.sql` #22 esperava tolerância 1,00, mas o admin do seed a alterou para 10 pela tela (audit `office.tolerance_changed` em 2026-09-29 02:20 UTC) | teste passa a fixar a tolerância dentro da própria transação (rollback); configuração do usuário preservada; verify repetido | nenhum no produto |
| 6 | 1ª execução do worker levou ~607 s (máquina ocupada); a 3ª levou 260 s (antes do ciclo: ~218 s) | nenhuma ação | +~40 s pelos testes do Fator R |

---

## Deviations from Design

| Deviation | User Decision | Reason | Impact |
|---|---|---|---|
| Gancho `adjust` em `decision.project` + `payroll_history` em `projection.py` no lugar de `folha_12m_override` só na projeção | Registrado como desvio técnico (requisito inalterado) | Sensibilidade também precisa da folha 12m derivada | Nenhum efeito fora do rápido com Fator R |
| `db.py` alterado para o PDF | Registrado | PDF precisa de base/rate e atividades | Consulta do relatório com 2 campos a mais |
| Testes novos em `test_fator_r.py` em vez de `test_quick_view.py`/`test_rapido_pipeline.py` | Registrado | Rodam sem os PDFs reais | Cobertura roda sempre, inclusive sem `docs/Amostras` |
| Tabela de atividades na tela de projeção inline (sem componente `ActivitiesTable`) | Registrado | Tabela simples de 3 colunas | Nenhum |

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
