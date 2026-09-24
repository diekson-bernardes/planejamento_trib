# BUILD REPORT: Importação e Conciliação de Documentos Fiscais

> Implementation report for Importação e Conciliação de Documentos Fiscais

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | IMPORTACAO_CONCILIACAO |
| **Date** | 2026-09-24 |
| **Author** | SDD Build by RDD |
| **BRAINSTORM** | `sdd/BRAINSTORM_IMPORTACAO_CONCILIACAO.md` |
| **DEFINE** | `sdd/DEFINE_IMPORTACAO_CONCILIACAO.md` |
| **DESIGN** | `sdd/DESIGN_IMPORTACAO_CONCILIACAO.md` (v1.1) |
| **Status** | Complete |

Branch: `feat/importacao-conciliacao` (criada a partir de `master`, commit `a374529`). Nenhum commit foi feito no Build (não solicitado).

---

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 85 |
| Cross-file coupling | High: o schema SQL (migrations) é contrato do worker Python e do site; tipos gerados do banco usados em todo o web |
| Security surface | High: RLS multi-tenant, políticas de Storage, chave de serviço no worker/admin, imutabilidade e auditoria |
| LLM prompt items | None (`LLM Prompts: false` no DEFINE e no DESIGN) |
| Independent volume | Médio: componentes do web e golden JSON independentes; migrations/worker sequenciais |
| Context-rot risk | Médio: manifest grande, mitigado por sumarização automática do contexto |
| Runtime capabilities | default disponível; ralph e briefs disponíveis via subagentes |

**Recommendation:** default — coerência cross-file entre SQL, worker e web e itens de segurança pesam mais do que contexto limpo por tarefa.

**User decision:** default (confirmado em 2026-09-24).

**Pre-build review:** Not available — nenhuma ferramenta de revisão externa formal pré-build; o usuário escolheu revisão pós-build (code review + security review).

---

## Summary

| Metric | Value |
|---|---|
| **Tasks Completed** | 85/85 |
| **Files Created** | 89 (85 do manifest + 4 de tooling aprovados) |
| **Files Modified** | 0 |
| **Files Deleted** | 0 pelo Build (ver Issues: `prompts/prompt01.md` aparece deletado no working tree sem ação do Build) |
| **Verification Commands Run** | 24 |
| **Verify Gate** | Green |
| **Execution Mode** | default |

---

## Task Execution

| # | Manifest ID | Task | Executor | Status | Verification | Evidence |
|---:|---:|---|---|---|---|---|
| 1 | 1–4 | Create `.gitignore`, `.env.example`, `package.json`, `README.md` | direct | Complete | `git check-ignore -v apps/web/.env.local`; `npm install` | `.env.*` e `docs/Amostras/` ignorados; 99 pacotes, 0 vulnerabilidades |
| 2 | 5 | Create `supabase/config.toml` (supabase init; `enable_signup=false`) | direct | Complete | `npx supabase start` | exit 0; 7 migrations + seed aplicados |
| 3 | 6–12 | Create migrations tenancy, companies/cases, files/jobs, extraction, reconciliation, snapshot/audit, storage | direct | Complete | `npx supabase db reset` | exit 0, todas aplicadas (3 execuções) |
| 4 | 13 | Create `supabase/seed.sql` (escritórios A/B, usuários e mapeamentos fictícios) | direct | Complete | `npx supabase db reset` | seed aplicado |
| 5 | 14–15 | Create `supabase/tests/rls.test.sql`, `homologation.test.sql` | direct | Complete | `npx supabase test db` | 41/41 pgTAP PASS |
| 6 | 16–18 | Create `pyproject.toml`, `Dockerfile`, `worker/__init__.py` | direct | Complete | `docker build services/worker` + import check | exit 0; `imports ok` |
| 7 | 19–25 | Create config, models, errors, pdf/numbers, pdf/layout, classify, parsers/base | direct | Complete | `pytest tests/test_numbers.py tests/test_classify.py` | incluídos nos 73 passed |
| 8 | 26–30 | Create parsers PGDAS-D, Folha, DRE, Balancete e registro | direct | Complete | smoke dos parsers nas 6 amostras | 957 valores; 42 validações internas pass |
| 9 | 31–32 | Create `validations.py`, `reconcile.py` | direct | Complete | `pytest tests/test_validations.py tests/test_reconcile.py` | R1–R6 ago/2026 diff 0,00 |
| 10 | 33–37 | Create db, storage, export_xlsx, pipeline, main | direct | Complete | `pytest tests/test_pipeline.py`; worker real no smoke E2E | pass; worker real processou 6 PDFs |
| 11 | 38–45 | Create conftest e 7 golden JSON (sem PII) | direct | Complete | geração + conferência com conciliação manual do Brainstorm | valores de referência idênticos |
| 12 | 46–53 | Create 8 arquivos de teste do worker | direct | Complete | `python -m pytest services/worker/tests -q` | 73 passed |
| 13 | 54–58 | Create `apps/web/package.json`, tsconfig, next.config, vitest.config, database.types | direct | Complete | `npm run db:types`; `tsc --noEmit` | 931 linhas de tipos; typecheck exit 0 |
| 14 | 59–65 | Create supabase clients (server/client/admin), hash, schemas, format, middleware | direct | Complete | `vitest run`; `next build` | 11 testes pass; build exit 0 |
| 15 | 66–82 | Create layout, globals.css, login, shell, páginas de dossiês, actions, componentes, rota de exportação, admin | direct | Complete | `next build` + smoke HTTP autenticado | 12/12 checagens de página |
| 16 | 83–84 | Create `schemas.test.ts`, `hash.test.ts` | direct | Complete | `npm run test --workspace apps/web` | 11 passed |
| 17 | 85 | Create `scripts/verify.mjs` | direct | Complete | `npm run verify`; negativo com `SAMPLES_DIR` inexistente | exit 0; negativo exit 1 |

