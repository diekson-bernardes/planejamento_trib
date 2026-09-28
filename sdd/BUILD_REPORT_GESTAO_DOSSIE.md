# BUILD REPORT: Gestão do dossiê (pós-ciclo 5)

> Implementation report for Gestão do dossiê — razão social preenchida pela consulta do CNPJ; excluir dossiê, arquivo e empresa; editar período/tipo do dossiê e dados da empresa; reabrir dossiê homologado.

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | GESTAO_DOSSIE |
| **Date** | 2026-09-28 |
| **Author** | SDD Build by RDD |
| **BRAINSTORM** | N/A — requisito direto do usuário na sessão do ciclo 5 (sem fase de Brainstorm) |
| **DEFINE** | N/A — escopo fechado por perguntas na sessão (ver Mode Selection) |
| **DESIGN** | N/A — decisões registradas neste relatório |
| **Status** | Complete |

---

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 14 arquivos (migration, pgTAP, worker, testes, web, README) |
| Cross-file coupling | Médio — gatilhos de imutabilidade dos ciclos 1–3, fila de jobs, Storage e telas do dossiê |
| Security surface | Alta — exclusão/reabertura liberam proteções (append-only, homologado imutável, recomendação emitida) |
| LLM Prompts | None |
| Independent volume | Baixo |
| Context-rot risk | Baixo |
| Runtime capabilities | default |

**Recommendation:** default, na mesma branch do ciclo 5, com testes, Verify Gate e relatório próprios.

**User decision:** default, confirmado em 2026-09-28 junto com o escopo abaixo.

Escopo decidido pelo usuário:
- Razão social: opção (a) — opcional no cadastro, preenchida pela consulta à Receita (job do worker).
- Excluir: dossiê inteiro, arquivo enviado e empresa. Editar: período do dossiê, dados da empresa e tipo do dossiê.
- Dossiê homologado: **qualquer membro do escritório, sem restrição**, pode reabrir ou excluir — inclusive snapshot,
  recomendações e PDFs emitidos (alternativas com proteções ou restritas ao responsável técnico foram apresentadas e recusadas).
- Commit do ciclo 5 antes (`478c821`), esta mudança em seguida.

**Pre-build review:** No — revisão feita após a implementação, com teste de sistema.

---

## Summary

| Metric | Value |
|---|---|
| **Tasks Completed** | 6/6 |
| **Files Created** | 4 (migration, pgTAP, teste de integração, este relatório) |
| **Files Modified** | 12 |
| **Files Deleted** | 0 |
| **Verification Commands Run** | 15 (`supabase migration up`, pgTAP ×3, checagem real do Storage, pytest db, typecheck ×3, vitest, smoke no sistema local, `next build`, `npm run verify`) |
| **Verify Gate** | Green |
| **Execution Mode** | default |

---

## Task Execution

| # | Manifest | Task | Mode | Status | Verification | Evidence |
|---:|---|---|---|---|---|---|
| 1 | migration | `20260928000006_gestao_dossie.sql`: liberação controlada das proteções (`app.purge_case`), RPCs `delete_case`, `reopen_case`, `update_case`, `delete_source_file`, `update_company`, `delete_company`, `companies.razao_social_pendente`, job `purge_storage`, homologação bloqueada com razão social pendente | direct | Complete | `npx supabase migration up`; pgTAP | aplicada; 128 asserts anteriores verdes |
| 2 | pgTAP | `gestao_dossie.test.sql` (14 asserts) | direct | Complete | `npx supabase test db` | Files=7 Tests=142 PASS |
| 3 | worker | `storage.py` (`list_prefix`, `delete`), job `purge_storage`, razão social pela consulta em `db.save_company_cnae` | direct | Complete | checagem no Storage local | 4 objetos (com subpastas) listados e apagados |
| 4 | teste | `test_gestao_dossie.py` (3 fluxos com banco) | direct | Complete | `pytest tests/test_gestao_dossie.py` | 3 passed |
| 5 | web | ações `updateCase`, `reopenCase`, `deleteCase`, `deleteSourceFile`, `updateCompany`, `deleteCompany`; cadastro só com CNPJ; card "Empresa"; "Dados do dossiê"; "Reabrir ou excluir"; "Empresas sem dossiê"; `btn-danger` | direct | Complete | typecheck; vitest; smoke | 25 vitest; páginas 200 |
| 6 | docs | README (seção "Gestão do dossiê") e este relatório | direct | Complete | `npm run verify` | PASS |

