# DESIGN: Importação e Conciliação de Documentos Fiscais

> Technical design for implementing Importação e Conciliação de Documentos Fiscais

## Metadata

| Attribute | Value |
|---|---|
| **Feature** | IMPORTACAO_CONCILIACAO |
| **Date** | 2026-09-24 |
| **Author** | SDD Design by RDD |
| **BRAINSTORM** | `sdd/BRAINSTORM_IMPORTACAO_CONCILIACAO.md` |
| **DEFINE** | `sdd/DEFINE_IMPORTACAO_CONCILIACAO.md` |
| **UX REVIEW** | N/A |
| **LLM Prompts** | false |
| **Status** | Ready for Build |

---

## Architecture Overview

Arquitetura de **aplicativo web SaaS multi-tenant**: um tenant por escritório, isolado por RLS; front-end e back-end Next.js; Supabase como plataforma de dados; worker Python assíncrono para o processamento pesado e determinístico.

```text
 Navegador (Analista / Admin do escritório)
   │  HTTPS
   ▼
┌──────────────────────────────────────────────────────────────┐
│ apps/web  — Next.js (App Router, TypeScript)                  │
│  • Páginas: login, dossiês, upload, revisão, conciliação,     │
│    homologação, exportação, admin                             │
│  • Server Actions (zod) → Supabase com JWT do usuário (RLS)   │
│  • SHA-256 do arquivo calculado no navegador (WebCrypto)      │
└───────┬───────────────────────────────┬──────────────────────┘
        │ upload direto (RLS Storage)   │ SQL/RPC (RLS)
        ▼                               ▼
┌────────────────────┐   ┌──────────────────────────────────────┐
│ Supabase Storage   │   │ Supabase Postgres                     │
│ bucket privado     │   │  tenancy · cases · source_files       │
│ documents/         │   │  jobs (fila) · extracted_values       │
│  <office>/<case>/  │   │  value_adjustments · validations      │
│ exports/           │   │  reconciliations · snapshots          │
└────────▲───────────┘   │  audit_events · RPC homologate_case   │
         │               └──────────────▲───────────────────────┘
         │ download PDF /               │ claim job (SKIP LOCKED),
         │ upload XLSX                  │ grava valores/validações/
         │ (service role)               │ conciliações (service role)
┌────────┴──────────────────────────────┴───────────────────────┐
│ services/worker — Python 3.12+ (container Docker)              │
│  loop de polling → pipeline:                                   │
│   recepção → classificação → parser (pdfplumber, coordenadas)  │
│   → normalização → validações internas → conciliação           │
│   → exportação XLSX (openpyxl)                                 │
│  Parsers: PGDAS-D · Folha Alterdata · DRE Alterdata ·          │
│           Balancete Analítico Alterdata                        │
└────────────────────────────────────────────────────────────────┘
 Saídas: tela de revisão/conciliação; snapshot JSON (hash); XLSX
```

---

## Components

| Component | Purpose | Technology / Pattern | Inputs | Outputs | Dependencies |
|---|---|---|---|---|---|
| Web App | UI e casos de uso: login, empresas, dossiês, upload, revisão, ajuste, justificativa, homologação, exportação, admin | Next.js App Router + TypeScript + `@supabase/ssr` + zod + Tailwind | Ações do usuário, PDFs | Linhas em `source_files`/`jobs`, ajustes, justificativas, chamada RPC de homologação, downloads | Supabase Auth/DB/Storage |
| Auth & Tenancy | Identidade, papéis (admin/analyst) e isolamento por escritório | Supabase Auth + tabelas `offices`/`office_members` + RLS com `is_member(office_id)` | JWT | Decisão de acesso | Postgres |
| Storage | Guarda PDFs originais e XLSX exportados | Supabase Storage, bucket privado `documents`, path `<office_id>/<case_id>/<file_id>.pdf` e `<office_id>/<case_id>/exports/...` | Upload do navegador / worker | URLs assinadas | Auth & Tenancy |
| Job Queue | Fila durável e idempotente | Tabela `jobs` + `FOR UPDATE SKIP LOCKED` + `idempotency_key` único | Inserts da web e do worker | Job reivindicado | Postgres |
| Worker Runtime | Loop de polling, claim, execução e retry com backoff | Python, `psycopg` 3, container Docker | Jobs | Status do job | Job Queue, Storage |
| Classifier | Identifica o tipo do documento, CNPJ e competência por âncoras de cabeçalho | Regras determinísticas sobre o texto da página 1 | PDF | `doc_type`, `cnpj`, `competence` ou `UNCLASSIFIED` | Layout Engine |
| Layout Engine | Reconstrói linhas por coordenadas e faz o parse de números BR | `pdfplumber` `extract_words` + agrupamento por `top` | PDF | `Row[]` com bbox e página | pdfplumber |
| Parsers (4) | Extraem todas as linhas por layout | Classe por documento com `PARSER_VERSION` e âncoras obrigatórias | `Row[]` | `ExtractedValue[]` | Layout Engine |
| Internal Validator | Confere totais internos de cada documento | Funções puras por `doc_type` | `ExtractedValue[]` | Linhas em `validations` | Parsers |
| Reconciler | Concilia as fontes por competência com tolerância | Regras R1–R6 parametrizadas por `account_mappings` e `offices.settings` | Valores efetivos do dossiê | Linhas em `reconciliations` | Postgres |
| Homologation | Congela o snapshot imutável com hash | Função SQL `homologate_case` + `pgcrypto` + triggers de imutabilidade | `case_id` | Linha em `snapshots`, status do caso | Postgres |
| Exporter | Gera XLSX do snapshot; o JSON é o próprio snapshot | `openpyxl` (worker) + Route Handler JSON (web) | Snapshot | Arquivos XLSX/JSON | Storage |
| Audit Log | Registra antes/depois de uploads, ajustes, justificativas, homologações e exportações | Tabela `audit_events` append-only + triggers | Eventos | Trilha de auditoria | Postgres |

---

## Key Decisions

### Decision 1: Aplicativo web SaaS multi-tenant com isolamento por RLS

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-24 |
| **Source** | Instrução do usuário na fase Design ("aplicativo web (SaaS)") + DEFINE (piloto multi-escritório) |

**Context:** O piloto atende vários escritórios parceiros, e os dados de um escritório não podem vazar para outro (AT-018).

**Choice:** Banco compartilhado com coluna `office_id` em todas as tabelas de domínio, RLS ativa em todas elas e políticas de Storage baseadas no primeiro segmento do path (`office_id`). O provisionamento de escritórios é administrativo (seed/SQL do responsável da plataforma). O Admin do escritório convida analistas.

**Rationale:** É o modelo SaaS mais simples de operar no Supabase e atende ao isolamento com testes automatizáveis (pgTAP).

**Alternatives Rejected:**
1. Um projeto Supabase por escritório — custo e operação multiplicados para um piloto.
2. Schema por tenant — complica migrations e RLS sem ganho no piloto.

**Consequences:**
- Toda query e todo insert do worker (service role, que ignora RLS) precisam filtrar e gravar `office_id` explicitamente; isso é coberto por teste.
- Cadastro público, planos e cobrança permanecem fora do escopo (DEFINE).

