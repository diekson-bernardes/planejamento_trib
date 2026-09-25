# HANDOFF: Importação e Conciliação de Documentos Fiscais (ciclo 1 do Planejamento Tributário)

> Registro do que ficou pronto e do que vem depois. Um arquivo por feature — cada etapa nova entra como seção no topo, nunca como arquivo separado.

## Ficha da feature

| Campo | Valor |
|---|---|
| **Objetivo** | Aplicativo web SaaS multi-escritório que importa PDFs do PGDAS-D e da Alterdata (Resumo Geral da Folha, DRE, Balancete Analítico), extrai todas as linhas com origem, concilia as fontes por competência (R1–R6, tolerância padrão R$ 1,00), permite revisão com ajuste justificado e homologa um snapshot imutável com SHA-256 exportável em JSON/XLSX — base de dados para o futuro motor tributário (ciclo 2). |
| **Status** | 🔨 em andamento |
| **Feito** | Brainstorm, Define, Design v1.1 e KB (2026-09-24); Build completo com Verify Gate verde (2026-09-24) |
| **Falta** | Commit/push do código; conferência visual das telas logadas pelo usuário; confirmar a deleção de `prompts/prompt01.md`; decidir hospedagem do piloto (Supabase remoto + container do worker + host do Next.js) |
| **Pronto quando** | (1) `npm run verify` termina com exit 0 na branch commitada; (2) um analista do escritório, pela interface em http://localhost:3000 (ou no ambiente do piloto), cria um dossiê, envia os 6 PDFs de `docs/Amostras/`, vê R1–R6 de 08/2026 como "Conciliado", homologa e baixa o XLSX; (3) o código está commitado na branch `feat/importacao-conciliacao` e publicado no remoto `master` (github.com/diekson-bernardes/planejamento_trib). |

---

## Eventos

- 2026-09-24 — Escopo do ciclo 1 fechado no Brainstorm como **somente importação + conciliação + homologação + exportação**; motor tributário (Simples/Presumido/Real), projeção e recomendação ficam para o ciclo 2.
- 2026-09-24 — Público mudou de "só o escritório" para **escritórios parceiros (piloto)** → multi-tenant com RLS desde o MVP.
- 2026-09-24 — Origem dos relatórios fixada em **somente Alterdata**, **PDF com texto** (OCR e XLSX fora do MVP), após o usuário alternar entre "4 sistemas" e "muito variado".
- 2026-09-24 — Design v1.1: Supabase CLI como devDependency e chamada via `npx supabase` (a CLI não está no PATH global da máquina).
- 2026-09-24 — Review pós-build aplicou 10 correções (ver Build Report); duas mudaram regras: homologação exige fila de extract/reconcile vazia do dossiê; `storage_path` deve ser exatamente `<office_id>/<case_id>/<file_id>.pdf`.

---

## 2026-09-24 — Build (SDD Build by RDD) e fechamento do ciclo 1

### O que foi feito

- **85 arquivos do File Manifest** implementados na branch `feat/importacao-conciliacao` (monorepo npm workspaces):
  - `supabase/migrations/20260924000001..7_*.sql` — tenancy + RLS (`is_member`, `is_admin`), empresas/dossiês/mapeamentos, arquivos + fila `jobs` (claim com `FOR UPDATE SKIP LOCKED`), valores extraídos + ajustes + view `effective_values`, conciliações, snapshots/auditoria append-only + `homologate_case()`, bucket privado `documents`.
  - `supabase/seed.sql` — Escritório A (`a0000000-0000-4000-8000-000000000001`) e B (`b0000000-0000-4000-8000-000000000002`), usuários fictícios, mapeamentos Alterdata padrão (40101, 4.1.1.01.001, 34009, 3.1.1.15.009, 20308, 20403, 20405, 20401).
  - `services/worker/` — Python: parsers `pgdas-1.0.0`, `folha-alterdata-1.0.0`, `dre-alterdata-1.0.0`, `balancete-alterdata-1.0.0` (linhas reconstruídas por coordenada com `pdfplumber`, tolerância 2,5 pt), validações internas, conciliação R1–R6, exportação XLSX, pipeline e loop com lease/backoff; `Dockerfile`.
  - `apps/web/` — Next.js 16 + Tailwind v4: login, dossiês, upload direto ao Storage com SHA-256 no navegador, revisão com ajuste justificado, conciliação com justificativa, homologação, exportação JSON/XLSX, administração (convite, tolerância, contas-alvo).
  - `scripts/verify.mjs` — Verify Gate; `README.md` com setup.