---

## Files Changed

| File | Action | Notes |
|---|---|---|
| `supabase/migrations/20260928000006_gestao_dossie.sql` | Create | proteções com liberação por dossiê; 6 RPCs; job `purge_storage`; razão social pendente |
| `supabase/tests/gestao_dossie.test.sql` | Create | outro escritório bloqueado; DELETE direto negado mesmo com a transação marcada; motivo obrigatório |
| `services/worker/src/worker/storage.py` | Modify | `list_prefix` (recursivo) e `delete` no Storage |
| `services/worker/src/worker/pipeline.py` | Modify | job `purge_storage` (só caminhos do próprio escritório e dossiê) |
| `services/worker/src/worker/db.py` | Modify | razão social da consulta quando pendente |
| `services/worker/tests/conftest.py`, `services/worker/tests/test_gestao_dossie.py` | Modify / Create | Storage em memória com listagem/exclusão; fluxos de gestão |
| `apps/web/src/lib/database.types.ts`, `apps/web/src/lib/schemas.ts`, `apps/web/src/lib/schemas.test.ts` | Modify | tipos; `reasonSchema`, `updateCaseSchema`, `companyNameSchema`; razão social opcional |
| `apps/web/src/app/(app)/cases/actions.ts` | Modify | ações de gestão; cadastro só com CNPJ dispara a consulta |
| `apps/web/src/app/(app)/cases/new/page.tsx`, `apps/web/src/app/(app)/cases/[id]/page.tsx`, `apps/web/src/components/CompanyCnae.tsx`, `apps/web/src/app/globals.css` | Modify | telas de gestão |
| `README.md` | Modify | seção "Gestão do dossiê" |

---

## Drift Detected

| File | Change outside manifest | Decision | Reason |
|---|---|---|---|
| Regra de imutabilidade dos ciclos 1–3 | dossiê homologado e recomendação emitida passam a poder ser apagados | aprovado pelo usuário (2026-09-28) | requisito explícito "qualquer membro, sem restrição" |
| `homologate_case` | passa a chamar `rapido_blockers` para todos os tipos | registrado | bloquear homologação com razão social pendente também no dossiê completo |

---

## Verification Results

### Incremental Verification

| Step | Command | Result | Evidence |
|---|---|---|---|
| Migration | `npx supabase migration up`; `npx supabase test db` | Pass | 128 → 142 asserts |
| Storage real | script com `SupabaseStorage` no Storage local | Pass | subpastas listadas; 4 → 0 objetos |
| Integração | `pytest tests/test_gestao_dossie.py` | Pass | 3 passed |
| Web | typecheck; `vitest run` | Pass | 25 passed |
| Sistema local | smoke com site, worker e Storage | Pass | ver Complementary Checks |

### Verify Gate

| Attribute | Value |
|---|---|
| **Kind** | test |
| **Command / Method** | `npm run verify` |
| **Exit / Result** | 0 |
| **Status** | Green |
| **Evidence** | pytest 223 passed; pgTAP Files=7 Tests=142 Result: PASS; typecheck ok; vitest 25 passed — "VERIFY GATE: PASS" |

### Manual UX Receipt

N/A

### Complementary Checks

| Check | Command / Method | Status | Evidence |
|---|---|---|---|
| Lint | N/A | N/A | o projeto não define lint |
| Typecheck | `npm run typecheck` | Pass | sem erros |
| Tests | `npm run verify` | Pass | ver Verify Gate |
| Build / Compile | `next build` | Pass | rotas compiladas |
| Smoke no sistema local | site + worker + Storage, sem chamar a automação n8n | Pass | empresa só com CNPJ → razão social pendente e homologação bloqueada; razão social gravada; dossiê editado para rápido; dossiê do ciclo 5 (`ad17fd06…`, com PDF emitido) reaberto (PDF 1 → 0 no Storage) e excluído (7 → 0 objetos); empresa excluída; auditoria com `case.reopened`, `case.deleted`, `case.updated`, `company.updated`, `company.deleted` |