### Decision 2: Fila de jobs em tabela Postgres com polling do worker

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-24 |
| **Source** | DEFINE (idempotência, retry seguro, ≤ 5 min) + clarificação técnica |

**Context:** O processamento de PDFs é assíncrono e precisa de retry sem duplicar registros.

**Choice:** Tabela `jobs` (`kind`: `extract` \| `reconcile` \| `export_xlsx`) com `idempotency_key` único, claim via `UPDATE ... WHERE id = (SELECT ... FOR UPDATE SKIP LOCKED LIMIT 1)`, polling a cada `WORKER_POLL_SECONDS` (padrão 2 s), até `WORKER_MAX_ATTEMPTS` tentativas e lease de `WORKER_LEASE_SECONDS` para jobs órfãos.

**Rationale:** Nenhuma infraestrutura adicional; é transacional com os dados; é fácil de testar e de observar em SQL.

**Alternatives Rejected:**
1. `pgmq` / Supabase Queues — mais uma extensão e API para um volume de piloto.
2. Webhook/Edge Function disparando o worker — exige endpoint público no worker e trata retry pior.

**Consequences:**
- Latência mínima igual ao intervalo de polling (2 s), compatível com a meta de 5 min.
- O worker precisa de conexão Postgres direta (`DATABASE_URL`).

### Decision 3: Parsers determinísticos por coordenadas com versão

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-24 |
| **Source** | Brainstorm (Approach A, amostras observadas) + DEFINE (LLM Prompts=false) |

**Context:** `pdftotext -layout` embaralha colunas nos PDFs Alterdata; reconstruir por `top` funcionou nos 4 tipos.

**Choice:** Um Layout Engine comum (agrupamento de palavras por `top` com tolerância `LINE_TOL=2.5pt`, ordenação por `x0`) e quatro parsers com âncoras obrigatórias e `PARSER_VERSION` semântica. Âncora ausente dispara `LayoutNotRecognized` e o arquivo inteiro falha, sem valores parciais (AT-014).

**Rationale:** Rastreabilidade (página + bbox), reprodutibilidade e testes com casos dourados.

**Alternatives Rejected:**
1. Extração por LLM — não determinística; removida via YAGNI.
2. Extração de tabela automática do pdfplumber (`extract_tables`) — os PDFs "Print To PDF" não têm linhas de grade confiáveis.

**Consequences:**
- Mudança de layout exige nova versão do parser.
- Os valores gravam `parser_version`, o que permite reprocessar e comparar.

### Decision 4: Extração idempotente por substituição transacional

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-24 |
| **Source** | DEFINE (AT-015, critério de reprocessamento) |

**Context:** Retries e reprocessamentos não podem duplicar valores.

**Choice:** Numa única transação: `DELETE FROM extracted_values WHERE file_id = $1` seguido do insert do conjunto completo, com `ordinal` sequencial e `UNIQUE(file_id, ordinal)`. `result_hash` = SHA-256 do JSON canônico dos valores extraídos, gravado em `source_files`. Reprocessamento é bloqueado se o arquivo já tiver ajustes manuais ou o caso estiver homologado.

**Rationale:** Simples e verificável: mesmo arquivo + mesma versão = mesmo `result_hash`.

**Alternatives Rejected:**
1. Upsert por chave natural — as linhas de rubricas repetem código (ex.: "141" aparece duas vezes na amostra), então a chave natural é ambígua.

**Consequences:**
- Ajustes referenciam `extracted_values.id`, por isso o reprocessamento só é permitido sem ajustes.

### Decision 5: Valores efetivos = extraído + último ajuste; original preservado

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-24 |
| **Source** | DEFINE (AT-017, RF-05 do PRD) |

**Context:** Ajustes manuais precisam de motivo e não podem apagar o original.

**Choice:** `extracted_values` nunca é atualizado pela web (sem política de UPDATE). Ajustes são inseridos em `value_adjustments` (motivo obrigatório, `CHECK (length(reason) >= 5)`). A view `effective_values` expõe `coalesce(último ajuste, valor original)`. Trigger grava em `audit_events`.

**Rationale:** Imutabilidade do dado extraído e trilha completa.

**Alternatives Rejected:**
1. Colunas `original_value`/`current_value` na mesma linha — perde o histórico de ajustes sucessivos.

**Consequences:**
- A conciliação e o snapshot leem sempre `effective_values`.

### Decision 6: Homologação atômica no banco com snapshot JSONB + SHA-256

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-24 |
| **Source** | DEFINE (AT-009, AT-019, AT-020, AT-021) |

**Context:** A homologação precisa verificar bloqueios e congelar os dados de forma atômica.

**Choice:** Função `homologate_case(p_case_id uuid)` (`SECURITY INVOKER`) que: verifica que o usuário é membro do escritório; verifica ausência de arquivos `failed`/`rejected`/`unclassified`/`cnpj_mismatch` e de conciliações `divergent` sem justificativa; monta `content jsonb` (empresa, período, arquivos com hash, valores efetivos com origem, ajustes, validações, conciliações, `parser_versions`); calcula `sha256 = encode(digest(content::text,'sha256'),'hex')`; insere em `snapshots`; muda o caso para `homologated`. Triggers `BEFORE INSERT/UPDATE/DELETE` bloqueiam alterações em `value_adjustments`, `reconciliations`, `source_files` e `snapshots` de casos homologados.

**Rationale:** Uma única transação garante consistência; o hash sobre `jsonb::text` é estável porque o jsonb normaliza a ordem das chaves.

**Alternatives Rejected:**
1. Homologação no worker — processo assíncrono desnecessário para uma operação curta e crítica.

**Consequences:**
- A exportação JSON é o `content` do snapshot + `sha256`; o XLSX é derivado dele pelo worker.

### Decision 7: Conciliação parametrizada por mapeamento de contas Alterdata

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-24 |
| **Source** | Brainstorm (conciliação observada em ago/2026) + DEFINE (A-004, A-005, tolerância R$ 1,00) |

**Context:** As contas-alvo são identificáveis pelo código Alterdata, mas podem variar por empresa.

**Choice:** Tabela `account_mappings(office_id, company_id NULL, target, doc_type, account_code)`. Linhas com `company_id` nulo são o padrão do escritório; o seed usa os códigos das amostras. Regras por competência:
- R1 Receita: PGDAS `rpa_total` × DRE `vendas` × balancete `vendas` (crédito − débito do período).
- R2 DAS: PGDAS `total_debito` × DRE `simples` × balancete `simples_despesa` (débito do período).
- R3 INSS: folha `inss_empregados` × balancete `inss_a_pagar` (crédito do período).
- R4 FGTS: folha `fgts_apurado` × balancete `fgts_a_pagar` (crédito do período).
- R5 Proventos: folha `total_adicionais` × balancete `salarios_a_pagar` (crédito do período).
- R6 DAS anterior: PGDAS(m−1) `total_debito` × balancete `simples_a_recolher` (saldo anterior de m).

`status` ∈ `ok` \| `divergent` \| `missing_source`. `missing_source` gera alerta, sem bloquear (AT-016).

**Rationale:** Reproduz exatamente a conciliação manual validada e permite ajuste por empresa sem mudar código.

