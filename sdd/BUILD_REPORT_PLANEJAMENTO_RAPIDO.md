# BUILD REPORT: Planejamento Rápido (ciclo 5)

> Implementation report for Planejamento Rápido — dossiê de 2027 a partir da Declaração de Faturamento, folha e DRE (PDF ou digitados), com CNAE consultado na automação n8n (ou digitado), anexo sugerido por tabela CNAE → anexo e comparação Simples por dentro × Simples por fora × Lucro Presumido.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | PLANEJAMENTO_RAPIDO |
| **Date** | 2026-09-28 |
| **Author** | SDD Build by RDD |
| **BRAINSTORM** | `sdd/BRAINSTORM_PLANEJAMENTO_RAPIDO.md` |
| **DEFINE** | `sdd/DEFINE_PLANEJAMENTO_RAPIDO.md` |
| **DESIGN** | `sdd/DESIGN_PLANEJAMENTO_RAPIDO.md` |
| **Status** | Complete |

---

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 26 itens (≈ 40 arquivos) |
| Cross-file coupling | High — o adaptador `quick_view` alimenta a projeção dos ciclos 3–4; `homologate_case` redefinida; parâmetro novo no motor |
| Security surface | Migration com tabela nova + RLS, 6 RPCs `security definer`, chamada externa à automação n8n (MCP sem autenticação) |
| LLM Prompts | None (`LLM Prompts: false`; a automação é chamada como ferramenta MCP determinística) |
| Independent volume | Baixo — cadeia entrada → homologação → premissas → projeção → PDF |
| Context-rot risk | Alto (26 itens; sessão interrompida por limite de uso e retomada) — mitigado por testes por módulo, goldens e Verify Gate |
| Runtime capabilities | default disponível; ralph possível via subagentes, desaconselhado pelo acoplamento |

**Recommendation:** default — acoplamento alto, quatro goldens a proteger e superfície de segurança no banco.

**User decision:** default; revisão somente pós-build; uma chamada real à automação n8n com o CNPJ da amostra para conferir o formato (sem gravar sócios); commit dos documentos primeiro (`ab8778c`) e do código no fim.

**Pre-build review:** No — usuário escolheu revisão pós-build.

---

## Summary

| Metric | Value |
|---|---|
| **Tasks Completed** | 26/26 |
| **Files Created** | 15 (migration, pgTAP, tabela CNAE, `cnae.py`, `quick_view.py`, parser, `cnpj_lookup.py`, 5 testes, golden, 3 componentes web, KB) |
| **Files Modified** | 27 (manifest + 3 fora dele, ver Drift) |
| **Files Deleted** | 0 |
| **Verification Commands Run** | 27 (pytest por módulo ×12, pytest `-m "not db"` ×2, pytest `-m db` ×4, pgTAP ×6, typecheck ×5, vitest ×2, `npm run verify` ×3, `next build`, build/execução Docker, chamada real à automação, smoke E2E, conferência de páginas) |
| **Verify Gate** | Green |
| **Execution Mode** | default |

---

## Task Execution

| # | Manifest | Task | Mode | Status | Verification | Evidence |
|---:|---|---|---|---|---|---|
| 1 | 1–2 | Migration `20260926000005_planejamento_rapido.sql` + pgTAP | direct | Complete | `npx supabase migration up`; `npx supabase test db` | aplicada; Files=6 Tests=128 PASS (20 novos) |
| 2 | 3–4 | Tabela `rules/cnae_anexos.json` (82 prefixos, `verificado: false`) e `engine/cnae.py` | direct | Complete | `test_cnae.py` | 4744-0/01 → Anexo I; prefixo mais longo; vedações; fora da tabela sem sugestão |
| 3 | 5–7 | Tipo `DECLARACAO_FATURAMENTO`, classificação (período MM/AAAA), parser e validações | direct | Complete | `test_declaracao_faturamento.py` | 12 meses, Total Geral 3.719.883,51, soma e sequência aprovadas; CNPJ divergente bloqueado |
| 4 | 8–10 | `quick_view.py`, `synthetic_month` público, sugestões do rápido | direct | Complete | `test_quick_view.py` | meses realizados 06–08; atividades normal/ST/monofásico; perfil por CNAE; créditos sem sugestão |
| 5 | 11–12 | Linha informativa `faixa`; parâmetro de regimes em `calculate`/`project`/sensibilidade | direct | Complete | `pytest -m "not db"` | 169 passed com os 4 goldens intactos |
| 6 | 13 | Cliente MCP `cnpj_lookup.py` | direct | Complete | `test_cnpj_lookup.py` + 1 chamada real | resposta real = lista com 1 objeto da BrasilAPI; sócios descartados |
| 7 | 14–15 | Pipeline (job `lookup_company`, rápido em suggest/project, sem R1–R7), config, db, PDF | direct | Complete | `test_rapido_pipeline.py` | fluxo completo em 4,6 s; PDF "planejamento rápido" com CNAE, faixa e origem |
| 8 | 16–21 | Testes, fixtures, golden `rapido_2027` + teste | direct | Complete | `pytest tests/test_decisao_golden.py` | golden aprovado em 2026-09-28 reproduzido |
| 9 | 22–25 | Tipos, rótulos, schemas, criação com tipo, CNAE, digitação, planejamento só 2027, tabela de faixa | direct | Complete | typecheck, vitest, `next build`, smoke HTTP | 22 vitest; páginas 200 com os textos esperados |
| 10 | 26 | `verify.mjs` (amostra RBT12.pdf), README, KB `cnae-e-anexo.md` | direct | Complete | `npm run verify` | PASS |