---

## Acceptance Test Verification

| AT | Description | Status | Evidence |
|---|---|---|---|
| G-01 | Empresa cadastrada só com CNPJ recebe a razão social da consulta | Pass | `test_legal_name_comes_from_cnpj_lookup` |
| G-02 | Razão social digitada nunca é sobrescrita pela consulta | Pass | `test_legal_name_comes_from_cnpj_lookup` |
| G-03 | Razão social pendente bloqueia a homologação | Pass | `test_legal_name_comes_from_cnpj_lookup`; smoke |
| G-04 | Reabrir descarta snapshot, projeções, recomendações e PDF, mantém premissas, exige motivo | Pass | `test_reopen_edit_delete_case_and_company`; smoke |
| G-05 | Excluir arquivo remove valores e objeto do Storage | Pass | `test_reopen_edit_delete_case_and_company`; pgTAP |
| G-06 | Editar período/tipo; rápido exige 12 meses; completo descarta digitação | Pass | `test_reopen_edit_delete_case_and_company`; pgTAP |
| G-07 | Excluir dossiê homologado com PDF emitido por qualquer membro | Pass | `test_delete_homologated_case_with_emitted_pdf` |
| G-08 | Excluir empresa só sem dossiês | Pass | `test_reopen_edit_delete_case_and_company`; pgTAP |
| G-09 | Outro escritório não exclui, edita nem reabre; DELETE direto negado | Pass | `gestao_dossie.test.sql` |
| G-10 | Auditoria registra motivo e autor; continua somente inclusão | Pass | testes de integração; pgTAP (`delete from audit_events` negado) |

---

## Advisor Ledger

None — no formal external review; riscos tratados na implementação (liberação das proteções só dentro das funções, verificada por pgTAP; `purge_storage` limitado aos caminhos do escritório e do dossiê do job).

---

## Issues Encountered

| # | Issue | Resolution | Impact |
|---:|---|---|---|
| 1 | Revogar o auxiliar `purging_case` quebraria edições diretas de `tax_cases` (o gatilho roda como o usuário) | auxiliar mantido executável (só lê a marca da transação) | nenhum |
| 2 | CNPJ do teste pgTAP já existia no seed | CNPJ válido sem uso (99887766000105) | nenhum |
| 3 | Usuário relatou PDFs "na fila" e razão social/CNAE não preenchidos: nenhum worker rodando; `npm run dev:worker` falhava (pacote `worker` não instalado) e o worker não lia o `.env` da raiz | worker carrega o `.env` da raiz sem sobrescrever o ambiente; `npm run dev:worker` usa `scripts/dev-worker.mjs` (PYTHONPATH para `services/worker/src`); `.env` local criado (fora do Git); `.env.example` e README atualizados | fila processada: razão social e CNAE da empresa do usuário vieram da automação; "Faturamento LP.pdf" extraído com validações aprovadas |
| 4 | Os testes de integração consumiam jobs de qualquer escritório — o Verify Gate processou a extração e a consulta do usuário com a configuração de teste (FILE_NOT_FOUND e URL vazia) | `claim_job`/`Pipeline` com filtro opcional de escritório, usado em todos os testes; teste de regressão; jobs do usuário recolocados na fila | nenhum após a correção |
| 5 | A empresa fictícia do seed (`c0000000-…-0a`), fixture do pgTAP, foi excluída pelo usuário pela tela (auditoria 13:01, admin.a) | recriada a partir do `seed.sql` no banco local | pgTAP depende dela; excluí-la de novo quebra o Verify Gate local |

---

## Deviations from Design

| Deviation | User Decision | Reason | Impact |
|---|---|---|---|
| Exclusão é física (dados e PDFs apagados), só a auditoria permanece | "Qualquer membro, sem restrição" | escolha do usuário | recomendações emitidas e PDFs deixam de existir após excluir/reabrir |
| Reabrir mantém as premissas | registrado | a nova sugestão reaproveita as confirmadas quando a sugestão não muda | nenhum |

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