**Alternatives Rejected:**
1. Códigos fixos no código — quebra em planos de contas diferentes.
2. De-para completo rubrica → conta — adiado (SHOULD, simplificado).

**Consequences:**
- Empresas com plano de contas diferente precisam de mapeamento antes de conciliar (tela Admin).

### Decision 8: Hospedagem agnóstica de provedor

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-24 |
| **Source** | DEFINE (Open Questions não bloqueantes) |

**Context:** O provedor de hospedagem do worker e da web não foi escolhido.

**Choice:** O worker é entregue como imagem Docker configurada só por variáveis de ambiente. A web é um app Next.js padrão (`next build && next start`). Nenhum SDK de provedor no código.

**Rationale:** Não bloqueia o Build; a escolha do provedor fica para o deploy do piloto.

**Alternatives Rejected:**
1. Acoplar a um provedor agora — decisão sem requisito que a sustente.

**Consequences:**
- O deploy é um passo operacional separado do Build.

### Decision 9: Amostras reais fora do Git; casos dourados sem PII

| Attribute | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-24 |
| **Source** | DEFINE (constraint LGPD) |

**Context:** As amostras contêm CPF, RG e nomes; fixtures versionadas não podem ter PII.

**Choice:** `docs/Amostras/` entra no `.gitignore`. Os testes leem PDFs de `SAMPLES_DIR` (padrão `docs/Amostras`) e comparam com `services/worker/tests/golden/*.json`, que contêm apenas valores numéricos, códigos de conta/rubrica, CNPJ da empresa e competências (nenhum nome de pessoa, CPF ou RG). Testes que dependem dos PDFs são marcados `samples`; `npm run verify` exige `SAMPLES_DIR` presente e falha com mensagem clara se estiver ausente.

**Rationale:** Cumpre a LGPD sem perder os casos dourados.

**Alternatives Rejected:**
1. Anonimizar os PDFs — reescrever PDFs pode alterar coordenadas e invalidar o teste do parser.

**Consequences:**
- CI remoto precisará receber as amostras por segredo/artefato privado (fora deste Build).

---

## File Manifest