---

## Files Changed

| File | Action | Notes |
|---|---|---|
| `supabase/migrations/20260926000005_planejamento_rapido.sql` | Create | `tax_cases.kind`; doc_type da declaração; `companies.cnae_*`; `manual_values` + RLS + imutabilidade; RPCs `enter_manual_values`, `clear_manual_values`, `request_company_lookup`, `set_company_cnae`, `rapido_blockers`; `homologate_case`, `request_calculation` e `request_projection` por tipo |
| `supabase/tests/planejamento_rapido.test.sql` | Create | 20 asserts |
| `services/worker/rules/cnae_anexos.json` | Create | 82 prefixos, versão 2026.1.0, `verificado: false` |
| `services/worker/src/worker/engine/cnae.py`, `engine/quick_view.py`, `parsers/declaracao_faturamento.py`, `cnpj_lookup.py` | Create | tabela, adaptador, parser, cliente MCP |
| `services/worker/src/worker/models.py`, `services/worker/src/worker/classify.py`, `services/worker/src/worker/validations.py`, `services/worker/src/worker/config.py`, `services/worker/src/worker/db.py`, `services/worker/src/worker/pipeline.py`, `services/worker/src/worker/report_pdf.py`, `parsers/__init__.py` | Modify | tipo novo, período MM/AAAA, validações, CNAE, job, rápido no pipeline, PDF |
| `services/worker/src/worker/engine/simples.py`, `services/worker/src/worker/engine/calculate.py`, `services/worker/src/worker/engine/decision.py`, `services/worker/src/worker/engine/projection.py`, `services/worker/src/worker/engine/sensitivity.py` | Modify | linha `faixa`; parâmetro de regimes; `synthetic_month` público |
| `services/worker/tests/test_declaracao_faturamento.py`, `services/worker/tests/test_cnae.py`, `services/worker/tests/test_cnpj_lookup.py`, `services/worker/tests/test_quick_view.py`, `services/worker/tests/test_rapido_pipeline.py` | Create | — |
| `services/worker/tests/golden/rapido_2027.json`, `tests/test_decisao_golden.py`, `tests/conftest.py` | Create / Modify | golden aprovado (sem dados pessoais); fixtures do rápido |
| `apps/web/src/lib/database.types.ts`, `apps/web/src/lib/format.ts`, `apps/web/src/lib/schemas.ts`, `apps/web/src/lib/schemas.test.ts` | Modify | tipos, rótulos, `manualValuesSchema`, `cnaeSchema`, tipo do dossiê |
| `apps/web/src/components/CompanyCnae.tsx`, `apps/web/src/components/ManualValuesForm.tsx`, `apps/web/src/components/SimplesBandTable.tsx` | Create | CNAE, digitação, faixa |
| `apps/web/src/app/(app)/cases/new/page.tsx`, `apps/web/src/app/(app)/cases/actions.ts`, `apps/web/src/app/(app)/cases/[id]/page.tsx`, `apps/web/src/app/(app)/cases/[id]/planning/page.tsx`, `apps/web/src/app/(app)/cases/[id]/planning/projection/[projId]/page.tsx`, `components/ProjectionTable.tsx` | Modify | criação com tipo, ações, checklist, só Projetar 2027, tabela de faixa |
| `scripts/verify.mjs`, `README.md`, `kb/simples-nacional/index.md`, `kb/simples-nacional/concepts/cnae-e-anexo.md` | Modify / Create | amostra no gate, seção do ciclo 5, KB |

---

## Drift Detected