- **Verificação:** `npm run verify` exit 0 → pytest 73 passed, pgTAP 41 (Result: PASS), typecheck ok, vitest 11 passed. `next build` e `docker build services/worker` ok.
- **Smoke real** (Storage + worker + RLS, usuários do seed): 6 PDFs prontos em ~10 s; R1–R6 de 08/2026 com diferença 0,00; homologação com hash; XLSX de ~80 KB baixado; escritório B negado em dossiê, PDF, snapshot, XLSX e páginas (404).
- **Review pós-build:** 10 achados aplicados (lista no `sdd/BUILD_REPORT_IMPORTACAO_CONCILIACAO.md`, seção Advisor Ledger).
- **Checklist de fechamento — o que foi conferido:**
  - O código roda: Verify Gate verde, build do site e da imagem do worker concluídos, site e worker rodando localmente.
  - Critérios de aceite: AT-001 a AT-022 com evidência no Build Report (AT-022 medido em 4,1 s no pytest e ~10 s com Storage real; limite 300 s).
  - Mudanças salvas: todos os arquivos estão gravados no disco, na branch `feat/importacao-conciliacao`, **ainda sem commit** — ficou como pendência.
  - O que quebrou está anotado: sim, na seção Pendências abaixo e em Issues Encountered do Build Report.

### Casos e testes em aberto

- **Amostras reais** (fora do Git, contêm CPF/RG): `docs/Amostras/1.PGDASD-DECLARACAO-37704456202606001.pdf`, `...202607001.pdf`, `...202608001.pdf`, `2.Resumo da Folha.pdf`, `3.DRE.pdf`, `Balancete.pdf` — empresa CNPJ `37.704.456/0001-42`, comércio (Anexo I, faixa 6).
- **Valores de referência de 08/2026** (conferidos manualmente no Brainstorm e reproduzidos pelo sistema): receita 203.180,77; DAS 23.430,47; INSS 2.963,53; FGTS 2.706,49; proventos 34.212,13; DAS de 07/2026 = 38.975,46 = saldo anterior de Simples a Recolher [20308].
- **Dossiês no banco local** (Supabase local, escritório A): `a9954b89-f8dc-4c4f-b08a-5cef7cb1262e` (homologado, 6 arquivos, com XLSX) e `85032664-c7f4-46f5-836e-6ded853c719f` (em revisão, 6 arquivos). Somem com `npm run db:reset`.
- **Usuários locais** (senha `senha-local-123`): `analista.a@example.com`, `admin.a@example.com` (Escritório A), `analista.b@example.com` (Escritório B).
- **Telas logadas** foram verificadas só por HTTP (12/12 checagens); a conferência visual no navegador ficou para o usuário (política: a IA não digita senhas).

### Pendências

**🐛 Bug fix** — o que ficou quebrado, parcial ou com comportamento errado conhecido:

- `prompts/prompt01.md` (arquivo vazio versionado) aparece como **deletado** no working tree sem ação do Build — confirmar se foi intencional; se não, `git checkout -- prompts/prompt01.md`.
- UX: o dossiê mostra "Em revisão" alguns segundos antes de a conciliação terminar; nesse intervalo a homologação responde "Processamento/conciliação em andamento — aguarde e tente novamente". Não quebra dados, mas confunde. Correção sugerida: mostrar "Conciliando" enquanto houver job `reconcile` na fila do dossiê.
- Aviso do Next 16: `apps/web/src/middleware.ts` usa convenção depreciada (novo nome `proxy.ts`). Funciona; migrar com `npx @next/codemod@canary middleware-to-proxy .`.

**✨ Feature improvement** — o que é incremento planejado, melhoria ou próxima etapa de escopo:

- Commit e push do ciclo 1 (branch `feat/importacao-conciliacao`).
- Obter mais amostras (outros meses e outros clientes Alterdata) e ampliar os golden em `services/worker/tests/golden/` — hoje os parsers foram validados em um único cliente e um mês de folha/contábil.
- Hospedagem do piloto: Supabase remoto (`npx supabase link` + `db push`), container do worker, host do Next.js; MFA e política de retenção antes de abrir para mais escritórios.
- Revisão pelo usuário da base de conhecimento `kb/` (6 domínios marcados PENDENTE DE REVISÃO; LC 214, LC 224 e Lei 15.270 lidas só em fontes secundárias).
- Ciclo 2 (novo fluxo SDD): motor tributário — elegibilidade e cálculo de Simples, Presumido e Real consumindo o snapshot homologado; base em `kb/planejamento-comparativo/`.
- `/security-review` não rodou (exige `origin/HEAD`); rodar depois do push.