| # | File | Action | Purpose | Agent / Owner | Dependencies |
|---:|---|---|---|---|---|
| 1 | `.gitignore` | Create | Ignorar `node_modules`, `.env*`, `.venv`, `.next`, `docs/Amostras/`, `__pycache__` | (general) | None |
| 2 | `.env.example` | Create | Variáveis da web e do worker, sem valores sensíveis | (general) | None |
| 3 | `package.json` | Create | Workspaces npm (`apps/web`); devDependency `supabase` (Supabase CLI, versão fixada, validada 2.117.0); scripts `verify`, `verify:worker`, `verify:db` (`npx supabase test db`), `verify:web`, `db:start` (`npx supabase start`), `db:types` (`npx supabase gen types typescript --local`) | (general) | None |
| 4 | `README.md` | Create | Pré-requisitos (Node 20+, Python 3.12+, Docker Desktop em execução; Supabase CLI instalada via `npm install`, sem instalação global), setup local e execução do verify | (general) | 3 |
| 5 | `supabase/config.toml` | Create | Configuração do Supabase local (via `supabase init`) | (general) | None |
| 6 | `supabase/migrations/20260924000001_tenancy.sql` | Create | `offices`, `office_members`, enum `member_role`, funções `is_member`/`is_admin`, RLS | (general) | 5 |
| 7 | `supabase/migrations/20260924000002_companies_cases.sql` | Create | `companies`, `tax_cases`, `account_mappings`, RLS | (general) | 6 |
| 8 | `supabase/migrations/20260924000003_files_jobs.sql` | Create | `source_files` (`UNIQUE(case_id, sha256)`), `jobs` (`UNIQUE(idempotency_key)`), trigger que enfileira `extract` no insert de arquivo, RLS | (general) | 7 |
| 9 | `supabase/migrations/20260924000004_extraction.sql` | Create | `extracted_values`, `value_adjustments`, `validations`, view `effective_values`, trigger que enfileira `reconcile` após ajuste, RLS | (general) | 8 |
| 10 | `supabase/migrations/20260924000005_reconciliation.sql` | Create | `reconciliations` + política de UPDATE restrita à justificativa, RLS | (general) | 9 |
| 11 | `supabase/migrations/20260924000006_snapshot_audit.sql` | Create | `snapshots`, `audit_events`, triggers de auditoria e imutabilidade, função `homologate_case` (pgcrypto) | (general) | 10 |
| 12 | `supabase/migrations/20260924000007_storage.sql` | Create | Bucket privado `documents` e políticas por `office_id` no path | (general) | 6 |
| 13 | `supabase/seed.sql` | Create | Escritórios A e B de teste, usuários admin/analista, `account_mappings` padrão Alterdata (40101, 4.1.1.01.001, 34009, 3.1.1.15.009, 20308, 20403, 20405, 20401) | (general) | 11, 12 |
| 14 | `supabase/tests/rls.test.sql` | Create | pgTAP: isolamento entre escritórios em todas as tabelas e no Storage (AT-018) | (general) | 13 |
| 15 | `supabase/tests/homologation.test.sql` | Create | pgTAP: bloqueio por divergência, snapshot + hash, imutabilidade, auditoria de ajustes (AT-009, AT-017, AT-019, AT-020) | (general) | 13 |
| 16 | `services/worker/pyproject.toml` | Create | Pacote `worker`; deps `pdfplumber`, `psycopg[binary]`, `pydantic`, `openpyxl`, `httpx`; dev `pytest`; marker `samples` | (general) | None |
| 17 | `services/worker/Dockerfile` | Create | Imagem Python slim que executa `python -m worker.main` | (general) | 16 |
| 18 | `services/worker/src/worker/__init__.py` | Create | Pacote | (general) | 16 |
| 19 | `services/worker/src/worker/config.py` | Create | Leitura de configuração via variáveis de ambiente (pydantic) | (general) | 18 |
| 20 | `services/worker/src/worker/models.py` | Create | `Row`, `Word`, `ExtractedValue`, `ParseResult`, `ValidationResult`, `ReconciliationResult`, `DocType` | (general) | 18 |
| 21 | `services/worker/src/worker/errors.py` | Create | `NoTextLayer`, `LayoutNotRecognized`, `CnpjMismatch`, `Unclassified`, `TransientError` com `code` | (general) | 18 |
| 22 | `services/worker/src/worker/pdf/numbers.py` | Create | Parse de moeda BR (`1.234,56`, sufixo D/C, asteriscos), CNPJ, competência, separação de células coladas (`92.916,6302/2025`) | (general) | 20 |
| 23 | `services/worker/src/worker/pdf/layout.py` | Create | Abertura do PDF, checagem da camada de texto e reconstrução de linhas por coordenada | (general) | 20, 21 |
| 24 | `services/worker/src/worker/classify.py` | Create | Âncoras de cabeçalho → `DocType`, CNPJ e competência | (general) | 22, 23 |
| 25 | `services/worker/src/worker/parsers/base.py` | Create | Protocolo `Parser` (`DOC_TYPE`, `PARSER_VERSION`, `parse(rows)`), helper `require_anchor` | (general) | 20, 21 |
| 26 | `services/worker/src/worker/parsers/pgdas.py` | Create | Parser PGDAS-D: 2.1, 2.2 (competências anteriores), 2.7 por atividade, 2.8 totais | (general) | 22, 25 |
| 27 | `services/worker/src/worker/parsers/folha_alterdata.py` | Create | Parser Resumo Geral: rubricas, totais, nº funcionários, GPS/FGTS/IRRF (página 2) | (general) | 22, 25 |
| 28 | `services/worker/src/worker/parsers/dre_alterdata.py` | Create | Parser DRE: contas com classificação, subtotais `=`, resultado do exercício | (general) | 22, 25 |
| 29 | `services/worker/src/worker/parsers/balancete_alterdata.py` | Create | Parser Balancete Analítico: código `[n]`, saldo anterior, débito, crédito, saldo atual, nível hierárquico | (general) | 22, 25 |
| 30 | `services/worker/src/worker/parsers/__init__.py` | Create | Registro `DocType → Parser` | (general) | 26, 27, 28, 29 |
| 31 | `services/worker/src/worker/validations.py` | Create | Validações internas por documento (AT-007) | (general) | 20 |
| 32 | `services/worker/src/worker/reconcile.py` | Create | Regras R1–R6 com tolerância e `account_mappings` (funções puras) | (general) | 20 |
| 33 | `services/worker/src/worker/db.py` | Create | Conexão psycopg, claim/finish/fail de jobs, persistência transacional de valores, validações e conciliações (sempre com `office_id`) | (general) | 19, 20 |
| 34 | `services/worker/src/worker/storage.py` | Create | Download/upload no Storage via REST com service role (`httpx`) | (general) | 19 |
| 35 | `services/worker/src/worker/export_xlsx.py` | Create | Gera XLSX (abas Resumo, Valores, Ajustes, Validações, Conciliações) a partir do snapshot | (general) | 20 |
| 36 | `services/worker/src/worker/pipeline.py` | Create | Orquestra `extract` (recepção → classificação → parser → validações → persistência → enfileira `reconcile`), `reconcile` e `export_xlsx` | (general) | 24, 30, 31, 32, 33, 34, 35 |
| 37 | `services/worker/src/worker/main.py` | Create | Loop de polling, lease, backoff, logs estruturados JSON, shutdown gracioso | (general) | 36 |
| 38 | `services/worker/tests/conftest.py` | Create | Fixture `SAMPLES_DIR`, skip/fail do marker `samples`, carregamento dos golden | (general) | 16 |
| 39 | `services/worker/tests/golden/pgdas_202606.json` | Create | Valores esperados do PGDAS 06/2026 (sem PII) | (general) | None |
| 40 | `services/worker/tests/golden/pgdas_202607.json` | Create | Valores esperados do PGDAS 07/2026 | (general) | None |
| 41 | `services/worker/tests/golden/pgdas_202608.json` | Create | Valores esperados do PGDAS 08/2026 | (general) | None |
| 42 | `services/worker/tests/golden/folha_202608.json` | Create | Rubricas e totais esperados da folha 08/2026 | (general) | None |
| 43 | `services/worker/tests/golden/dre_202608.json` | Create | Contas e resultado esperados da DRE 08/2026 | (general) | None |
| 44 | `services/worker/tests/golden/balancete_202608.json` | Create | Contas esperadas do balancete 08/2026 | (general) | None |
| 45 | `services/worker/tests/golden/reconciliation_202608.json` | Create | Resultado esperado de R1–R6 para 08/2026 | (general) | None |
| 46 | `services/worker/tests/test_numbers.py` | Create | Unit: moeda, D/C, asteriscos, células coladas, CNPJ | (general) | 22, 38 |
| 47 | `services/worker/tests/test_classify.py` | Create | 6/6 amostras classificadas; PDF sem texto; não classificado (AT-001, AT-010, AT-013) | (general) | 24, 38 |
| 48 | `services/worker/tests/test_parsers.py` | Create | Golden dos 4 parsers; bbox/página em 100% dos valores; âncora ausente → falha (AT-002 a AT-006, AT-014) | (general) | 30, 38, 39, 40, 41, 42, 43, 44 |
| 49 | `services/worker/tests/test_validations.py` | Create | Totais internos das amostras passam; valor adulterado falha (AT-007) | (general) | 31, 48 |
| 50 | `services/worker/tests/test_reconcile.py` | Create | R1–R6 de 08/2026 = golden; diferença > R$ 1,00 → `divergent`; fonte ausente → `missing_source` (AT-008, AT-009, AT-016) | (general) | 32, 45 |
| 51 | `services/worker/tests/test_pipeline.py` | Create | Integração com Postgres local: extração idempotente (mesmo `result_hash`, sem duplicar), duplicidade por hash, CNPJ divergente, `office_id` em todas as linhas (AT-011, AT-012, AT-015) | (general) | 36, 38 |
| 52 | `services/worker/tests/test_export_xlsx.py` | Create | XLSX contém todas as abas e o hash do snapshot (AT-021) | (general) | 35 |
| 53 | `services/worker/tests/test_performance.py` | Create | Smoke: 6 amostras → pronto para revisão em ≤ 300 s (AT-022) | (general) | 36, 38 |
| 54 | `apps/web/package.json` | Create | Next.js, React, `@supabase/ssr`, `@supabase/supabase-js`, zod, Tailwind; dev vitest, TypeScript; scripts `dev`, `build`, `typecheck`, `test` | (general) | 3 |
| 55 | `apps/web/tsconfig.json` | Create | TypeScript strict | (general) | 54 |
| 56 | `apps/web/next.config.ts` | Create | Configuração Next.js (limite de body para server actions) | (general) | 54 |
| 57 | `apps/web/vitest.config.ts` | Create | Configuração vitest | (general) | 54 |
| 58 | `apps/web/src/lib/database.types.ts` | Create | Tipos gerados via `npm run db:types` (`npx supabase gen types typescript --local`) | (general) | 11, 54 |
| 59 | `apps/web/src/lib/supabase/server.ts` | Create | Cliente Supabase server-side com cookies (JWT do usuário) | (general) | 58 |
| 60 | `apps/web/src/lib/supabase/client.ts` | Create | Cliente Supabase browser (upload direto ao Storage) | (general) | 58 |
| 61 | `apps/web/src/lib/supabase/admin.ts` | Create | Cliente service role, apenas server-side, só para convite de usuários | (general) | 58 |
| 62 | `apps/web/src/lib/hash.ts` | Create | SHA-256 de `File` via WebCrypto | (general) | 54 |
| 63 | `apps/web/src/lib/schemas.ts` | Create | Schemas zod: criar empresa/dossiê, registrar upload, ajuste (motivo ≥ 5), justificativa, classificação manual, tolerância | (general) | 54 |
| 64 | `apps/web/src/lib/format.ts` | Create | Formatação BRL, competência, status | (general) | 54 |
| 65 | `apps/web/src/middleware.ts` | Create | Refresh de sessão e redirect para `/login` | (general) | 59 |
| 66 | `apps/web/src/app/layout.tsx` | Create | Layout raiz, Tailwind, `lang="pt-BR"` | (general) | 54 |
| 67 | `apps/web/src/app/globals.css` | Create | Estilos base Tailwind | (general) | 54 |
| 68 | `apps/web/src/app/login/page.tsx` | Create | Login por e-mail/senha (Supabase Auth) | (general) | 59, 60 |
| 69 | `apps/web/src/app/(app)/layout.tsx` | Create | Shell autenticado com seletor de escritório e navegação | (general) | 59, 66 |
| 70 | `apps/web/src/app/(app)/cases/page.tsx` | Create | Lista de dossiês do escritório | (general) | 69, 64 |
| 71 | `apps/web/src/app/(app)/cases/new/page.tsx` | Create | Criar empresa (CNPJ) e dossiê (período) | (general) | 69, 63 |
| 72 | `apps/web/src/app/(app)/cases/actions.ts` | Create | Server actions: criar empresa/dossiê, registrar upload, reclassificar, ajustar valor, justificar divergência, homologar (RPC), solicitar XLSX | (general) | 59, 63 |
| 73 | `apps/web/src/app/(app)/cases/[id]/page.tsx` | Create | Painel do dossiê: upload, arquivos e status, pendências (competência faltante, falhas, divergências), homologar/exportar | (general) | 72, 74, 77 |
| 74 | `apps/web/src/components/UploadDropzone.tsx` | Create | Upload múltiplo com progresso, hash no navegador, alerta de duplicidade | (general) | 60, 62, 72 |
| 75 | `apps/web/src/app/(app)/cases/[id]/review/page.tsx` | Create | Revisão: valores efetivos com arquivo/página/bbox, link para o PDF assinado na página, edição com motivo | (general) | 72, 76 |
| 76 | `apps/web/src/components/ValueTable.tsx` | Create | Tabela de valores com origem, original × ajustado e diálogo de ajuste | (general) | 64 |
| 77 | `apps/web/src/components/StatusBadge.tsx` | Create | Badges de status de arquivo, job, conciliação e caso | (general) | 64 |
| 78 | `apps/web/src/app/(app)/cases/[id]/reconciliation/page.tsx` | Create | Conciliações por competência, diferença, status, justificativa | (general) | 72, 79 |
| 79 | `apps/web/src/components/ReconciliationTable.tsx` | Create | Tabela R1–R6 com ação de justificar | (general) | 64 |
| 80 | `apps/web/src/app/api/cases/[id]/export/route.ts` | Create | GET JSON do snapshot (`?format=json`) ou URL assinada do XLSX (`?format=xlsx`), respeitando RLS | (general) | 59 |
| 81 | `apps/web/src/app/(app)/admin/page.tsx` | Create | Admin: membros, convite de analista, tolerância, `account_mappings` | (general) | 69, 82 |
| 82 | `apps/web/src/app/(app)/admin/actions.ts` | Create | Server actions de admin (verificação `is_admin`) | (general) | 61, 63 |
| 83 | `apps/web/src/lib/schemas.test.ts` | Create | Vitest: motivo obrigatório, CNPJ válido, tolerância ≥ 0 | (general) | 57, 63 |
| 84 | `apps/web/src/lib/hash.test.ts` | Create | Vitest: SHA-256 conhecido | (general) | 57, 62 |
| 85 | `scripts/verify.mjs` | Create | Orquestra o verify: checa `SAMPLES_DIR`, checa Docker Engine ativo, roda pytest do worker, `npx supabase test db`, `typecheck` e `test` da web; toda chamada da CLI usa `npx supabase` (nunca o binário global); exit ≠ 0 em qualquer falha | (general) | 3, 14, 15, 46, 83 |