---

## Files Changed

| File | Action | Manifest ID | Verified | Notes |
|---|---|---:|---|---|
| `.gitignore`, `.env.example`, `package.json`, `README.md` | Create | 1–4 | Yes | Supabase CLI como devDependency (Design v1.1) |
| `supabase/config.toml`, `supabase/seed.sql` | Create | 5, 13 | Yes | cadastro público desativado |
| `supabase/migrations/20260924000001..7_*.sql` | Create | 6–12 | Yes | 7 migrations |
| `supabase/tests/rls.test.sql`, `homologation.test.sql` | Create | 14–15 | Yes | 22 + 19 asserções |
| `services/worker/pyproject.toml`, `Dockerfile` | Create | 16–17 | Yes | imagem construída |
| `services/worker/src/worker/*.py` (config, models, errors, classify, validations, reconcile, db, storage, export_xlsx, pipeline, main, `__init__`) | Create | 18–21, 24, 31–37 | Yes | |
| `services/worker/src/worker/pdf/numbers.py`, `pdf/layout.py` | Create | 22–23 | Yes | |
| `services/worker/src/worker/parsers/*.py` (base, pgdas, folha_alterdata, dre_alterdata, balancete_alterdata, `__init__`) | Create | 25–30 | Yes | versões `*-1.0.0` |
| `services/worker/tests/conftest.py`, `golden/*.json` (7), `test_*.py` (8) | Create | 38–53 | Yes | golden só com campos, códigos e valores |
| `apps/web/package.json`, `tsconfig.json`, `next.config.ts`, `vitest.config.ts` | Create | 54–57 | Yes | `type: module`; TypeScript 5.9.3 |
| `apps/web/src/lib/*` (database.types, supabase/server, client, admin, hash, schemas, format + 2 testes) | Create | 58–64, 83–84 | Yes | |
| `apps/web/src/middleware.ts` | Create | 65 | Yes | aviso de depreciação do Next 16 (ver Issues) |
| `apps/web/src/app/**` (layout, globals.css, login, (app)/layout, cases, new, [id], review, reconciliation, actions, admin, api export) | Create | 66–73, 75, 78, 80–82 | Yes | |
| `apps/web/src/components/*` (UploadDropzone, ValueTable, StatusBadge, ReconciliationTable) | Create | 74, 76–77, 79 | Yes | |
| `scripts/verify.mjs` | Create | 85 | Yes | Verify Gate |
| `apps/web/postcss.config.mjs`, `package-lock.json`, `supabase/.gitignore`, `.claude/launch.json` | Create | — | Yes | tooling aprovado (ver Drift) |