| File | Change outside manifest | Decision | Reason |
|---|---|---|---|
| `services/worker/src/worker/engine/sensitivity.py` | parâmetro de regimes repassado ao `calculate` | registrado | sem ele a sensibilidade do rápido calcularia o Real |
| `apps/web/src/components/ProjectionTable.tsx` | tipo `ProjectionLine` com `origin` | registrado | a tabela de faixa lê a origem das linhas |
| `supabase/migrations/…` (RPCs `clear_manual_values`, `rapido_blockers`) | funções não listadas no Design | registrado | remover digitação e mostrar os bloqueios na tela |

---

## Verification Results

### Incremental Verification

| Step | Command | Result | Evidence |
|---|---|---|---|
| Migration | `npx supabase migration up`; `npx supabase test db` | Pass | 108 → 128 asserts |
| Parser e validações | `pytest tests/test_declaracao_faturamento.py` | Pass | 4 passed (inclui CNPJ divergente com banco) |
| Tabela CNAE | `pytest tests/test_cnae.py` | Pass | 9 passed |
| Cliente MCP | `pytest tests/test_cnpj_lookup.py` + chamada real | Pass | 8 passed; formato real conferido |
| Adaptador e motor | `pytest tests/test_quick_view.py`; `pytest -m "not db"` | Pass | 9 passed; 169 passed sem regressão |
| Integração | `pytest tests/test_rapido_pipeline.py` | Pass | 3 passed; projeção 4,6 s (97 execuções) |
| Golden | `pytest tests/test_decisao_golden.py` | Pass | 3 passed (2026, 2027, rápido) |
| Web | typecheck; `vitest run` | Pass | 22 passed |
| Smoke E2E | script autenticado em dossiê próprio `ad17fd06…` | Pass | ver Complementary Checks |

### Verify Gate

| Attribute | Value |
|---|---|
| **Kind** | test |
| **Command / Method** | `npm run verify` |
| **Exit / Result** | 0 |
| **Status** | Green |
| **Evidence** | pytest 218 passed; pgTAP Files=6 Tests=128 Result: PASS; typecheck ok; vitest 22 passed — "VERIFY GATE: PASS" (após correções da revisão e golden aprovado) |

### Manual UX Receipt

N/A

### Complementary Checks

| Check | Command / Method | Status | Evidence |
|---|---|---|---|
| Lint | N/A | N/A | o projeto não define lint |
| Typecheck | `npm run typecheck` | Pass | sem erros |
| Tests | `npm run verify` | Pass | ver Verify Gate |
| Build / Compile | `next build`; `docker build` + `docker run` | Pass | rotas compiladas; imagem carrega a tabela CNAE (2026.1.0, 82 prefixos) |
| Smoke E2E | dossiê `ad17fd06-ae22-4daa-ab6e-6c6eebb0d1ff` | Pass | 7 PDFs extraídos; digitação em mês com PDF recusada; perfil Anexo I sugerido; Projetar 2026 recusado; projeção 2027 em 13,3 s = golden; analista aprova → 42501; PDF 18.549 bytes com SHA-256 conferido; RLS 0/0; páginas 200 |

---

## Acceptance Test Verification

| AT | Description | Status | Evidence |
|---|---|---|---|
| AT-501 | Declaração extraída com origem e soma = Total Geral | Pass | `test_declaracao_is_parsed_with_12_months_and_total` |
| AT-502 | Soma divergente falha e bloqueia | Pass | `test_tampered_month_fails_total_check`; `rapido_blockers` inclui validação falha |
| AT-503 | CNPJ divergente | Pass | `test_declaracao_with_other_cnpj_is_blocked` |
| AT-504 | Sem 12 meses consecutivos bloqueia | Pass | `test_rapido_without_revenue_or_folha_is_blocked`; pgTAP |
| AT-505 | Digitação gravada com autor e usada no snapshot | Pass | `test_rapido_flow`; `test_manual_values_make_a_realized_month`; pgTAP |
| AT-506 | Digitação em mês com PDF recusada | Pass | `test_rapido_flow`; smoke |
| AT-507 | Sem folha ou DRE bloqueia | Pass | `test_rapido_without_revenue_or_folha_is_blocked` |
| AT-508 | Consulta n8n grava CNAE sem sócios | Pass | `test_extracts_only_cnae_and_name`; `test_rapido_flow`; chamada real |
| AT-509 | Falha da automação → CNAE digitado | Pass | `test_failures_raise_lookup_error`; `test_lookup_failure_allows_typed_cnae` |
| AT-510 | Perfil sugerido pelo CNAE | Pass | `test_suggestions_for_rapido`; smoke |
| AT-511 | CNAE fora da tabela sem sugestão | Pass | `test_unknown_cnae_leaves_profile_without_suggestion` |
| AT-512 | Três alternativas, sem Real | Pass | `test_three_alternatives_with_band`; `test_rapido_flow`; smoke |
| AT-513 | Faixa, nominal, dedução e efetiva na tela, memória e PDF | Pass | `test_three_alternatives_with_band`; PDF do `test_rapido_flow`; smoke (tela) |
| AT-514 | RBT12 > 4,8 mi tira o Simples | Pass (com ressalva) | `test_revenue_above_limit_makes_simples_ineligible` — ver Deviations |
| AT-515 | Premissa pendente bloqueia | Pass | `test_pending_profile_blocks`; `blocking()` do pipeline |
| AT-516 | ≤ 60 s | Pass | integração 4,6 s; smoke 13,3 s |
| AT-517 | PDF "planejamento rápido" com CNAE, faixa e origem | Pass | `test_rapido_flow` (texto extraído) |
| AT-518 | Golden aprovado | Pass | `test_rapido_2027_matches_approved_golden`; aprovação: Diekson Bernardes, 2026-09-28 |
| AT-519 | Goldens anteriores e dossiê completo inalterados | Pass | `npm run verify` |