**Total Files:** 85

### Agent Assignment Rationale

| Agent / Owner | Files Assigned | Why |
|---|---|---|
| (general) | 1–85 | Nenhum catálogo de agentes especializados foi fornecido ou observado no projeto |

**Agent Discovery:** Not available

---

## Code Patterns

### Pattern 1: Reconstrução de linhas por coordenadas (Layout Engine)

```python
# services/worker/src/worker/pdf/layout.py
from dataclasses import dataclass
import pdfplumber
from worker.errors import NoTextLayer

LINE_TOL = 2.5  # pontos

@dataclass(frozen=True)
class Word:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float

@dataclass(frozen=True)
class Row:
    page: int                      # 1-based
    words: tuple[Word, ...]

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return (min(w.x0 for w in self.words), min(w.top for w in self.words),
                max(w.x1 for w in self.words), max(w.bottom for w in self.words))

def read_rows(path: str) -> list[Row]:
    rows: list[Row] = []
    with pdfplumber.open(path) as pdf:
        if not any((p.extract_text() or "").strip() for p in pdf.pages):
            raise NoTextLayer("PDF sem texto selecionável — OCR não suportado")
        for pno, page in enumerate(pdf.pages, start=1):
            words = sorted(page.extract_words(use_text_flow=False), key=lambda w: (w["top"], w["x0"]))
            current: list[Word] = []
            for w in words:
                word = Word(w["text"], w["x0"], w["x1"], w["top"], w["bottom"])
                if current and abs(word.top - current[0].top) > LINE_TOL:
                    rows.append(Row(pno, tuple(sorted(current, key=lambda x: x.x0))))
                    current = []
                current.append(word)
            if current:
                rows.append(Row(pno, tuple(sorted(current, key=lambda x: x.x0))))
    return rows
```

### Pattern 2: Números BR, natureza D/C e células coladas

```python
# services/worker/src/worker/pdf/numbers.py
import re
from decimal import Decimal

# quantificadores escritos por extenso: \d\d?\d? = 1 a 3 dígitos
MONEY = re.compile(r"\**(-?\d\d?\d?(?:\.\d\d\d)*,\d\d)([DC])?")
GLUED = re.compile(r"(\d\d?\d?(?:\.\d\d\d)*,\d\d)(\d\d/\d\d\d\d)")  # "92.916,6302/2025"

def parse_money(token: str) -> tuple[Decimal, str | None]:
    m = MONEY.fullmatch(token.strip())
    if not m:
        raise ValueError("valor monetário inválido: " + repr(token))
    value = Decimal(m.group(1).replace(".", "").replace(",", "."))
    return value, m.group(2)  # natureza 'D' | 'C' | None

def unglue(text: str) -> str:
    return GLUED.sub(r"\1 \2", text)
```

### Pattern 3: Contrato do parser e do valor extraído