### Próximos passos

1. Conferir e decidir sobre `prompts/prompt01.md` — `git status --short prompts/`. Pronto quando: o arquivo estiver restaurado ou a deleção for intencional e entrar no commit.
2. Conferir as telas no navegador — com Docker Desktop aberto: `npm run db:start`, `npm run dev:web` e `npm run dev:worker` (variáveis `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` de `npx supabase status`); entrar em http://localhost:3000 com `analista.a@example.com` / `senha-local-123`, criar dossiê para CNPJ 37.704.456/0001-42 (06/2026 a 08/2026) e enviar os 6 PDFs de `docs/Amostras/`. Pronto quando: R1–R6 de 08/2026 aparecem "Conciliado", a homologação mostra o hash e o XLSX baixa.
3. Commitar o ciclo 1 — `git add` de tudo exceto `docs/Amostras/` (já no `.gitignore`); conferir que nenhum PDF ou `.env.local` entra. Pronto quando: `npm run verify` exit 0 após o commit e `git status` limpo.
4. Publicar e revisar — push de `feat/importacao-conciliacao` para o remoto `master` (github.com/diekson-bernardes/planejamento_trib) e rodar `/security-review`. Pronto quando: review sem achados HIGH abertos.
5. Iniciar o ciclo 2 com a skill SDD Brainstorm by RDD tendo como entrada `docs/PRD_Planejamento_Tributario.md` §8–10 e `kb/planejamento-comparativo/index.md`. Pronto quando: `sdd/BRAINSTORM_MOTOR_TRIBUTARIO.md` gerado.

### Alertas — o que não quebrar

- **Isolamento por escritório:** toda tabela de domínio tem `office_id` + RLS; o worker usa conexão de serviço (ignora RLS) e **precisa filtrar/gravar `office_id` em toda query** (`services/worker/src/worker/db.py`). `supabase/tests/rls.test.sql` é parte do gate.
- **Imutabilidade:** `extracted_values` nunca é atualizado por usuário; ajustes só em `value_adjustments` com motivo ≥ 5 caracteres; dossiê homologado é somente leitura (triggers `*_immutable`); `snapshots` e `audit_events` são append-only.
- **Golden sem PII:** `services/worker/tests/golden/*.json` não podem conter rótulos (o balancete tem nome de pessoa em conta de adiantamento). `docs/Amostras/` nunca entra no Git.
- **Mudança de layout = nova versão de parser** (`PARSER_VERSION`), nunca edição silenciosa; os golden devem ser regenerados e conferidos contra os valores de referência de 08/2026.
- **Supabase CLI:** sempre `npx supabase …` (não está no PATH); Docker Desktop precisa estar aberto.
- **Fora de escopo:** OCR, XLSX de entrada, outros ERPs, IA na extração, razão contábil, papéis Revisor/Cliente/Auditor, cadastro público/cobrança, cálculo de regimes tributários.

### Onde está o trabalho

- Projeto: `C:\Users\User\Documents\BRAVO-BUILDER-PROJETOS\PLANEJAMENTO_TRIB`
- Branch: `feat/importacao-conciliacao` (criada de `master` @ `a374529 Inicio Sistema`), **sem commit** do Build.
- Especificação: `sdd/BRAINSTORM_…`, `sdd/DEFINE_…`, `sdd/DESIGN_…` (v1.1), `sdd/BUILD_REPORT_IMPORTACAO_CONCILIACAO.md`.
- Base de conhecimento: `kb/_index.yaml` (6 domínios).
- Processos locais ao fim da sessão: Supabase local (containers `supabase_*_planejamento-trib`), site em http://localhost:3000 (preview) e worker em segundo plano — podem ter sido encerrados junto com a sessão.

---

## 2026-09-24 — Brainstorm, Define, Design e KB

Brainstorm (escopo ciclo 1, abordagem A: parsers determinísticos Python + Supabase + Next.js), Define (22 ATs, Clarity 14/15, tolerância R$ 1,00, Verify Gate `npm run verify`), Design (85 arquivos, 9 ADRs; v1.1 com Supabase CLI via npx) e KB `kb/` (Simples, Presumido, Real, comparativo, documentos-fonte, reforma) — todos em `sdd/` e `kb/`.