---

## Drift Detected

| # | Task / Path | Drift | Decision | Action |
|---:|---|---|---|---|
| 1 | `apps/web/postcss.config.mjs` | Tailwind v4 exige config PostCSS fora do manifest | approved deviation (usuário, antes da 1ª alteração) | criado |
| 2 | `package-lock.json`, `apps/web/next-env.d.ts`, `supabase/.gitignore` | artefatos gerados por npm/Next/Supabase CLI | approved deviation (usuário) | mantidos; `next-env.d.ts` no `.gitignore` |
| 3 | `.claude/launch.json` | config do preview do Claude Code para o smoke visual (não é código do produto) | approved deviation (tooling de verificação) | criado; pode ser removido sem impacto |
| 4 | `homologate_case` | Design (Decision 6) previa `SECURITY INVOKER`; implementado `SECURITY DEFINER` com checagem explícita `is_member` | approved deviation (mais restritivo; contrato RPC inalterado) | usuários não recebem INSERT em snapshots nem UPDATE de status |
| 5 | Auditoria `write.denied` | Observability do Design citava auditar negações; impossível gravar em transação que sofre rollback | false positive de spec | negação registrada pelo erro retornado e logs do Postgres |

---

## Verification Results

### Incremental Verification

| Task | Command / Method | Result | Evidence |
|---|---|---|---|
| Migrations + seed | `npx supabase start` / `npx supabase db reset` | Pass | 7 migrations + seed aplicados |
| pgTAP (1ª versão) | `npx supabase test db` | Pass | 39/39 |
| Parsers | script de smoke nas 6 amostras | Pass | 125/127/129/165/28/383 valores; 42 validações pass |
| Golden × conciliação manual | comparação com a conferência independente do Brainstorm | Pass | R1 203.180,77; R2 23.430,47; R3 2.963,53; R4 2.706,49; R5 34.212,13; R6 38.975,46 — diff 0,00 |
| Worker | `python -m pytest services/worker/tests -q` | Pass | 72 passed (depois 73 com o teste de PDF corrompido) |
| Web | `tsc --noEmit`; `vitest run` | Pass | exit 0; 11 passed |
| Web build | `npm run build --workspace apps/web` | Pass | 9 rotas compiladas |
| Imagem do worker | `docker build` + `python -c "import worker.pipeline"` | Pass | exit 0 |
| E2E real (Storage + worker + RLS) | smoke supabase-js com usuários do seed | Pass | 6 PDFs extraídos, R1–R6 ok, homologação, XLSX 80 KB, B negado |
| Páginas autenticadas | smoke HTTP com cookies `@supabase/ssr` | Pass | 12/12 |
| UI sem sessão | navegador: `/cases` → `/login` | Pass | redirecionamento e estilos Tailwind ok |
| Gate negativo | `SAMPLES_DIR=C:\nao-existe node scripts/verify.mjs` | Pass (falha esperada) | exit 1 com mensagem de amostras ausentes |

### Verify Gate

| Attribute | Value |
|---|---|
| **Kind** | test |
| **Command / Method** | `npm run verify` |
| **Exit / Result** | 0 |
| **Status** | Green |
| **Evidence** | Execução final após correções do review: Docker ok; Supabase ok; pytest `73 passed`; pgTAP `Files=2, Tests=41, Result: PASS`; typecheck exit 0; vitest `11 passed`; saída `VERIFY GATE: PASS`. Houve uma execução intermediária red (exit 1, 2 asserções pgTAP) corrigida na 1ª tentativa da retry ladder |

### Manual UX Receipt

N/A

### Complementary Checks