```python
# services/worker/src/worker/models.py (trecho) + parsers/base.py
from decimal import Decimal
from enum import StrEnum
from pydantic import BaseModel

class DocType(StrEnum):
    PGDAS_D = "PGDAS_D"
    FOLHA_ALTERDATA = "FOLHA_ALTERDATA"
    DRE_ALTERDATA = "DRE_ALTERDATA"
    BALANCETE_ALTERDATA = "BALANCETE_ALTERDATA"

class ExtractedValue(BaseModel):
    ordinal: int
    section: str                 # ex.: "2.7.atividade.1", "rubricas.adicionais"
    field_key: str               # ex.: "tributo.irpj", "rubrica.001", "conta.20308"
    label: str
    account_code: str | None = None
    column: str | None = None    # ex.: "total", "saldo_anterior", "debito"
    competence: str              # "YYYY-MM"
    value: Decimal
    nature: str | None = None    # "D" | "C"
    page: int
    bbox: tuple[float, float, float, float]

class ParseResult(BaseModel):
    doc_type: DocType
    parser_version: str
    cnpj: str
    competence: str
    values: list[ExtractedValue]

# parsers/base.py
from typing import Protocol
from worker.errors import LayoutNotRecognized
from worker.pdf.layout import Row

class Parser(Protocol):
    DOC_TYPE: DocType
    PARSER_VERSION: str
    def parse(self, rows: list[Row]) -> ParseResult: ...

def require_anchor(rows: list[Row], anchor: str, parser_version: str) -> int:
    for i, r in enumerate(rows):
        if anchor in r.text:
            return i
    raise LayoutNotRecognized("âncora ausente: " + repr(anchor) + " (parser " + parser_version + ")")
```

### Pattern 4: RLS por escritório

```sql
-- supabase/migrations/20260924000001_tenancy.sql (trecho)
create or replace function public.is_member(p_office uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from office_members
                 where office_id = p_office and user_id = auth.uid());
$$;

-- padrão aplicado a cada tabela de domínio
alter table public.source_files enable row level security;
create policy source_files_select on public.source_files
  for select using (public.is_member(office_id));
create policy source_files_insert on public.source_files
  for insert with check (public.is_member(office_id) and uploaded_by = auth.uid());

-- storage: primeiro segmento do path = office_id
create policy documents_rw on storage.objects for all
  using (bucket_id = 'documents' and public.is_member(((storage.foldername(name))[1])::uuid))
  with check (bucket_id = 'documents' and public.is_member(((storage.foldername(name))[1])::uuid));
```

### Pattern 5: Claim de job idempotente

```sql
-- usado por services/worker/src/worker/db.py
update jobs set status = 'running', attempts = attempts + 1, locked_at = now()
where id = (
  select id from jobs
  where status = 'queued'
     or (status = 'running' and locked_at < now() - make_interval(secs => %(lease)s))
  order by created_at
  for update skip locked
  limit 1
)
returning id, office_id, kind, payload, attempts;
```

### Pattern 6: Server action com validação e RLS

```typescript
// apps/web/src/app/(app)/cases/actions.ts (trecho)
"use server";
import {
  revalidatePath,
} from "next/cache";
import {
  createClient,
} from "@/lib/supabase/server";
import {
  adjustValueSchema,
} from "@/lib/schemas";

type ActionResult =
  | {
      ok: true;
    }
  | {
      ok: false;
      error: unknown;
    };

const fail = (error: unknown): ActionResult => ({
  ok: false,
  error,
});

// input esperado: valueId (uuid), newValue (string decimal), reason (mín. 5 caracteres)
export async function adjustValue(input: unknown): Promise<ActionResult> {
  const parsed = adjustValueSchema.safeParse(input);
  if (!parsed.success) return fail(parsed.error.flatten());

  const supabase = await createClient();
  const auth = await supabase.auth.getUser();
  const user = auth.data.user;
  if (!user) return fail("não autenticado");

  const result = await supabase.from("value_adjustments").insert({
    value_id: parsed.data.valueId,
    new_value: parsed.data.newValue,
    reason: parsed.data.reason,
    author: user.id,
  });
  if (result.error) return fail(result.error.message); // RLS ou trigger de imutabilidade
  revalidatePath("/cases");
  return {
    ok: true,
  };
}
```

---

## Data Flow

```text
1. Upload (web)
   Analista seleciona PDFs → navegador calcula SHA-256 → consulta source_files(case_id, sha256)
   → duplicado: alerta e não envia (AT-011)
   → novo: upload para documents/<office>/<case>/<file_id>.pdf (política Storage)
     → server action insere source_files(status='uploaded') → trigger insere
       jobs(kind='extract', idempotency_key='extract:<file_id>:<sha256>') + audit_event
   │
   ▼
2. Claim (worker)
   Polling a cada 2 s → claim com SKIP LOCKED → source_files.status='processing'
   │
   ▼
3. Recepção
   Download do Storage → confere SHA-256 e MIME application/pdf → read_rows()
   → NoTextLayer: status='rejected', error_code='NO_TEXT' (AT-010), job done (sem retry)
   │
   ▼
4. Classificação
   Âncoras da página 1 → doc_type, CNPJ, competência
   → sem âncora: status='unclassified' (AT-013); reclassificação manual reenfileira extract
   → CNPJ ≠ companies.cnpj: status='cnpj_mismatch' (bloqueante, AT-012)
   │
   ▼
5. Extração
   Parser[doc_type].parse(rows) → ParseResult com todas as linhas, página e bbox
   → LayoutNotRecognized: status='failed', error_code='LAYOUT', parser_version (AT-014)
   │
   ▼
6. Validações internas + persistência (1 transação)
   validations.py → DELETE/INSERT extracted_values e validations → result_hash
   → source_files.status='extracted' → enfileira jobs(kind='reconcile',
     idempotency_key='reconcile:<case_id>:<epoch>')
   │
   ▼
7. Conciliação
   Lê effective_values + account_mappings + offices.settings.tolerance_brl
   → R1..R6 por competência → upsert reconciliations (ok | divergent | missing_source),
     preservando justificativas quando os valores não mudaram
   → caso fica 'review' quando todos os arquivos saíram de 'uploaded'/'processing'
   │
   ▼
8. Revisão (web)
   Analista vê valores com origem (link para o PDF assinado #page=N); ajusta com motivo
   → value_adjustments + audit_event → trigger enfileira reconcile (volta ao passo 7)
   Analista justifica divergências → reconciliations.justification + audit_event
   │
   ▼
9. Homologação (web → RPC homologate_case)
   Checa bloqueios → falha com lista de pendências (AT-009)
   → OK: snapshot(content jsonb, sha256) + case.status='homologated' + audit_event (AT-019)
   → triggers passam a rejeitar alterações (AT-020)
   │
   ▼
10. Exportação
   JSON: GET /api/cases/<id>/export?format=json → snapshot.content + sha256
   XLSX: server action enfileira export_xlsx → worker gera com openpyxl →
         documents/<office>/<case>/exports/<snapshot_id>.xlsx → URL assinada (AT-021)
```

---

## Integration Points

| External System | Integration Type | Authentication | Direction | Failure / Retry |
|---|---|---|---|---|
| Supabase Auth | SDK (`@supabase/ssr`) | E-mail/senha; JWT em cookie | in/out | Falha de sessão → redirect para `/login`; sem retry automático |
| Supabase Postgres (web) | SDK/PostgREST + RPC | JWT do usuário (RLS) | bidirectional | Erro exibido ao usuário; operações idempotentes podem ser repetidas pelo usuário |
| Supabase Postgres (worker) | `psycopg` conexão direta | `DATABASE_URL` com role de serviço | bidirectional | Erro de conexão → `TransientError`, job volta para `queued` com backoff exponencial (2^n s, até `WORKER_MAX_ATTEMPTS`=3); depois `failed` |
| Supabase Storage (web) | SDK upload direto | JWT do usuário (políticas Storage) | out | Falha de upload → arquivo não registrado; usuário reenvia |
| Supabase Storage (worker) | REST via `httpx` | `SUPABASE_SERVICE_ROLE_KEY` | bidirectional | Timeout 30 s; 5xx/timeout → `TransientError` com retry; 404 → `failed` com `FILE_NOT_FOUND` |