Golden `rapido_2027` (CBS 9,5%, IBS 0,1%, crescimento 5%, créditos informados, ST/monofásico 0%): Simples 445.983,00 < híbrido 532.676,31 < Presumido 536.469,60; recomendado Simples, 19,44% abaixo do híbrido; 5ª faixa jan–jul e 6ª faixa ago–dez de 2027.

---

## Advisor Ledger

| # | Phase | Note | Severity | Decision | Evidence |
|---:|---|---|---|---|---|
| 1 | post-build | `rapido_blockers` sem checagem de escritório (vazamento de nomes de arquivo entre escritórios) | HIGH | APPLIED | `is_member` na função; assert pgTAP |
| 2 | post-build (smoke) | Grupo de premissas `rapido` ausente da tela de planejamento | HIGH | APPLIED | grupo na ordem + grupos desconhecidos exibidos no fim; página conferida |
| 3 | build | Base de créditos sugerida como zero sem livro/balancete | HIGH | APPLIED | sugestão nula ("informar as compras"); teste |
| 4 | build | Parâmetro de regimes sombreado por variável local em `calculate` | HIGH | APPLIED | renomeado para `only`; teste |
| 5 | build | Perfil sugerido sem `choices` falhava na confirmação | MEDIUM | APPLIED | `choices` reaproveitadas; teste de integração |
| 6 | post-build | Consulta de CNAE sem deduplicação (cota da BrasilAPI) | LOW | APPLIED | recusa com consulta na fila; assert pgTAP |

---

## Issues Encountered

| # | Issue | Resolution | Impact |
|---:|---|---|---|
| 1 | Heredocs longos quebrados pelo shell do Windows | scripts gravados pela ferramenta de arquivos | nenhum |
| 2 | Sessão interrompida por limite de uso no meio do smoke | retomada com o mesmo worker e site | nenhum |
| 3 | Validação `taxes`/`profile` do banco avalia subconsulta mesmo com tipo errado | sugestão passa a enviar `choices` | nenhum |
| 4 | Worker em segundo plano disputa jobs dos testes | parado antes do Verify Gate | nenhum |

---

## Deviations from Design

| Deviation | User Decision | Reason | Impact |
|---|---|---|---|
| AT-514: acima de R$ 4,8 mi o Simples sai como "não calculado" (RBT12 acima da última faixa) com alerta de teto, não como "inelegível" | registrado neste relatório | motor inalterado (elegibilidade herdada do ciclo 2) | efeito igual: Simples fora do ranking, Presumido recomendado |
| Soma de % ST + % monofásico > 100% recusada no motor (projeção falha com mensagem), não na RPC de confirmação | registrado | evita regra especial em `confirm_assumption` | erro aparece ao projetar |
| Resposta de `Consultar_CNPJ` é lista com um objeto (A-501 previa objeto) | registrado | conferido na chamada real | cliente aceita os dois |
| Fator R: `folha.folha_12m` sugerida pela média dos meses informados × 12 | registrado | sem série 2.3 do PGDAS-D | premissa confirmável |
| ICMS no regime normal: proxy do DAS; base de CBS/IBS usa esse ICMS | registrado (Decision 8) | sem ICMS apurado | ressalva; ST = 0% eleva o ICMS |
| Receita bruta da DRE digitada é informativa (não conferida com o faturamento) | registrado | fora dos MUST | nenhum no cálculo |

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