| Check | Command / Method | Status | Evidence |
|---|---|---|---|
| Lint | N/A | N/A | projeto sem linter configurado (não previsto no Design) |
| Typecheck | `npm run typecheck --workspace apps/web` | Pass | exit 0 |
| Tests | pytest + pgTAP + vitest (via gate) | Pass | 73 + 41 + 11 |
| Build / Compile | `npm run build --workspace apps/web`; `docker build services/worker` | Pass | ambos exit 0 |

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|---|---|---|---|
| AT-001 | Classificação do PGDAS-D com CNPJ, período e hash | Pass | `test_classify.py` (6/6 amostras); `source_files.sha256` gravado |
| AT-002 | Extração do PGDAS-D 08/2026 (RPA, RBT12, séries, tributos) | Pass | `test_parsers.py` golden + `test_key_values_of_august` |
| AT-003 | Extração da folha (rubricas, totais, GPS/FGTS/IRRF) | Pass | golden `folha_202608.json`; totais 34.212,13 / 4.361,13 / 29.851,00 |
| AT-004 | Extração da DRE e resultado 126.353,14 | Pass | golden `dre_202608.json` |
| AT-005 | Extração do balancete (95 contas × 4 colunas) | Pass | golden `balancete_202608.json` |
| AT-006 | Origem (arquivo, página, bbox, versão do parser) em cada valor | Pass | `test_every_value_has_origin`; colunas NOT NULL no banco |
| AT-007 | Validações internas | Pass | `test_validations.py` (pass nas amostras; adulteração falha) |
| AT-008 | Conciliação R1–R6 | Pass | `test_reconcile.py` + E2E real (todas ok, diff 0) |
| AT-009 | Divergência acima da tolerância bloqueia a homologação | Pass | `test_tolerance_boundary`; pgTAP `homologation.test.sql` |
| AT-010 | PDF sem texto rejeitado | Pass | `test_classify.py`, `test_pipeline.py` (status rejected, NO_TEXT) |
| AT-011 | Duplicidade por SHA-256 | Pass | `test_duplicate_hash_in_same_case_is_rejected`; E2E código 23505 |
| AT-012 | CNPJ divergente | Pass | `test_cnpj_mismatch_blocks_file` |
| AT-013 | Não classificado + classificação manual | Pass | `test_unknown_document_is_unclassified`; reclassificação reenfileira (trigger) |
| AT-014 | Layout não reconhecido sem valores parciais | Pass | `test_missing_anchor_fails_without_partial_values`; `test_layout_change_fails_with_parser_version` |
| AT-015 | Reprocessamento idempotente | Pass | `test_extraction_is_idempotent` (mesmo result_hash e contagem) |
| AT-016 | Competência faltante gera alerta sem bloquear | Pass | `test_missing_payroll_is_missing_source_not_divergent`; painel de pendências |
| AT-017 | Ajuste com motivo, original preservado e auditoria | Pass | pgTAP (6 asserções) + `schemas.test.ts` |
| AT-018 | Isolamento entre escritórios | Pass | pgTAP `rls.test.sql` (22) + E2E (B negado em dossiê, PDF, snapshot, XLSX, páginas) |
| AT-019 | Homologação gera snapshot com SHA-256 | Pass | pgTAP (hash confere com o conteúdo) + E2E |
| AT-020 | Dossiê homologado somente leitura | Pass | pgTAP + E2E ("Dossiê homologado: alteração não permitida") |
| AT-021 | Exportação XLSX e JSON com hash | Pass | `test_export_xlsx.py`; E2E XLSX 80 KB; JSON com 957 valores e sha256 do snapshot |
| AT-022 | 6 PDFs prontos para revisão em até 5 min | Pass | pytest: 4,1 s; E2E com Storage e worker reais: 9,2–10,2 s |

---

## Advisor Ledger

Revisão pós-build com a skill `code-review` (nível high) sobre `supabase/migrations`, `services/worker/src`, `apps/web/src` e `scripts/verify.mjs`. A skill `security-review` não pôde rodar (exige `origin/HEAD`; código ainda não commitado nem publicado): registrada como Not available; a superfície de segurança foi coberta pelo code review.