---

## Testing Strategy

| Test Type | Scope / Requirement | Files | Tools | Pass Signal |
|---|---|---|---|---|
| Unit | Parse de números, D/C, células coladas, CNPJ | `services/worker/tests/test_numbers.py` | pytest | Todos passam |
| Unit | Classificação 6/6, PDF sem texto, não classificado (AT-001, AT-010, AT-013) | `services/worker/tests/test_classify.py` | pytest (`samples`) | 6/6 tipos, CNPJ e competência corretos |
| Unit (golden) | Todas as linhas dos 4 parsers = golden; 100% com página/bbox; âncora ausente falha (AT-002 a AT-006, AT-014) | `services/worker/tests/test_parsers.py`, `services/worker/tests/golden/*.json` | pytest (`samples`) | Igualdade exata com o golden |
| Unit | Validações internas (AT-007) | `services/worker/tests/test_validations.py` | pytest | Amostras passam; valor adulterado falha |
| Unit (golden) | Conciliação R1–R6 08/2026, tolerância, `missing_source` (AT-008, AT-009, AT-016) | `services/worker/tests/test_reconcile.py` | pytest | Igual ao golden; > R$ 1,00 → `divergent` |
| Integration | Pipeline com Postgres local: idempotência, duplicidade, CNPJ divergente, `office_id` (AT-011, AT-012, AT-015) | `services/worker/tests/test_pipeline.py` | pytest + Supabase local | Mesmo `result_hash` e contagem após 2 execuções |
| Integration | Exportação XLSX (AT-021) | `services/worker/tests/test_export_xlsx.py` | pytest + openpyxl | Abas presentes e hash igual ao do snapshot |
| Integration (DB) | RLS entre escritórios em tabelas e Storage (AT-018) | `supabase/tests/rls.test.sql` | pgTAP via `npx supabase test db` | 0 linhas cruzadas |
| Integration (DB) | Homologação, bloqueio, imutabilidade e auditoria (AT-009, AT-017, AT-019, AT-020) | `supabase/tests/homologation.test.sql` | pgTAP via `npx supabase test db` | Todos os asserts passam |
| Unit (web) | Schemas zod e hash (AT-017 no cliente) | `apps/web/src/lib/schemas.test.ts`, `apps/web/src/lib/hash.test.ts` | vitest | Todos passam |
| Typecheck | Web | `apps/web/tsconfig.json` | `tsc --noEmit` | exit 0 |
| Smoke | 6 PDFs → "pronto para revisão" em ≤ 300 s (AT-022) | `services/worker/tests/test_performance.py` | pytest (`samples`) + Supabase local | Tempo ≤ 300 s |
| E2E / Verify Gate | Todos os anteriores | `scripts/verify.mjs`, `package.json` | `npm run verify` | exit 0 |

---

## Error Handling

| Error Type | Detection | Handling Strategy | Retry? | Observability |
|---|---|---|---|---|
| PDF sem camada de texto | `NoTextLayer` em `read_rows` | `source_files.status='rejected'`, `error_code='NO_TEXT'`, mensagem ao usuário | No | Log `file.rejected` + métrica `files_rejected_total<code>` |
| Arquivo não-PDF / MIME inválido | Magic bytes `%PDF` no worker; `accept` no input da web | `rejected`, `error_code='NOT_PDF'` | No | Log `file.rejected` |
| Duplicidade | `UNIQUE(case_id, sha256)` + consulta prévia na web | Alerta na UI; não insere | N/A | Evento de auditoria `file.duplicate` |
| Tipo não reconhecido | `Unclassified` no classificador | `status='unclassified'`; reclassificação manual reenfileira | No | Log `file.unclassified` |
| CNPJ divergente | Comparação com `companies.cnpj` | `status='cnpj_mismatch'`; bloqueia homologação | No | Log `file.cnpj_mismatch` |
| Layout alterado | `LayoutNotRecognized` | `status='failed'`, `error_code='LAYOUT'`, `parser_version`; nenhum valor gravado | No | Métrica `parser_failures_total<doc_type,parser_version>` |
| Validação interna falha | `validations.status='fail'` | Exibida como pendência; o analista ajusta com motivo | N/A | Contagem de validações falhas por arquivo |
| Divergência de conciliação | `diff > tolerance` | `divergent`; bloqueia `homologate_case` até correção/justificativa | N/A | Métrica `reconciliation_divergent_total<rule>` |
| Banco/Storage indisponível ou timeout | Exceção psycopg/httpx | `TransientError`: job volta a `queued` com backoff; após 3 tentativas `failed` | Yes | Log `job.retry`/`job.failed` com `attempts` |
| Worker morre no meio do job | `locked_at` mais antigo que o lease | Outro ciclo reivindica; a extração é idempotente | Yes | Log `job.reclaimed` |
| Tentativa de alterar caso homologado | Trigger de imutabilidade (`raise exception`) | Erro retornado à UI: "dossiê homologado" | No | Evento de auditoria `write.denied` |
| Acesso a outro escritório | RLS | 0 linhas / erro de política | No | Logs do Postgres |
| Reprocessar arquivo com ajustes | Checagem em `pipeline.extract` | `failed`, `error_code='HAS_ADJUSTMENTS'` | No | Log `job.rejected` |

---

## Configuration

| Config Key | Type | Source / Default | Sensitive? | Description |
|---|---|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | string | env (web) | No | URL do projeto Supabase |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | string | env (web) | No | Chave pública (anon/publishable) |
| `SUPABASE_SERVICE_ROLE_KEY` | string | env (web server-only e worker) | Yes | Usada só em `admin.ts` (convites) e no worker (Storage) |
| `SUPABASE_URL` | string | env (worker) | No | URL do Supabase para REST do Storage |
| `DATABASE_URL` | string | env (worker) | Yes | Conexão Postgres do worker |
| `WORKER_POLL_SECONDS` | int | env / `2` | No | Intervalo de polling |
| `WORKER_MAX_ATTEMPTS` | int | env / `3` | No | Tentativas antes de `failed` |
| `WORKER_LEASE_SECONDS` | int | env / `300` | No | Lease de jobs `running` órfãos |
| `STORAGE_BUCKET` | string | env / `documents` | No | Bucket privado |
| `MAX_UPLOAD_MB` | int | env / `20` | No | Limite de tamanho por PDF |
| `SAMPLES_DIR` | path | env / `docs/Amostras` | No (conteúdo com PII fora do Git) | PDFs para testes `samples` |
| `offices.settings.tolerance_brl` | numeric | banco / `1.00` | No | Tolerância de conciliação por escritório |
| `account_mappings` | tabela | banco / seed Alterdata | No | Contas-alvo das regras R1–R6 |

---

## Security Considerations