| # | Phase | Note | Severity | Decision | Evidence |
|---:|---|---|---|---|---|
| 1 | post-build | Reprocessar arquivo com ajustes marcava o arquivo como `failed` e travava a homologação | HIGH | APPLIED | checagem movida para antes do processamento; teste atualizado |
| 2 | post-build | Homologação possível com conciliação ainda na fila (snapshot com resultado desatualizado) | HIGH | APPLIED | `homologate_case` bloqueia jobs extract/reconcile pendentes; pgTAP novo |
| 3 | post-build | Mudança de tolerância não reconciliava os dossiês abertos | MEDIUM | APPLIED | trigger `offices_tolerance_reconcile` + auditoria; pgTAP novo |
| 4 | post-build | Exportação XLSX que falhou não podia ser pedida de novo | MEDIUM | APPLIED | `request_xlsx_export` reenfileira job `failed` |
| 5 | post-build | `window.open` após `await` bloqueado por popup | MEDIUM | APPLIED | janela aberta no clique; URL definida depois |
| 6 | post-build | PDF corrompido era repetido 3 vezes e terminava como INTERNAL | MEDIUM | APPLIED | `read_rows` converte em `NOT_PDF`; teste novo |
| 7 | post-build | `storage_path` podia apontar para o PDF de outro dossiê do mesmo escritório | MEDIUM | APPLIED | constraint exige caminho escritório/dossiê/arquivo.pdf |
| 8 | post-build | Convite só procurava o usuário existente nos primeiros 1000 | LOW | APPLIED | `listUserEmails` paginado |
| 9 | post-build | N+1 de `getUserById` na página de admin | LOW | APPLIED | uma listagem paginada |
| 10 | post-build | Cálculo duplicado de estabelecimentos nas validações do PGDAS | LOW | APPLIED | expressão única |

Após os itens HIGH, o Verify Gate foi repetido (Green) e os smokes E2E e de páginas foram repetidos (Pass).

---

## Issues Encountered

| # | Issue | Resolution | Impact |
|---:|---|---|---|
| 1 | Trigger de reclassificação bloqueava o worker ao gravar o tipo detectado | condição restrita a ações de usuário (`auth.uid()` presente) | nenhum após correção |
| 2 | psycopg com `autocommit=False` transformaria blocos `transaction()` em savepoints sem commit | conexão do worker em `autocommit=True` | corrigido antes dos testes |
| 3 | Tailwind v4 não aplica `@apply` de classes próprias em `@layer components` | componentes declarados com `@utility`; classe `table` renomeada para `data-table` | nenhum |
| 4 | Concatenação `text[] ‖ 'literal'` interpretada como array no Postgres | cast `::text` | gate red uma vez, corrigido na 1ª tentativa |
| 5 | Next 16 marca `middleware.ts` como depreciado (novo nome: `proxy.ts`) | mantido o caminho do Design; funciona, com aviso no build | migração futura com `npx @next/codemod middleware-to-proxy` |
| 6 | TypeScript 7.0 recém-lançado | fixado TypeScript 5.9.3, compatível com Next 16 | nenhum |
| 7 | `prompts/prompt01.md` (vazio) aparece como deletado no working tree | Build nunca alterou `prompts/`; tratado como ação do usuário, não revertido | confirmar com o usuário |
| 8 | Login no navegador não automatizado (política: não digitar senhas) | smoke autenticado feito por HTTP com cookies do `@supabase/ssr` | inspeção visual das telas logadas pendente para o usuário |
| 9 | Status do dossiê vira "Em revisão" alguns segundos antes de a conciliação terminar | a homologação avisa "aguarde e tente novamente" enquanto houver job pendente | UX: possível melhoria de exibir "conciliando" |

---

## Deviations from Design

| Deviation | User Decision | Reason | Impact |
|---|---|---|---|
| `homologate_case` como `SECURITY DEFINER` com checagem `is_member` | Registrado; contrato inalterado | evita conceder INSERT em snapshots e UPDATE de status aos usuários | mais seguro |
| Constraint do `storage_path` mais estrita (escritório/dossiê/arquivo.pdf) | Aplicado via review | impede referência cruzada entre dossiês | clientes devem montar o caminho nesse formato (o site já monta) |
| Homologação exige fila vazia de extract/reconcile do dossiê | Aplicado via review | snapshot nunca usa conciliação desatualizada | espera de poucos segundos após ajustes |
| Tabela `jobs` ganhou `run_after` (backoff) | Detalhe de implementação | backoff exponencial previsto no Design | nenhum |
| `errors.py` ganhou `HashMismatch` | Detalhe de implementação | conferência do SHA-256 no download | arquivos adulterados são rejeitados |

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