- **Isolamento de tenant:** RLS em todas as tabelas de domínio com `is_member(office_id)`; políticas de Storage pelo prefixo `office_id`; o teste pgTAP `rls.test.sql` é parte obrigatória do Verify Gate.
- **Service role:** o worker ignora RLS, por isso toda query em `db.py` recebe e filtra por `office_id` vindo do job; `test_pipeline.py` verifica que todas as linhas gravadas têm o `office_id` do caso. Na web, `SUPABASE_SERVICE_ROLE_KEY` só existe em `lib/supabase/admin.ts` (server-only, com `import "server-only"`) e só é usada após checar `is_admin`.
- **Autorização por papel:** convites, tolerância e `account_mappings` exigem `is_admin`; o analista não altera parâmetros.
- **Validação de entrada:** zod em todas as server actions; MIME e magic bytes `%PDF` checados no worker; limite `MAX_UPLOAD_MB`; nome original do arquivo guardado só como metadado (o path usa `file_id`).
- **PII / LGPD:** bucket privado com URLs assinadas de curta duração (60 s); logs do worker registram só IDs, códigos de erro e contagens, nunca texto do PDF, nomes, CPF ou RG; `docs/Amostras/` fora do Git; golden sem PII.
- **Imutabilidade e auditoria:** `extracted_values` sem política de UPDATE/DELETE para usuários; `audit_events` e `snapshots` append-only via trigger; homologado = somente leitura.
- **Segredos:** apenas via variáveis de ambiente; `.env*` no `.gitignore`; `.env.example` sem valores.
- **Upload direto:** como o navegador grava no Storage, a política exige que o primeiro segmento do path seja um escritório do qual o usuário é membro.

---

## Observability

| Aspect | Implementation | Signal / Why |
|---|---|---|
| Logging | Worker: JSON por linha (`event`, `job_id`, `file_id`, `office_id`, `doc_type`, `parser_version`, `duration_ms`, `error_code`), sem PII. Web: erros de server action no log do servidor | Diagnosticar falhas por layout, retries e jobs órfãos |
| Metrics | Derivadas em SQL a partir de `jobs`/`source_files`/`reconciliations`: tempo upload→`extracted` por arquivo, tempo até o caso ficar `review`, falhas por `doc_type`/`parser_version`, divergências por regra | Acompanhar a meta de ≤ 5 min (AT-022), a completude e a qualidade dos parsers (métricas do PRD) |
| Tracing | N/A — correlação por `job_id`/`file_id`/`case_id` nos logs e no `audit_events` | Fluxo assíncrono simples; IDs bastam para seguir um arquivo ponta a ponta |

---

## Requirements Traceability

| Requirement / AT | Design Element | Test / Gate |
|---|---|---|
| MUST isolamento por escritório / AT-018 | Decision 1, #6, #12, #14 | `rls.test.sql` |
| MUST empresa e dossiê | #7, #71, #72 | `schemas.test.ts`, `rls.test.sql` |
| MUST upload, hash, duplicidade / AT-011 | #8, #62, #74 | `test_pipeline.py`, `hash.test.ts` |
| AT-001 classificação | #24 | `test_classify.py` |
| AT-002 PGDAS-D | #26 | `test_parsers.py` + golden #39–#41 |
| AT-003 Folha | #27 | `test_parsers.py` + golden #42 |
| AT-004 DRE | #28 | `test_parsers.py` + golden #43 |
| AT-005 Balancete | #29 | `test_parsers.py` + golden #44 |
| AT-006 origem de cada valor | Pattern 1/3, #23, #9 | `test_parsers.py` |
| AT-007 validações internas | #31 | `test_validations.py` |
| AT-008 conciliação | Decision 7, #32 | `test_reconcile.py` + golden #45 |
| AT-009 bloqueio por divergência | #11 (`homologate_case`), #32 | `test_reconcile.py`, `homologation.test.sql` |
| AT-010 PDF sem texto | Pattern 1, #23 | `test_classify.py` |
| AT-012 CNPJ divergente | #36 | `test_pipeline.py` |
| AT-013 não classificado + manual | #24, #72 | `test_classify.py` |
| AT-014 layout não reconhecido | Decision 3, #25 | `test_parsers.py` |
| AT-015 idempotência | Decision 2, 4, #33 | `test_pipeline.py` |
| AT-016 competência faltante | Decision 7 (`missing_source`), #73 | `test_reconcile.py` |
| AT-017 ajuste com motivo + auditoria | Decision 5, #9, #11, #76 | `homologation.test.sql`, `schemas.test.ts` |
| AT-019 snapshot + hash | Decision 6, #11 | `homologation.test.sql` |
| AT-020 imutabilidade | Decision 6, #11 | `homologation.test.sql` |
| AT-021 exportação XLSX/JSON | #35, #80 | `test_export_xlsx.py` |
| AT-022 ≤ 5 min para 6 PDFs | Decision 2, #36, #37 | `test_performance.py` |
| Verify Gate `npm run verify` | #3, #85 | exit 0 |
| SHOULD classificação manual | #72, #73 | `test_classify.py` |
| SHOULD de-para simplificado | Decision 7, #13, #81 | `test_reconcile.py` |
| SHOULD painel de pendências | #73 | Revisão manual no Build |

---

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual Risk |
|---|---|---|---|
| Layout Alterdata varia entre empresas/meses (A-001, A-002) | Parser falha com `LAYOUT` | Âncoras textuais em vez de coordenadas absolutas; colunas por ordem relativa de `x0`; `parser_version`; falha explícita | Médio: amostras de um único cliente |
| Agrupamento por `top` junta ou separa linhas indevidamente | Valores trocados | `LINE_TOL` configurável no código; golden cobre 100% das linhas; validações internas detectam | Baixo |
| Plano de contas diferente do seed | Conciliação `missing_source` | `account_mappings` por empresa editável pelo Admin | Baixo |
| `npx supabase test db` e Supabase local exigem Docker Engine ativo | Verify Gate não roda na máquina | CLI fixada como devDependency e chamada via `npx`; `verify.mjs` checa o Docker Engine e falha com mensagem clara se estiver parado | Baixo: toolchain verificado em 2026-09-24 (Node 24.14.1, Python 3.14.4, Docker 29.6.1, Supabase CLI 2.117.0 via npx) |
| Amostras ausentes na máquina/CI | Testes `samples` não rodam | `verify.mjs` exige `SAMPLES_DIR` e falha explicitamente (não pula silenciosamente) | Baixo |
| Service role no worker ignora RLS | Vazamento entre escritórios | Filtro obrigatório por `office_id` + teste de integração | Baixo |
| PII em logs ou fixtures | Violação da LGPD | Logs só com IDs; golden sem PII; `.gitignore` | Baixo |
| Hash do snapshot depende da serialização `jsonb::text` | Hash diferente entre versões do Postgres | Hash gravado no snapshot e nunca recalculado para comparação; export traz o hash gravado | Baixo |

---

## Advisor Ledger

None — no formal external design review.

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-09-24 | SDD Design by RDD | Initial version |
| 1.1 | 2026-09-24 | SDD Design by RDD | Supabase CLI como devDependency no `package.json` raiz e chamada via `npx supabase` em scripts e `verify.mjs` (a CLI não está no PATH global); `verify.mjs` checa o Docker Engine; risco de toolchain rebaixado após checagem local |

---

## Next Step

Execute o **SDD Build by RDD**.
